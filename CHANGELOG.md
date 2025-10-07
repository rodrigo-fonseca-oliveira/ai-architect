# Changelog

## [0.9.0] - 2025-10-07

### Added

* `/architect` endpoint as unified meta-agent orchestrator for RAG, Agents, and MLflow.
* Architect UI with streaming and SSE support.
* Governance layer: audit logs, cost tracking, FinOps metrics.
* Observability stack with Prometheus and Grafana integration.
* Full documentation suite (`/docs`): API, RAG, Router, Risk, PII, Memory, Observability, and MLOps plans.
* RBAC implementation, PII detection, and risk scoring sub-agents.
* Prompt registry and deterministic retrieval pipeline.

### Changed

* Refactored `README.md` to center around the `/architect` endpoint.
* Reorganized project structure into modular components (`app/routers`, `app/services`, etc.).
* Unified routing logic and deterministic RAG paths.
* Updated CI workflows and Makefile for testing and OpenAPI export.
* Enhanced audit DB schema for cost and latency tracking.

### Fixed

* Streaming response stability issues in Architect UI.
* MLflow drift detection edge cases.
* Minor type and logging inconsistencies across routers.

---

## [0.1.0] - Initial Commit

### Added

* Initial FastAPI skeleton and basic `/query` endpoint.
* Early agentic and retrieval experimentation.
* Bootstrap for documentation, Makefile, and project scaffolding.

---

## 🧭 Maintaining the Changelog

To keep this file useful and accurate:

1. **For each new version tag**, add a section at the top following the format:

   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD
   ### Added
   - ...
   ### Changed
   - ...
   ### Fixed
   - ...
   ```

2. **Follow semantic versioning**:

   * **MAJOR**: Breaking changes or major refactor (`1.0.0` → `2.0.0`).
   * **MINOR**: New features, backward compatible (`0.9.0` → `0.10.0`).
   * **PATCH**: Fixes and small tweaks (`0.9.0` → `0.9.1`).

3. **Tag releases** in git:

   ```bash
   git tag -a v0.10.0 -m "Your summary here"
   git push origin v0.10.0
   ```

4. **Link to GitHub releases**: copy key highlights from each entry to the release description for visibility.

Keeping this file updated ensures transparency for contributors and users reviewing the project's
