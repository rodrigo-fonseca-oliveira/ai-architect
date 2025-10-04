import hashlib
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from db.models import Audit


def make_hash(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    h = hashlib.sha256()
    h.update(value.encode("utf-8"))
    return h.hexdigest()


def write_audit(db: Session, **kwargs) -> Audit:
    # Map incoming fields and default created_at
    record = Audit(
        request_id=kwargs.get("request_id"),
        endpoint=kwargs.get("endpoint"),
        user_id=kwargs.get("user_id"),
        created_at=datetime.utcnow(),
        tokens_prompt=kwargs.get("tokens_prompt"),
        tokens_completion=kwargs.get("tokens_completion"),
        cost_usd=kwargs.get("cost_usd"),
        latency_ms=kwargs.get("latency_ms"),
        compliance_flag=kwargs.get("compliance_flag", False),
        prompt_hash=kwargs.get("prompt_hash"),
        response_hash=kwargs.get("response_hash"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
