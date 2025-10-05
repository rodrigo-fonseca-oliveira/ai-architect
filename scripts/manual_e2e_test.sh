#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://127.0.0.1:8000}
LOGDIR=${LOGDIR:-e2e_logs}
START_SERVER=${START_SERVER:-false}
STRESS=${STRESS:-0}

mkdir -p "$LOGDIR"

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
  echo $SVPID > "$LOGDIR/server.pid"
  wait_for_server
}

function req() {
  set -o pipefail
  local name="$1"; shift
  echo "# $name" | tee -a "$LOGDIR/trace.log"
  echo "$@" | tee -a "$LOGDIR/trace.log"
  bash -lc "$@" | tee "$LOGDIR/${name}.out"
}

if [[ "$START_SERVER" == "true" ]]; then
  start_server
fi

# 1) Health & Metrics
req health "curl -sS $API_URL/healthz | jq ." || true
req metrics "curl -sS $API_URL/metrics | head -n 50" || true

# 2) Query — ungrounded
req query_ungrounded "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Hello there\",\"grounded\": false}' | jq ."

# 3) Grounded with citations
mkdir -p e2e_docs; printf 'GDPR is a regulation about data protection.' > e2e_docs/gdpr.txt
export DOCS_PATH=$PWD/e2e_docs
req query_grounded "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is GDPR?\",\"grounded\": true}' | jq ."

# 4) Router intents
export ROUTER_ENABLED=true
req router_pii "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"Email is bob@example.com\",\"grounded\": false}' | jq ."
req router_risk "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"What is the risk score for this incident?\",\"grounded\": false}' | jq ."
req router_policy "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"What policy covers encryption?\",\"grounded\": false}' | jq ."

# 5) PII endpoint
req pii "curl -sS -X POST $API_URL/pii -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Contact me at alice.smith+test@example.org and +1 416-555-1212\",\"include_citations\": false}' | jq ."

# 6) Risk scoring
req risk_heuristic "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Critical breach and violation, potential lawsuit\"}' | jq ."
export RISK_ML_ENABLED=true; export RISK_THRESHOLD=0.6
req risk_ml "curl -sS -X POST $API_URL/risk -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"text\":\"Critical incident with severe impact and vulnerability exposed.\"}' | jq ."

# 7) Memory — short-term
export MEMORY_SHORT_ENABLED=true
req memory_short_drive "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"hello\",\"user_id\":\"u\",\"session_id\":\"s\"}' | jq ."
req memory_short_list "curl -sS \"$API_URL/memory/short?user_id=u&session_id=s\" -H 'X-User-Role: analyst' | jq ."
req memory_short_clear "curl -sS -X DELETE \"$API_URL/memory/short?user_id=u&session_id=s\" -H 'X-User-Role: analyst' | jq ."

# 8) Memory — long-term
export MEMORY_LONG_ENABLED=true
req memory_long_drive "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -d '{\"question\":\"A long message to seed long memory\",\"user_id\":\"lu\"}' | jq ."
req memory_long_list "curl -sS \"$API_URL/memory/long?user_id=lu\" -H 'X-User-Role: admin' | jq ."
req memory_long_clear "curl -sS -X DELETE \"$API_URL/memory/long?user_id=lu\" -H 'X-User-Role: admin' | jq ."

# 9) Agents — research
req research "curl -sS -X POST $API_URL/research -H 'Content-Type: application/json' -d '{\"topic\":\"Latest updates on GDPR and AI\",\"steps\":[\"search\",\"fetch\",\"summarize\",\"risk_check\"]}' | jq ."

# 10) RAG flags
export RAG_MULTI_QUERY_ENABLED=true; export RAG_MULTI_QUERY_COUNT=4; export RAG_HYDE_ENABLED=true
req rag_flags "curl -sS -X POST $API_URL/query -H 'Content-Type: application/json' -H 'X-User-Role: analyst' -d '{\"question\":\"What is data retention?\",\"grounded\": true}' | jq ."

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

echo "E2E test completed. Logs in $LOGDIR"
