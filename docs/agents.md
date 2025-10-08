# Agents

Architect agent and community loop
- The Architect agent can propose features when it detects gaps between a user goal and current capabilities (e.g., a new endpoint or a router rule).
- Users can copy the proposal (summary, steps, flags) into a GitHub issue; see docs/llm_agent_streaming_prompts.md for a ready-to-use prompt set.
- This closes the loop between learning, brainstorming, and contribution, keeping the repo a living reference architecture.

## Research Agent

- Endpoint: POST /research (analyst/admin; per-step RBAC applies)
- Steps:
  1) search(topic) -> [{title, url}]
  2) fetch(urls) -> [{url, text}]
  3) summarize(docs) -> findings: [{title, summary, url}]
  4) risk_check(topic, findings) -> flagged: bool (uses DENYLIST)
- Config:
  - AGENT_LIVE_MODE (default: false) — when true, fetch performs real HTTP GETs (limited)
  - AGENT_URL_ALLOWLIST (comma-separated prefixes) — restricts live fetch to allowed domains/prefixes
  - DENYLIST (comma-separated terms) — flags risky research content in risk_check
- RBAC:
  - fetch/search/summarize: analyst+
  - risk_check: guest+
- Audit: steps include {name, inputs, outputs.preview, latency_ms, hash, timestamp}

## Policy Navigator Agent

- Endpoint: POST /policy_navigator (analyst/admin)
- Behavior:
  1) Decompose policy question into sub-questions (max POLICY_NAV_MAX_SUBQS, default 3)
  2) Retrieve citations per sub-question using existing retriever
  3) Synthesize a concise recommendation referencing evidence
- Config:
  - POLICY_NAV_ENABLED (default: true)
  - POLICY_NAV_MAX_SUBQS (default: 3)
- Audit: includes step entries for decompose, retrieve, synthesize with inputs/outputs preview and latency

## PII Remediation Agent

- Endpoint: POST /pii_remediation (analyst/admin)
- Behavior:
  1) Detect PII entities in the input text
  2) Retrieve relevant remediation guidance (when grounded=true)
  3) Synthesize actionable redactions and optional code snippets
- Config:
  - PII_REMEDIATION_ENABLED (default: true)
  - PII_REMEDIATION_INCLUDE_SNIPPETS (default: true)
- Output: remediation items per type, optional citations and snippets
