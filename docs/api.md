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
- POST /query — RAG-like simple query; grounded queries require analyst/admin
- POST /research — multi-step research pipeline with auditing; step RBAC applies

See Swagger (/docs) for full request/response schemas and try-it-out.
