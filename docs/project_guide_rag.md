# Project Guide RAG and Solution Architect Mode

Purpose
- Turn this repo into a self-guided product tour and solution architect assistant by using its own documentation as the RAG corpus.
- Enable:
  - Learning about AI architecture patterns and this project’s components
  - Brainstorming adaptations and implementation steps for company use cases
  - Mapping use cases to endpoints/agents/configs in this repo
  - Recruiting contributors by identifying gaps and proposing structured issues

Motivation
- Leverages grounded QA with citations, agentic workflows, auditability, and determinism.
- Low lift: ingest local docs; add a prompt profile and a mode flag.
- High value: onboarding, discovery, and contribution funnel.

Scope and features
- Phase A: Docs ingestion + Project Guide QA
  - Expand ingestion to include docs/, README.md, prompts/ notes, examples/.
  - Add a “Project Guide” mode flag (payload: guide=true) to switch to the project_guide prompt style, and enforce grounded=true for citations.
  - Answer style/prompt structure:
    - Summary of the answer
    - Referenced docs with file paths (citations)
    - Next steps and relevant env flags/configs

- Phase B: Brainstorm and solution mapping
  - Add a prompt profile “project_guide_brainstorm”:
    - Ask clarifying questions about the company use case and constraints
    - Suggest components to use (endpoints/services/agents)
    - Provide a quick plan with files to touch and flags to set

- Phase C: Gap detection and contributor funnel
  - Compare user needs to the Roadmap and current features
  - Propose “contribution ideas” and generate a GitHub-ready issue draft:
    - Title, description, acceptance criteria, files to modify, tests to add
  - Return the draft for copy-paste or a future /contribute endpoint

- Phase D: Patterns catalogue
  - Maintain a small library of “patterns”:
    - Regulated PII intake, audit-heavy LLM interactions, cost monitoring, router-driven use case routing
  - Link patterns to code pointers, env vars, and example cURL

Initial implementation plan (minimal)
- Ingestion: set DOCS_PATH to include ./docs and README.md
- Router/Endpoint: keep /query as-is; add a guide flag to payload to select the project_guide prompt and enforce grounded=true
- Prompt: add prompts/query_guide.yaml (or extend prompts/query.yaml) that outputs Summary, References, Next steps, Relevant configs
- Testing (later):
  - Ask “How does the router work?” and expect citations from docs/router.md
  - Ask “How to enable PII locales?” with citations from docs/pii.md and README

Future enhancements
- Tag-aware retrieval (annotate docs with topics and filter during retrieval)
- /router/preview endpoint to show intent decisions with rules and reasons
- Draft issue generator endpoint that returns suggested GitHub issue markdown

Risks and considerations
- Keep responses deterministic; avoid external calls
- Ensure RBAC and grounded rules remain unchanged; guide mode should not bypass policies
- Maintain auditability: store guide flag, prompt version, and citations in audit

Operational notes
- Implement behind a feature flag (PROJECT_GUIDE_ENABLED) to avoid impacting existing flows during manual QA.
- Document usage with cURL examples and a short README section once shipped.
