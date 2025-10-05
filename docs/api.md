# API Overview

This service is a FastAPI application for AI risk, compliance, and observability.

- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc
- OpenAPI spec (exported): docs/openapi.yaml (see scripts/export_openapi.py)

## Cross-cutting behavior

- Request ID
  - Each request receives a request ID. By default, it is generated server-side.
  - Override header name via REQUEST_ID_HEADER (default: X-Request-ID).
  - Response includes the same header and logs include request_id.

- Error responses (JSON)
  - All errors use a consistent JSON shape:
    {
      "status": <int>,
      "error": <string>,
      "detail": <any>,
      "request_id": <string|null>
    }
  - Examples:
    - 422 Validation Error
      {
        "status": 422,
        "error": "Validation error",
        "detail": [{"loc": ["body", "field"], "msg": "...", "type": "..."}],
        "request_id": "..."
      }
    - 403 Forbidden
      {
        "status": 403,
        "error": "forbidden",
        "detail": "forbidden",
        "request_id": "..."
      }

- RBAC
  - Header: X-User-Role with one of: guest, analyst, admin (default: guest if missing/unknown).
  - Route-level rules (summary):
    - /metrics: open by default; if METRICS_TOKEN is set, requires header X-Metrics-Token.
    - /predict: analyst/admin
    - /query: grounded=true requires analyst/admin; grounded=false allows guest.
    - /research: step-based rules
      - fetch/search/summarize: analyst+
      - risk_check: guest+

## Notable endpoints

- GET /healthz — liveness probe
- GET /metrics — Prometheus metrics (optionally token-protected)
- POST /predict — model inference; requires role analyst/admin
- POST /query

Request: { question: str, grounded?: bool, user_id?: str, session_id?: str, intent?: str }
  - Response: { answer, citations?, audit }
  - Notes: session_id enables short-term memory grouping when MEMORY_SHORT_ENABLED=true
  - Config: LC_RAG_ENABLED (LangChain RAG), ROUTER_ENABLED (intent routing)
- POST /risk — Risk scoring endpoint (analyst/admin)
  - Request: { text: str }
  - Response: { label, value, rationale, audit }
- POST /policy_navigator — Policy Navigator Agent (analyst/admin)
  - Request: { question: string, max_subqs?: number }
  - Response: { recommendation: string, citations: [{source, snippet, page?}], audit: { steps[] } }

- GET /memory/short — list short-term memory for a session (analyst/admin)
  - Params: user_id (required), session_id (required)
  - Response: { turns: [{role, content, timestamp}], summary: string|null, audit: {...} }
- DELETE /memory/short — clear short-term memory for a session (analyst/admin)
  - Params: user_id (required), session_id (required)
  - Response: { cleared: boolean, audit: {...} }
- GET /memory/long — list long-term facts (analyst/admin)
  - Params: user_id (required), q (optional)
  - Response: { facts: [{text, created_at?, metadata?}], audit: {..., memory_long_reads?, memory_long_pruned?} }
- DELETE /memory/long — clear long-term facts for user (analyst/admin)
  - Params: user_id (required)
  - Response: { cleared: boolean, audit: {...} }
- GET /memory/long/export — export long-term facts (analyst/admin)
  - Params: user_id (required)
  - Response: { facts: [{id, text, created_at, metadata, embedding_present, embedding_dim}], audit: {..., memory_long_reads?, memory_long_pruned?} }
- POST /memory/long/import — import long-term facts (analyst/admin)
  - Params: user_id (required)
  - Body: { facts: [{ text: string, metadata?: object }] }
  - Response: { imported: number, audit: {..., memory_long_writes?, memory_long_pruned?} }
- GET /memory/status — memory status (admin only)
  - Response: { config: {...}, short_memory: { sessions: [{user_id, session_id, turns, summary}], db_ok }, long_memory: { users: [{user_id, facts}], store_ok }, counters: { memory_short_pruned_total, memory_long_pruned_total }, audit: {...} }

- /query audit includes memory counters when flags enabled:
  - memory_short_reads, memory_short_writes, summary_updated, memory_short_pruned
  - memory_long_reads, memory_long_writes, memory_long_pruned

  - Feature flags:
    - LC_RAG_ENABLED: optional LangChain RetrievalQA backend for grounded QA
    - ROUTER_ENABLED: routes intents (qa, pii_detect, risk_score, other) using simple rules
  - Request fields:
    - question: string (min 3)
    - grounded: boolean (default false)
    - user_id: optional string
    - intent: optional ("auto"|"qa"|"pii_detect"|"risk_score"|"other"); default "auto"
- POST /research — multi-step research pipeline with auditing; step RBAC applies

## Router Agent

- Feature-flag: ROUTER_ENABLED (default false)
- Intent options: qa | pii_detect | risk_score | other
- Behavior when enabled:
  - If intent not provided or set to "auto", the router picks an intent using simple rules (see docs/agents.md).
  - For qa + grounded=true, RAG citations are returned as before, and LC_RAG_ENABLED can switch the backend.
- Audit enrichment: router_backend and router_intent are included in the /query response audit field.
- When intent=pii_detect, the answer summarizes detections and the audit includes pii_entities_count, pii_types, and pii_counts.


See Swagger (/docs) for full request/response schemas and try-it-out.
