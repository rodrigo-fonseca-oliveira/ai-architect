import re
from typing import Dict, List, Any

# Simple, deterministic PII detector using regex/heuristics.
# Returns masked previews and basic counts, no external calls.


def _mask(value: str, head: int = 2, tail: int = 2) -> str:
    if not value:
        return value
    if len(value) <= head + tail:
        return "*" * len(value)
    return value[:head] + "*" * (len(value) - head - tail) + value[-tail:]


def _luhn_check(num: str) -> bool:
    s = [int(ch) for ch in re.sub(r"\D", "", num)]
    total = 0
    double = False
    for d in reversed(s):
        if double:
            d = d * 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return total % 10 == 0 if s else False


PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+\d{1,3}[ -]?)?(?:\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    # IPv6 (simplified):
    "ipv6": re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b"),
    # IBAN (simplified, 15-34 alphanum starting with 2 letters):
    "iban": re.compile(r"\b[A-Za-z]{2}[0-9A-Za-z]{13,32}\b"),
    # Passport (generic heuristic: 7-9 alphanum):
    "passport": re.compile(r"\b[0-9A-Za-z]{7,9}\b"),
    # credit card: detect sequences of 13-19 digits separated by spaces or dashes; validate with Luhn
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
}


ACTIVE_DEFAULT = ["email", "phone", "ssn", "credit_card", "ipv4"]


def _active_types_from_env() -> List[str]:
    import os

    raw = os.getenv("PII_TYPES", ",".join(ACTIVE_DEFAULT))
    return [t.strip() for t in raw.split(",") if t.strip()]


def detect_pii(text: str) -> Dict[str, Any]:
    entities: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}

    active = set(_active_types_from_env())

    for ptype, pat in PATTERNS.items():
        if ptype not in active:
            continue
        for m in pat.finditer(text or ""):
            val = m.group(0)
            if ptype == "credit_card" and not _luhn_check(val):
                continue
            counts[ptype] = counts.get(ptype, 0) + 1
            entities.append(
                {
                    "type": ptype,
                    "value_preview": _mask(val),
                    "span": [m.start(), m.end()],
                }
            )

    types_present = sorted(list(counts.keys()))
    return {
        "entities": entities,
        "types_present": types_present,
        "counts": counts,
        "total": len(entities),
    }
