import os
from typing import Dict

# Simple heuristic risk scorer with optional ML flag for future use.


RISK_KEYWORDS = {
    "high": [
        "breach",
        "violation",
        "non-compliant",
        "lawsuit",
        "penalty",
        "critical",
        "severe",
    ],
    "medium": [
        "exposure",
        "incident",
        "warning",
        "vulnerability",
        "moderate",
    ],
    "low": [
        "info",
        "advisory",
        "minor",
        "low",
    ],
}


def heuristic_score(text: str) -> Dict[str, object]:
    t = (text or "").lower()
    score = 0.0
    label = "low"
    rationale = []

    if any(k in t for k in RISK_KEYWORDS["high"]):
        score = 0.9
        label = "high"
        rationale.append("matched high-risk keywords")
    elif any(k in t for k in RISK_KEYWORDS["medium"]):
        score = 0.6
        label = "medium"
        rationale.append("matched medium-risk keywords")
    else:
        score = 0.2
        label = "low"
        rationale.append("no strong risk indicators")

    return {"label": label, "value": score, "rationale": "; ".join(rationale)}


def score(text: str) -> Dict[str, object]:
    # Future: if RISK_ML_ENABLED=true and model available, call ml_score
    if os.getenv("RISK_ML_ENABLED", "false").lower() in ("1", "true", "yes", "on"):
        # Placeholder: still use heuristic for now
        pass
    return heuristic_score(text)
