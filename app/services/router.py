import os
from typing import Literal

Intent = Literal["qa", "pii_detect", "risk_score", "other"]


def is_enabled() -> bool:
    return os.getenv("ROUTER_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def route_intent(question: str, grounded: bool) -> Intent:
    # Simple rules v1
    lower = (question or "").lower()
    if grounded:
        return "qa"
    pii_terms = ["ssn", "social security", "credit card", "cc number", "email", "pii", "phone number"]
    risk_terms = ["risk", "severity", "score", "risk score", "impact"]
    if any(t in lower for t in pii_terms):
        return "pii_detect"
    if any(t in lower for t in risk_terms):
        return "risk_score"
    return "qa"


def get_backend_meta() -> str:
    return "rules_v1"
