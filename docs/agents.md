# Router Agent

The Router Agent is a simple, feature-flagged component that selects an intent for a /query request.

- Feature flag: ROUTER_ENABLED (default: false)
- Backend: rules-based (rules_v1)
- Possible intents:
  - qa: question answering (RAG-backed when grounded=true)
  - pii_detect: detect presence of PII in the prompt
  - risk_score: assess risk-related questions
  - other: fallback

Routing rules (rules_v1):
- If grounded=true → qa
- If the question contains PII-like terms (e.g., "ssn", "social security", "credit card", "cc number", "email", "pii", "phone number") → pii_detect
- If the question contains risk keywords (e.g., "risk", "severity", "score", "risk score", "impact") → risk_score
- Otherwise → qa

Audit metadata:
- When ROUTER_ENABLED=true, the /query audit includes:
  - router_backend: "rules_v1"
  - router_intent: selected intent (qa|pii_detect|risk_score|other)

Extending the router:
- Edit app/services/router.py to add new intents or refine rules.
- Consider extracting rules to a YAML/JSON config for dynamic updates.
- Future: replace with a learned model or LLM classifier (guarded, cost-aware).

Observability:
- router_intent and rag_backend are included in the /query audit row for analytics.
- You can also add them to structured logs (see below) for centralized log analysis.
