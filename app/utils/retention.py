import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import Audit


def sweep_audit(db: Session, days: int | None = None) -> int:
    if days is None:
        try:
            days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
        except ValueError:
            days = 30
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = db.query(Audit).filter(Audit.created_at < cutoff)
    count = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return count
