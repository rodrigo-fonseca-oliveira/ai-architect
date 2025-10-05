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
  (. .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000) &
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
req router_pii "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Email is bob@example.com\",\"grounded\": false}' | jq ."
req router_risk "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"What is the risk score for this incident?\",\"grounded\": false}' | jq ."
req router_policy "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"What policy covers encryption?\",\"grounded\": false}' | jq ."
# Ambiguous prompt fallback check
req router_ambiguous "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Tell me something interesting\",\"grounded\": false}' | jq ."

# 5) PII endpoint - multiple cases
req pii_basic "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Contact me at alice.smith+test@example.org and +1 416-555-1212\",\"include_citations\": false}' | jq ."
req pii_ssn "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"SSN 123-45-6789 and email john.doe@example.com\",\"include_citations\": false}' | jq ."
req pii_cc "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"My Visa is 4111 1111 1111 1111 exp 10/30\",\"include_citations\": false}' | jq ."
req pii_with_citations "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Call me at (212) 555-0100 or email me@example.com\",\"include_citations\": true}' | jq ."
# RBAC negative case (expect 403)
set +e
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $API_URL/pii -H 'Content-Type: application/json' -d '{"text":"no role header should 403"}')
set -e
if [[ "$HTTP_CODE" != "403" ]]; then echo "FAIL: /pii without role should be 403, got $HTTP_CODE" | tee -a "$RUN_DIR/trace.log"; exit 1; else echo "PASS: /pii RBAC enforced (403)" | tee -a "$RUN_DIR/trace.log"; fi

# 6) Risk scoring + assertions
req risk_heuristic "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Critical breach and violation, potential lawsuit\"}' | jq ."
export RISK_ML_ENABLED=true; export RISK_THRESHOLD=0.6
req risk_ml "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Critical incident with severe impact and vulnerability exposed.\"}' | jq ."
# Edge near threshold
export RISK_THRESHOLD=0.5
req risk_edge "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"moderate issue, possible concern\"}' | jq ."

# 7) Memory — short-term
export MEMORY_SHORT_ENABLED=true
req memory_short_drive "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"hello\",\"user_id\":\"u\",\"session_id\":\"s\"}' | jq ."
req memory_short_list "curl -sS \"$API_URL/memory/short?user_id=u&session_id=s\" -H 'X-User-Role: analyst' | jq ."
sleep 0.1
req memory_short_clear "curl -sS -X DELETE \"$API_URL/memory/short?user_id=u&session_id=s\" -H 'X-User-Role: analyst' | jq ."
# Assert cleared semantics: if there were turns before, expect cleared=true; else allow false
TURNS_BEFORE=$(jq '.turns | length' "$RUN_DIR/memory_short_list.out" 2>/dev/null || echo 0)
CLEARED_SHORT=$(jq -r '.cleared // empty' "$RUN_DIR/memory_short_clear.out" 2>/dev/null || echo "")
if [[ ${TURNS_BEFORE:-0} -gt 0 ]]; then
  if [[ "$CLEARED_SHORT" != "true" ]]; then
    echo "FAIL: short memory had $TURNS_BEFORE turns before clear but cleared=$CLEARED_SHORT" | tee -a "$RUN_DIR/trace.log"; exit 1
  else
    echo "PASS: short memory cleared (had $TURNS_BEFORE turns)" | tee -a "$RUN_DIR/trace.log"
  fi
else
  if [[ "$CLEARED_SHORT" == "true" ]]; then
    echo "PASS: short memory cleared (no prior turns)" | tee -a "$RUN_DIR/trace.log"
  else
    echo "INFO: short memory had no turns; cleared=$CLEARED_SHORT (expected no-op)" | tee -a "$RUN_DIR/trace.log"
  fi
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
req rag_flags "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data retention?\",\"grounded\": true}' | jq ."
# Variant: disable hyDE
export RAG_HYDE_ENABLED=false
req rag_flags_no_hyde "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data retention?\",\"grounded\": true}' | jq ."
# Variant: single-query
export RAG_MULTI_QUERY_ENABLED=false
req rag_flags_single "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data protection?\",\"grounded\": true}' | jq ."

# 11) Observability
req openapi "python scripts/export_openapi.py && ls -l docs/openapi.yaml"
req metrics_after "curl -sS $API_URL/metrics | head -n 50"

# 12) Optional stress
if [[ "$STRESS" -gt 0 ]]; then
  echo "Running stress: $STRESS parallel ungrounded queries"
  seq 1 "$STRESS" | xargs -n1 -P8 -I{} bash -c \
    "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Hello {}\",\"grounded\": false}' >/dev/null"
  req metrics_stress "curl -sS $API_URL/metrics | head -n 50"
fi

echo "E2E test completed. Logs in $RUN_DIR"
