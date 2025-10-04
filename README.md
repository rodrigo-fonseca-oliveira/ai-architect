
# 🛡 AI Risk & Compliance Monitor (with RAG, Agent, and MLflow)

> A minimal reference platform for **safe, observable, and cost-aware** AI.
> FastAPI gateway with audit logs, token/cost tracking, drift checks, and modular endpoints for **LLM (RAG)**, **Agent pipeline**, and **ML model serving** (MLflow).

---

## 1) Problem Statement

Enterprises adopting GenAI need **traceability, governance, and cost visibility** before they scale. This project wraps AI calls with a lightweight **monitoring & compliance layer** and exposes production-ready patterns:

* LLM/RAG Q&A with grounding and **citations**
* **Agentic** multi-step pipeline with tool auditing
* **ML training/serving** with MLflow + drift checks
* **FinOps**: token & cost tracking, `/metrics`
* **Auditability**: request/response hashes, denylist flags, retention

---

## 2) High-Level Architecture

```
Client → FastAPI Gateway
         ├── /query     (LLM + optional RAG) ─┐
         ├── /research  (Agent pipeline)      ├─→ Audit DB (SQLite/Postgres)
         ├── /predict   (MLflow model)        ┘
         ├── /metrics   (Prometheus text)
         └── /healthz
    [Structured logs + Request IDs + Token/Cost tracker + RBAC stub]
```

Architecture (Mermaid)

```mermaid
flowchart TD
    A[Client] -->|HTTP| B[FastAPI Gateway]
    B --> C[/query]
    B --> D[/research]
    B --> E[/predict]
    B --> F[/metrics]
    B --> G[/healthz]

    C --> C1[LLM Stub / Gateway]
    C --> C2[RAG Retriever (Chroma)]
    C2 --> C3[(VectorStore)]

    D --> D1[Agent Orchestrator]
    D1 --> D2[Tools (search/fetch/summarize)]

    E --> E1[MLflow Client]
    E1 --> E2[(MLflow Registry)]

    B --> H[Audit Writer]
    H --> H1[(SQLite: audit)]

    B --> I[Cost Tracker]

    F --> J[Prometheus Metrics]

    subgraph Observability
      H
      I
      J
    end

    subgraph Data
      C3
      H1
      E2
    end
```

---

## 3) Quickstart

```bash
# 0) Clone & env
git clone https://github.com/<you>/ai-risk-monitor
cd ai-risk-monitor
cp .env.example .env  # fill in keys if using a hosted LLM (or start with local/stub embeddings)

# 1) Setup venv and install
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# 2) Ingest docs for RAG (Phase 1)
# Place a few .txt/.md (and now .pdf) files under DOCS_PATH (see .env). Example:
# A tiny sample is already included: examples/gdpr.txt and examples/gdpr.pdf
python scripts/ingest_docs.py

# 3) Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4) Smoke test
curl -X POST localhost:8000/query -H "Content-Type: application/json" \
  -d '{"question":"What is GDPR?", "grounded": true}'

# 5) Metrics
# Exposes Prometheus counters & histograms
curl localhost:8000/metrics | sed -n '1,80p'
```

---

## 4) Repo Layout

```
ai-risk-monitor/
  README.md
  LICENSE
  architecture/
    ai_monitor_diagram.png
  app/
    main.py
    routers/
      query.py        # /query  (LLM + RAG)
      research.py     # /research (agent)
      predict.py      # /predict (MLflow)
      metrics.py      # /metrics, /healthz
    services/
      llm_gateway.py
      rag_retriever.py
      agent.py
      mlflow_client.py
    utils/
      logger.py       # JSON logs + req_id
      audit.py        # hash inputs/outputs, write audit row
      cost.py         # token & $ estimation
      rbac.py         # placeholder role checks
    schemas/
      query.py
      research.py
      predict.py
  db/
    models.py         # SQLAlchemy models
    session.py
    migrations/       # (optional) alembic
  ml/
    data/             # synthetic or downloaded
    train.py          # logs to MLflow
    evaluate.py
    drift.py          # PSI/KS checks
    registry.md       # how to use MLflow registry
  prompts/
    query.yaml        # versioned prompt templates
    research.yaml
  tests/
    test_query.py
    test_audit.py
    test_predict.py
  infra/
    Dockerfile
    docker-compose.yml
  .github/workflows/
    ci.yml            # lint + tests + (optional) fast train
  .env.example
```

---

## 5) Endpoints

* `POST /query`
  Input: `{ question: str, grounded?: bool }`
  Output: `{ answer, citations[], request_id, tokens, cost_usd }`

* `POST /research`
  Input: `{ topic: str, steps?: ["search","fetch","summarize","risk_check"] }`
  Output: `{ findings[], sources[], steps[], audit }`

  Example:
  ```bash
  curl -X POST localhost:8000/research -H "Content-Type: application/json" \
    -d '{
      "topic": "Latest updates on GDPR and AI",
      "steps": ["search","fetch","summarize","risk_check"]
    }'
  ```

  Notes:
  - Deterministic, offline-friendly by default (AGENT_LIVE_MODE=false).
  - Step-level audit is included (name, inputs, outputs preview, latency, hash, timestamp).
  - Denylist terms flagged into audit.compliance_flag.
  - To enable live fetch, set `AGENT_LIVE_MODE=true` and optionally `AGENT_URL_ALLOWLIST` (comma-separated prefixes).

* `POST /predict`
  Input: `{ features: {...} }`
  Output: `{ prediction, model_version, request_id }`

  Example:
  ```bash
  # Train a tiny model (local MLflow)
  . .venv/bin/activate && python ml/train.py

  # Predict using latest run artifact
  curl -X POST localhost:8000/predict -H "Content-Type: application/json" \
    -d '{"features": {"f0": 0.1, "f1": -0.2, "f2": 0.3, "f3": 0.0, "f4": 0.2, "f5": -0.1, "f6": 0.0, "f7": 0.0}}'
  ```

* `GET /metrics` → Prometheus text (latency, tokens, cost, requests)

* `GET /healthz` → liveness probe

---

## 6) Observability, Audit, & Cost

* **Structured JSON logs** with `request_id` (propagated)
* **Audit DB row** per request: timestamps, role, prompt/resp hashes, flags
* **Token & cost** estimator (per model) aggregated by user/day
* **Denylist** (e.g., “SSN”, “PHI”) → `compliance_flag=true` in audit row
* **Retention** via `LOG_RETENTION_DAYS` (cron or on-demand sweep)

### Retention Sweeper
- Deletes audit rows older than `LOG_RETENTION_DAYS` (default: 30).
- Run it via VS Code task: “Sweep retention (audit)”, or CLI:
  - `. .venv/bin/activate && python scripts/sweep_retention.py`

---

## 7) ML Lifecycle (MLflow)

* `ml/train.py` trains a tiny model (e.g., churn) → logs params/metrics/artifacts
* Register best model → served by `/predict` via `mlflow_client.py`
* `ml/drift.py` runs **PSI/KS** drift check; if over threshold, writes a “retrain recommended” flag (and exits non-zero in CI if you want to gate promotion)

---

## 8) Agentic Pipeline

* Deterministic steps: `search → fetch → summarize → risk_check`
* **Tool calls audited** (name, args, latency, result hash)
* Safety hook blocks disallowed tools (documented in README)

---

## 9) Security & Governance

* **No secrets** in code; use `.env.example`
* **RBAC**: roles (`admin`, `analyst`, `guest`) enforced via `X-User-Role` header
  - /metrics: admin only
  - /predict: analyst/admin
  - /query: grounded=true requires analyst/admin; guest allowed grounded=false
  - /research: guest cannot use `fetch` step; analyst/admin allowed
* **Data Card & Model Card** in `docs/` (templated Markdown)
* **Prompt Registry** in `prompts/*.yaml` (versioned, code-reviewed). Load via `app.utils.prompts.load_prompt(name, version)`.

---

## 10) Local Dev Commands

```bash
# Format & lint
ruff check . && ruff format .
mypy app || true

# Tests
pytest -q

# ML quick run
python ml/train.py
python ml/drift.py --input ml/data/new_batch.csv --baseline ml/data/baseline.csv
```

---

## 11) CI/CD (GitHub Actions)

* **ci.yml** runs on PR & main:

  * Setup Python, install deps
  * Ruff + mypy + pytest
  * `python ml/train.py` with small data (fast) — logs params/metrics/artifacts to MLflow local path
  * `python ml/drift.py --baseline ml/data/baseline.csv --input ml/data/new_batch.csv` (deterministic drift check)
    - Non-fatal by default in CI via `|| true`; remove `|| true` to fail the build on drift > threshold
  * Optionally push “candidate model” tag if metrics ≥ baseline
* (Optional) CD: deploy container to Render/Fly.io/Cloud Run (later)

### Deploy on Render (Docker)
1. Push this repo to GitHub.
2. In Render, create a new Web Service and connect the repo.
3. Choose “Deploy from Docker” and keep Dockerfile at repo root.
4. Set environment variables (from `.env.example`), at minimum:
   - APP_ENV=production
   - LOG_LEVEL=INFO
   - EMBEDDINGS_PROVIDER=stub (or local/openai)
   - VECTORSTORE_PATH=/data/vectorstore (if you add a disk)
   - DOCS_PATH=/app/examples
   - DB_URL=sqlite:////data/audit.db (if you add a disk)
5. Health check path: `/healthz` (port 8000).
6. (Optional) Add a persistent disk and mount at `/data` for audit.db and vectorstore.
7. Click Deploy. The app should be reachable at your Render URL.

---

## 12) Demo Script (90 seconds)

1. `uvicorn app.main:app` → hit `/healthz`
2. `POST /query` with grounded=true → show citations + cost
3. `GET /metrics` → point out latency, tokens, cost
4. Open `audit` table → show request row (hashes, flags, role)
5. (Later) Run `python ml/drift.py` → show drift flag → (optional) retrain action

### Screenshots (what to capture)
- CI: GitHub Actions run for main showing green checks
- Logs: Run API and capture JSON logs
  - `. .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 | tee logs/app.log`
  - Open `logs/app.log` for a compact JSON log screenshot
- Metrics: `curl localhost:8000/metrics` and capture counters/histograms
- MLflow UI: launch with `mlflow ui --backend-store-uri ./.mlruns` then open http://127.0.0.1:5000 and capture

---

## 13) Known Limitations

* Local vector store (Chroma/FAISS); swap for managed in prod
* Cost estimator approximates vendor pricing; not real billing
* RBAC is illustrative only; integrate with real IdP in prod
* Agent uses public sources; add Evals before production use

---

## 14) Roadmap (Weekend Plan ✅ / Later ⭐)

### Phase 0 — Bootstrap (Day 1)

* [x] FastAPI app skeleton + `/healthz`
* [x] JSON logger with `request_id`
* [x] SQLite DB + `audit` table (persist audit rows)
* [x] `/query` using a **stub LLM** (no external calls)
* [x] Token/cost estimator (mock) + `/metrics`
* [x] Basic tests (routers + audit write)
* [x] CI: ruff + pytest

### Phase 1 — Core Value (Day 2)

* [x] RAG: ingest local docs with Chroma (scripts/ingest_docs.py)
* [x] `/query` returns **citations** (snippet + source) when `grounded=true`
* [x] Denylist check + `compliance_flag` (env-based)
* [x] Retention sweeper (delete audit rows older than `LOG_RETENTION_DAYS`)
* [x] README architecture diagram + screenshots (CI, logs, MLflow UI)

### Phase 2 — Agent & MLflow (Stretch)

* [x] `/research`: search → fetch → summarize → risk_check
* [x] Agent **step audit** (tool name, args, latency, hash)
* [x] ML: `ml/train.py` → MLflow (local) logs params/metrics/artifacts
* [x] `/predict` loads latest model from MLflow local store
* [x] `ml/drift.py` (PSI) + “retrain recommended” flag
* [ ] CI runs tiny `train.py` and `drift.py` on PR

### Phase 3 — Polish & Wow (Later)

* [x] Role-based access checks (admin/analyst/guest)
* [ ] Prompt registry (`prompts/*.yaml`) + loader
* [ ] Plotly mini dashboard (cost/day, drift status)
* [x] Dockerized one-click deploy (Render)
* [ ] Data Card & Model Card in `docs/`

---

## 15) Tech Stack

* **API**: FastAPI, Pydantic, Uvicorn
* **LLM/RAG**: Local stub → (optionally) OpenAI/Azure/OpenRouter + FAISS/Chroma
* **Agent**: simple orchestrator, `requests` for web fetch
* **ML**: scikit-learn, MLflow
* **DB**: SQLite (swap to Postgres)
* **Obs**: JSON logs + Prometheus `/metrics`
* **CI**: GitHub Actions; lint + tests + (optional) fast train

---

## 16) License

Apache-2.0 (or MIT). Add `LICENSE` file.


