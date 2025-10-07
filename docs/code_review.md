AI Architect — Code Review (Session 1)

Overview and scope
- Purpose: Baseline review of code quality, structure, and doc-to-code alignment. No application code changes in this session.
- Deliverables: This living report, a checklist index, and a baseline test run summary.

Repository map (high level)
- FastAPI app: app/
  - Routers: app/routers/* (query, research, predict, pii, pii_remediation, risk, memory, metrics, architect, architect_stream, architect_ui, policy)
  - Services: app/services/* (langchain_rag, router, llm_client, policy_navigator, architect_agent, architect_schema, pii_detector, pii_remediation, mlflow_client, prompt_runner)
  - Utils: app/utils/* (logger, metrics, audit, rbac, cost, prompts, exceptions, retention)
  - Memory backends: app/memory/* (short_memory, long_memory)
  - Schemas: app/schemas/* (research, predict)
  - Entry point: app/main.py
- Persistence: db/* (models, session)
- ML: ml/* (train.py, drift.py, data/*.csv)
- OpenAPI: docs/openapi.yaml (generated via scripts/export_openapi.py)
- Docs: docs/*.md
- Tests: tests/* (broad functional coverage by component and endpoint)

API and behavior alignment checklist (initial)
- Endpoints implemented vs docs/openapi.yaml
  - GET /healthz: implemented (metrics router) — OK
  - GET /metrics: implemented with optional token (X-Metrics-Token) — OK
  - POST /query: implemented — OK
  - POST /research: implemented — OK
  - POST /predict: implemented — OK
  - POST /pii: implemented — OK
  - POST /risk: implemented — OK
  - Memory endpoints (get/delete short, get/delete long, export/import, status): implemented — OK
  - POST /policy_navigator: implemented — OK
  - POST /pii_remediation: implemented — OK
  - Architect/Architect UI/stream endpoints exist but are intentionally not exposed in openapi.yaml (consider documenting explicitly) — NOTE

Cross-cutting behavior
- Request ID middleware present; exceptions mapped to JSON via app/utils/exceptions.py — aligns with docs/api.md.
- RBAC: parse_role(header X-User-Role), require_role helper; grounded query requires analyst/admin — aligns with docs/security.md and docs/api.md.
- Observability: Prometheus counters/histograms exposed; /metrics excluded from request counters; optional token — aligns with docs/observability.md.
- Audit trail: db/models.Audit and utils/audit.write_audit used best-effort in routers.

Quality notes (initial scan)
- Error handling: consistent JSON error envelope via exception handlers — good.
- Logging: JSON logger with request_id propagation — good; consider structured fields for key audit extras where relevant.
- Configuration: env-first, flags throughout; sensible defaults; feature flags for router, RAG, LLM, memory — good.
- Security: RBAC enforced across sensitive endpoints; /metrics optional token; no secrets in code — good. Consider rate limiting/abuse guards if exposed publicly.
- Performance: synchronous CPU-bound work mostly light; RAG path uses filesystem scans; long operations (MLflow, vector ops) are not on request path except predict — acceptable for reference implementation.
- Testing: extensive functional tests; includes router rules, RAG flags, metrics, PII, risk, memory, LLM audit, drift, MLflow train — strong coverage by behavior.

Doc vs code drift (early findings)
- Architect endpoints (/architect, /architect/stream, /architect/ui) exist and are tested but not present in docs/openapi.yaml — consider adding to docs (or explicitly marking as experimental).
- scripts/ingest_docs.py is now a validation no-op (no vector store); docs mention LangChain mode and ingestion as optional — OK but clarify in docs that ingestion simply validates docs path in current version.
- Some docs reference vector store specifics historically; current code paths rely on a lightweight filesystem scan in services/langchain_rag.py — consider updating docs/rag.md accordingly.
- Metrics names in docs: app_requests_total, app_request_latency_seconds, app_tokens_total, app_cost_usd_total — match code — OK.

Security and privacy posture (initial)
- PII: /pii and /pii_remediation enforce analyst/admin; pii_detector used with best-effort; audit includes counts and types — OK.
- RBAC: step-level checks for /research; grounded queries restricted — OK.
- Retention: memory docs describe env knobs; endpoints expose status and export/import — OK.

Testing baseline (to be filled after running pytest)
- Command: . .venv/bin/activate && pytest -q
- Result: TEST_RESULTS_PLACEHOLDER

Recommendations (priority draft)
- Add architect endpoints to OpenAPI/docs or explicitly mark as experimental in docs.
- Clarify RAG ingestion story in docs (current stub scans DOCS_PATH for .md/.txt and falls back to synthetic citation).
- Consider adding minimal health for DB (e.g., /metrics includes audit DB status gauge) — optional.
- Provide a docker-compose override or Make target to run tests in a container for consistency across machines (optional).

Next steps checklist
- [ ] Run full test suite and record baseline in this file.
- [ ] Produce endpoint-by-endpoint delta table (docs vs code) with parameters/status codes.
- [ ] Deeper review: memory persistence guarantees and pruning semantics; long-memory eviction correctness.
- [ ] Deeper review: router rule precedence and default behavior; document examples.
- [ ] Deeper review: MLflow integration and predictable local runs.

Session log
- Created by: code review session 1
- Date: PLACEHOLDER_DATE
