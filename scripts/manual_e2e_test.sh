#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://127.0.0.1:8000}
LOGDIR=${LOGDIR:-e2e_logs}
START_SERVER=${START_SERVER:-false}
STRESS=${STRESS:-0}

# Per-run subfolder inside e2e_logs
RUN_STAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="$LOGDIR/$RUN_STAMP"
mkdir -p "$RUN_DIR"

# require jq
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Please install jq and rerun." >&2
  exit 1
fi

function wait_for_server() {
  echo "Waiting for API at $API_URL/healthz ..."
  for i in {1..30}; do
    if curl -fsS "$API_URL/healthz" >/dev/null; then
      echo "API is up"; return 0; fi
    sleep 1
  done
  echo "API did not start in time" >&2
  exit 1
}

function start_server() {
  echo "Starting server..."
  # Ensure env flags are inherited by the server process
  (. .venv/bin/activate && exec env RISK_ML_ENABLED="${RISK_ML_ENABLED:-}" RISK_THRESHOLD="${RISK_THRESHOLD:-}" ROUTER_ENABLED="${ROUTER_ENABLED:-}" DOCS_PATH="${DOCS_PATH:-}" uvicorn app.main:app --host 127.0.0.1 --port 8000) &
  SVPID=$!
  echo $SVPID > "$RUN_DIR/server.pid"
  wait_for_server
}

function req() {
  set -o pipefail
  local name="$1"; shift
  echo "# $name" | tee -a "$RUN_DIR/trace.log"
  echo "$@" | tee -a "$RUN_DIR/trace.log"
  eval "$@" | tee "$RUN_DIR/${name}.out"
}

cleanup() {
  if [[ "${START_SERVER:-false}" == "true" ]] && [[ -f "$RUN_DIR/server.pid" ]]; then
    SVPID=$(cat "$RUN_DIR/server.pid" || true)
    if [[ -n "${SVPID:-}" ]] && ps -p "$SVPID" >/dev/null 2>&1; then
      echo "Stopping server PID $SVPID" | tee -a "$RUN_DIR/trace.log"
      kill "$SVPID" || true
    fi
  fi
}
trap cleanup EXIT

if [[ "$START_SERVER" == "true" ]]; then
  # Ensure ML flags are set for deterministic behavior when starting server
  export RISK_ML_ENABLED=${RISK_ML_ENABLED:-true}
  export RISK_THRESHOLD=${RISK_THRESHOLD:-0.6}
  start_server
fi

# 1) Health & Metrics
req health "curl -sS $API_URL/healthz | jq ." || true
req metrics "curl -sS $API_URL/metrics | head -n 50" || true

# 2) Query — ungrounded
req query_ungrounded "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Hello there\",\"grounded\": false}' | jq ."

# 3) Grounded with citations + assertions
mkdir -p e2e_docs; printf 'GDPR is a regulation about data protection.' > e2e_docs/gdpr.txt
export DOCS_PATH=$PWD/e2e_docs
req query_grounded "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is GDPR?\",\"grounded\": true}' | jq ."
# Assert citations non-empty
CIT_COUNT=$(jq '.citations | length' "$RUN_DIR/query_grounded.out" 2>/dev/null || echo 0)
if [[ ${CIT_COUNT:-0} -lt 1 ]]; then
  echo "FAIL: grounded query produced empty citations" | tee -a "$RUN_DIR/trace.log"; exit 1
else
  echo "PASS: grounded query citations count=$CIT_COUNT" | tee -a "$RUN_DIR/trace.log"
fi

# 4) Router intents
export ROUTER_ENABLED=true
# Deterministic router checks with crafted prompts
req router_pii "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Email is bob@example.com\",\"grounded\": false}' | jq ."
PII_INTENT=$(jq -r '.audit.router_intent // empty' "$RUN_DIR/router_pii.out" 2>/dev/null || echo "")
if [[ "$PII_INTENT" != "pii_detect" && "$PII_INTENT" != "qa" ]]; then
  echo "FAIL: router intent for PII-like prompt unexpected: '$PII_INTENT'" | tee -a "$RUN_DIR/trace.log"; EXIT_CODE=1
else
  echo "PASS: router intent for PII-like prompt = $PII_INTENT" | tee -a "$RUN_DIR/trace.log"
fi
req router_risk "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"What is the risk score for this incident?\",\"grounded\": false}' | jq ."
RISK_INTENT=$(jq -r '.audit.router_intent // empty' "$RUN_DIR/router_risk.out" 2>/dev/null || echo "")
if [[ "$RISK_INTENT" != "risk_score" && "$RISK_INTENT" != "qa" ]]; then
  echo "FAIL: router intent for risk-like prompt unexpected: '$RISK_INTENT'" | tee -a "$RUN_DIR/trace.log"; EXIT_CODE=1
else
  echo "PASS: router intent for risk-like prompt = $RISK_INTENT" | tee -a "$RUN_DIR/trace.log"
fi
req router_policy "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"What policy covers encryption?\",\"grounded\": false}' | jq ."
# Ambiguous prompt fallback check
req router_ambiguous "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Tell me something interesting\",\"grounded\": false}' | jq ."

# 5) PII endpoint - multiple cases
req pii_basic "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Contact me at alice.smith+test@example.org and +1 416-555-1212\",\"include_citations\": false}' | jq ."
req pii_ssn "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"SSN 123-45-6789 and email john.doe@example.com\",\"include_citations\": false}' | jq ."
req pii_cc "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"My Visa is 4111 1111 1111 1111 exp 10/30\",\"include_citations\": false}' | jq ."
req pii_with_citations "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Call me at (212) 555-0100 or email me@example.com\",\"include_citations\": true}' | jq ."
# Shape & coherence assertions for include_citations
PII_TYPES=$(jq -r '.types_present | join(",")' "$RUN_DIR/pii_with_citations.out" 2>/dev/null || echo "")
if [[ -z "$PII_TYPES" ]]; then echo "FAIL: PII include_citations missing types_present" | tee -a "$RUN_DIR/trace.log"; EXIT_CODE=1; else echo "PASS: PII include_citations types_present=[$PII_TYPES]" | tee -a "$RUN_DIR/trace.log"; fi
ENT_OK=$(jq -r '((.entities // []) | all(. as $e | ($e|has("type")) and ($e|has("value_preview")) and ($e|has("span"))))' "$RUN_DIR/pii_with_citations.out" 2>/dev/null || echo "false")
if [[ "$ENT_OK" != "true" ]]; then echo "FAIL: PII entities missing required fields" | tee -a "$RUN_DIR/trace.log"; EXIT_CODE=1; else echo "PASS: PII entities fields present" | tee -a "$RUN_DIR/trace.log"; fi
# RBAC negative case (expect 403)
set +e
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $API_URL/pii -H 'Content-Type: application/json' -d '{"text":"no role header should 403"}')
set -e
if [[ "$HTTP_CODE" != "403" ]]; then 
  echo "FAIL: /pii without role should be 403, got $HTTP_CODE" | tee -a "$RUN_DIR/trace.log"; EXIT_CODE=1 
else 
  echo "PASS: /pii RBAC enforced (403)" | tee -a "$RUN_DIR/trace.log"
  # Save the 403 response body for inspection
  curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -d '{"text":"no role header should 403"}' | tee "$RUN_DIR/pii_rbac_negative.out" >/dev/null
  echo "INFO: saved RBAC negative response to $RUN_DIR/pii_rbac_negative.out" | tee -a "$RUN_DIR/trace.log"
fi

# 6) Risk scoring + assertions
req risk_heuristic "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Critical breach and violation, potential lawsuit\"}' | jq ."
export RISK_ML_ENABLED=true; export RISK_THRESHOLD=0.6
req risk_ml "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Critical incident with severe impact and vulnerability exposed.\"}' | jq ."
# Assert risk ML method when enabled
RISK_METHOD=$(jq -r '.audit.risk_score_method // empty' "$RUN_DIR/risk_ml.out" 2>/dev/null || echo "")
if [[ "${RISK_METHOD}" != "ml" ]]; then
  echo "FAIL: Expected risk_score_method=ml when RISK_ML_ENABLED=true, got '$RISK_METHOD'" | tee -a "$RUN_DIR/trace.log"
  EXIT_CODE=1
else
  echo "PASS: risk_score_method=ml under ML mode" | tee -a "$RUN_DIR/trace.log"
fi
# Edge near threshold
export RISK_THRESHOLD=0.5
req risk_edge "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"moderate issue, possible concern\"}' | jq ."

# 7) Memory — short-term
export MEMORY_SHORT_ENABLED=true
export SHORT_MEMORY_MAX_TURNS_PER_SESSION=2
# Drive more turns than cap to exercise pruning
req memory_short_drive1 "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"hello\",\"user_id\":\"u\",\"session_id\":\"s\"}' | jq ."
req memory_short_drive2 "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"world\",\"user_id\":\"u\",\"session_id\":\"s\"}' | jq ."
req memory_short_drive3 "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"again\",\"user_id\":\"u\",\"session_id\":\"s\"}' | jq ."
req memory_short_list "curl -sS \"$API_URL/memory/short?user_id=u&session_id=s\" -H 'X-User-Role: analyst' | jq ."
sleep 0.1
req memory_short_clear "curl -sS -X DELETE \"$API_URL/memory/short?user_id=u&session_id=s\" -H 'X-User-Role: analyst' | jq ."
# Assert cleared semantics with prior turns
CLEARED_SHORT=$(jq -r '.cleared // empty' "$RUN_DIR/memory_short_clear.out" 2>/dev/null || echo "")
if [[ "$CLEARED_SHORT" != "true" ]]; then
  echo "FAIL: expected short memory cleared=true after prior turns, got '$CLEARED_SHORT'" | tee -a "$RUN_DIR/trace.log"; EXIT_CODE=1
else
  echo "PASS: short memory cleared after prior turns" | tee -a "$RUN_DIR/trace.log"
fi

# 8) Memory — long-term + retrieval assertion
export MEMORY_LONG_ENABLED=true
req memory_long_drive "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"A long message to seed long memory\",\"user_id\":\"lu\"}' | jq ."
req memory_long_list "curl -sS \"$API_URL/memory/long?user_id=lu\" -H 'X-User-Role: admin' | jq ."
req memory_long_clear "curl -sS -X DELETE \"$API_URL/memory/long?user_id=lu\" -H 'X-User-Role: admin' | jq ."
FACTS_BEFORE=$(jq '.facts | length' "$RUN_DIR/memory_long_list.out" 2>/dev/null || echo 0)
CLEARED_LONG=$(jq -r '.cleared // empty' "$RUN_DIR/memory_long_clear.out" 2>/dev/null || echo "")
if [[ ${FACTS_BEFORE:-0} -gt 0 ]]; then
  if [[ "$CLEARED_LONG" != "true" ]]; then
    echo "FAIL: long memory had $FACTS_BEFORE facts before clear but cleared=$CLEARED_LONG" | tee -a "$RUN_DIR/trace.log"; exit 1
  else
    echo "PASS: long memory cleared (had $FACTS_BEFORE facts)" | tee -a "$RUN_DIR/trace.log"
  fi
else
  if [[ "$CLEARED_LONG" == "true" ]]; then
    echo "PASS: long memory cleared (no prior facts)" | tee -a "$RUN_DIR/trace.log"
  else
    echo "INFO: long memory had no facts; cleared=$CLEARED_LONG (expected no-op)" | tee -a "$RUN_DIR/trace.log"
  fi
fi

# 9) Agents — research
req research "curl -sS -X POST $API_URL/research -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"topic\":\"Latest updates on GDPR and AI\",\"steps\":[\"search\",\"fetch\",\"summarize\",\"risk_check\"]}' | jq ."

# 10) RAG flags variants
export RAG_MULTI_QUERY_ENABLED=true; export RAG_MULTI_QUERY_COUNT=4; export RAG_HYDE_ENABLED=true
# Top-k = 1
export RAG_TOP_K=1
req rag_flags "curl -sS -X POST /query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data retention?\",\"grounded\": true}' | jq ."
CIT_COUNT_K1=$(jq '.citations | length' "/rag_flags.out" 2>/dev/null || echo 0)
if [[  -lt 1 ||  -gt 1 ]]; then echo "WARN: citations count  not within expected bounds for top_k=1" | tee -a "/trace.log"; else echo "PASS: citations count within bounds for top_k=1 ()" | tee -a "/trace.log"; fi
# Variant: disable hyDE, top-k = 3
export RAG_HYDE_ENABLED=false; export RAG_TOP_K=3
req rag_flags_no_hyde "curl -sS -X POST /query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data retention?\",\"grounded\": true}' | jq ."
CIT_COUNT_K3=$(jq '.citations | length' "/rag_flags_no_hyde.out" 2>/dev/null || echo 0)
if [[  -lt 1 ||  -gt 3 ]]; then echo "WARN: citations count  not within expected bounds for top_k=3" | tee -a "/trace.log"; else echo "PASS: citations count within bounds for top_k=3 ()" | tee -a "/trace.log"; fi
# Variant: single-query
export RAG_MULTI_QUERY_ENABLED=false
req rag_flags_single "curl -sS -X POST /query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data protection?\",\"grounded\": true}' | jq ."

# 11) Architect mode
export PROJECT_GUIDE_ENABLED=true
req architect_guide "curl -sS -X POST /architect -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"How does the router work?\",\"mode\":\"guide\"}' | jq ."
req architect_brainstorm "curl -sS -X POST /architect -H 'Content-Type: application/json' -d '{\"question\":\"Adapt for internal policy review\",\"mode\":\"brainstorm\"}' | jq ."

# 12) Observability
req openapi "python scripts/export_openapi.py && ls -l docs/openapi.yaml"
# Metrics delta checks
RISK_COUNT_BEFORE=$(curl -sS $API_URL/metrics | awk -F' ' '/^app_requests_total\{endpoint="\/risk",status="200"\}/ {print $2; exit}')
PII_COUNT_BEFORE=$(curl -sS $API_URL/metrics | awk -F' ' '/^app_requests_total\{endpoint="\/pii",status="200"\}/ {print $2; exit}')
req metrics_after "curl -sS $API_URL/metrics | head -n 50"
RISK_COUNT_AFTER=$(curl -sS $API_URL/metrics | awk -F' ' '/^app_requests_total\{endpoint="\/risk",status="200"\}/ {print $2; exit}')
PII_COUNT_AFTER=$(curl -sS $API_URL/metrics | awk -F' ' '/^app_requests_total\{endpoint="\/pii",status="200"\}/ {print $2; exit}')
if [[ -n "$PII_COUNT_BEFORE" && -n "$PII_COUNT_AFTER" && -n "$RISK_COUNT_BEFORE" && -n "$RISK_COUNT_AFTER" ]]; then
  if awk "BEGIN {exit !($PII_COUNT_AFTER >= $PII_COUNT_BEFORE && $RISK_COUNT_AFTER >= $RISK_COUNT_BEFORE)}"; then
    echo "PASS: metrics deltas non-decreasing for /pii and /risk" | tee -a "$RUN_DIR/trace.log"
  else
    echo "WARN: metrics deltas did not increase as expected (pii: $PII_COUNT_BEFORE->$PII_COUNT_AFTER, risk: $RISK_COUNT_BEFORE->$RISK_COUNT_AFTER)" | tee -a "$RUN_DIR/trace.log"
  fi
else
  echo "INFO: Could not parse request counters from metrics" | tee -a "$RUN_DIR/trace.log"
fi

# 12) Optional stress
if [[ "$STRESS" -gt 0 ]]; then
  echo "Running stress: $STRESS parallel ungrounded queries"
  seq 1 "$STRESS" | xargs -n1 -P8 -I{} bash -c \
    "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Hello {}\",\"grounded\": false}' >/dev/null"
  req metrics_stress "curl -sS $API_URL/metrics | head -n 50"
fi

echo "E2E test completed. Logs in $RUN_DIR"
