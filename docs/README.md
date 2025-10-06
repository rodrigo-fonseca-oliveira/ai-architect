# Documentation Index

Start here to explore AI Architect. This index complements the product-focused root README and serves as the corpus for the Architect agent (RAG grounding).

Entry points
- ai-architect-launch.md: launch scope, UX goals, and checklist
- architecture_index.md: orientation for the Architect use case and system map
- components.md: mapping of files to features and services
- api.md: REST endpoints and schemas
- deploy.md: local and cloud deployment notes

Core topics
- rag.md: retrieval configuration, flags, and ingestion workflow
- rag_vector_backends.md: vector backends roadmap and env toggles
- project_guide_rag.md: behavior spec for Project Guide and Architect modes
- router.md, router_rules.md: routing behavior and configuration
- memory.md: short/long memory behavior and endpoints
- observability.md: metrics, dashboards, and logs
- security.md: RBAC, PII, and retention
- ml.md, mlops_plan.md: MLflow, drift, and lifecycle
- testing.md: local tests, e2e flows, and CI tips

Artifacts and references
- data_card.md, model_card.md: documentation templates
- grafana/ai-monitor-dashboard.json: prebuilt Grafana dashboard
- openapi.yaml: exported API schema

Notes
- Docs under docs/ and the root README are ingested when DOCS_PATH points to the repository. See rag.md for ingestion and determinism notes.
