import os
from typing import Literal

Intent = Literal["qa", "pii_detect", "risk_score", "policy_navigator", "pii_remediation", "other"]


def is_enabled() -> bool:
    return os.getenv("ROUTER_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def route_intent(question: str, grounded: bool) -> Intent:
    # Simple rules v2
    q = (question or "").lower()
    # Grounded queries are always QA
    if grounded:
        return "qa"
    # PII flows: remediation hints
    if any(t in q for t in ("pii", "email", "ssn", "social security", "credit card", "iban", "ipv4", "ipv6", "passport", "phone number")):
        if any(w in q for w in ("redact", "mask", "anonymiz", "remediat")):
            return "pii_remediation"
        return "pii_detect"
    # Risk
    if any(t in q for t in ("risk", "severity", "score", "risk score", "impact", "hazard", "danger")):
        return "risk_score"
    # Policy Navigator
    if any(t in q for t in ("policy", "regulation", "regulatory", "compliance", "gdpr", "hipaa")):
        return "policy_navigator"
    # Default
    return "qa"


def get_backend_meta() -> str:
    return "rules_v1"
