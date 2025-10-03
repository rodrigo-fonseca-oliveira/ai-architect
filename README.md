
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

`architecture/ai_monitor_diagram.png` (add a PNG or Mermaid later)

---

## 3) Quickstart

```bash
# 0) Clone & env
git clone https://github.com/<you>/ai-risk-monitor
cd ai-risk-monitor
cp .env.example .env  # fill in keys if using a hosted LLM (or start with stub)

# 1) Run locally
docker compose up --build

# 2) Smoke test
curl -X POST localhost:8000/query -H "Content-Type: application/json" \
  -d '{"question":"What is GDPR?", "grounded": true}'
curl localhost:8000/metrics
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
  Input: `{ topic: str, steps?: ["search","fetch","summarize"] }`
  Output: `{ findings[], sources[], audit_trace[], request_id }`

* `POST /predict`
  Input: `{ features: {...} }`
  Output: `{ prediction, model_version, request_id }`

* `GET /metrics` → Prometheus text (latency, tokens, cost, requests)

* `GET /healthz` → liveness probe

---

## 6) Observability, Audit, & Cost

* **Structured JSON logs** with `request_id` (propagated)
* **Audit DB row** per request: timestamps, role, prompt/resp hashes, flags
* **Token & cost** estimator (per model) aggregated by user/day
* **Denylist** (e.g., “SSN”, “PHI”) → `compliance_flag=true` in audit row
* **Retention** via `LOG_RETENTION_DAYS` (cron or startup sweep)

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
* **RBAC placeholder**: roles (`admin`, `analyst`, `guest`) enforced in routers
* **Data Card & Model Card** in `docs/` (templated Markdown)
* **Prompt Registry** in `prompts/*.yaml` (versioned, code-reviewed)

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
  * `python ml/train.py` with small data (fast)
  * Optionally push “candidate model” tag if metrics ≥ baseline
* (Optional) CD: deploy container to Render/Fly.io/Cloud Run (later)

---

## 12) Demo Script (90 seconds)

1. `docker compose up` → hit `/healthz`
2. `POST /query` with grounded=true → show citations + cost
3. `GET /metrics` → point out latency, tokens, cost
4. Open `audit` table → show request row (hashes, flags, role)
5. Run `python ml/drift.py` → show drift flag → (optional) retrain action

---

## 13) Known Limitations

* Local vector store (Chroma/FAISS); swap for managed in prod
* Cost estimator approximates vendor pricing; not real billing
* RBAC is illustrative only; integrate with real IdP in prod
* Agent uses public sources; add Evals before production use

---

## 14) Roadmap (Weekend Plan ✅ / Later ⭐)

### Phase 0 — Bootstrap (Day 1)

* [ ] FastAPI app skeleton + `/healthz`
* [ ] JSON logger with `request_id`
* [ ] SQLite DB + `audit` table
* [ ] `/query` using a **stub LLM** (no external calls)
* [ ] Token/cost estimator (mock) + `/metrics`
* [ ] Basic tests (router + audit write)
* [ ] CI: ruff + pytest

### Phase 1 — Core Value (Day 2)

* [ ] RAG: ingest 2–3 PDFs (GDPR summary, AWS docs), FAISS/Chroma
* [ ] `/query` returns **citations** (page/snippet)
* [ ] Denylist check + `compliance_flag`
* [ ] Retention sweeper (delete audit rows older than `LOG_RETENTION_DAYS`)
* [ ] README architecture diagram + screenshots (CI, logs, MLflow UI)

### Phase 2 — Agent & MLflow (Stretch)

* [ ] `/research`: search → fetch → summarize → risk_check
* [ ] Agent **step audit** (tool name, args, latency, hash)
* [ ] ML: `ml/train.py` → MLflow; register best model
* [ ] `/predict` pulls model from MLflow registry
* [ ] `ml/drift.py` (PSI/KS) + “retrain recommended” flag
* [ ] CI runs tiny `train.py` and `drift.py` on PR

### Phase 3 — Polish & Wow (Later)

* [ ] Role-based access checks (admin/analyst/guest)
* [ ] Prompt registry (`prompts/*.yaml`) + loader
* [ ] Plotly mini dashboard (cost/day, drift status)
* [ ] Dockerized one-click deploy (Render/Fly/Cloud Run)
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

---

### Tips for implementation with refact.ai

* Start from the **Phase 0** checklist; open small PRs (“feat: audit table,” “feat: /query stub,” “chore: CI”).
* Generate boilerplate with the agent; keep **commits clean** and **PR descriptions crisp**.
* Add **screenshots** (CI run, MLflow UI, /metrics curl) even if you use local stubs first.
* If time is tight, ship **Phase 0 + half of Phase 1**; the README and roadmap will still look very “architect-level.”

If you want, I can also draft the `.env.example`, `ci.yml`, and a minimal `main.py` + `/query` stub you can paste in to hit the ground running.
