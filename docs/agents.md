# Agents

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
