import hashlib
from typing import Optional


def make_hash(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    h = hashlib.sha256()
    h.update(value.encode("utf-8"))
    return h.hexdigest()
