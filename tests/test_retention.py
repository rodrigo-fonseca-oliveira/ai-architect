from datetime import datetime, timedelta

from db.session import get_session, init_db
from db.models import Audit
from app.utils.retention import sweep_audit


def test_sweep_audit(tmp_path, monkeypatch):
    db_path = tmp_path / "audit.db"
    if db_path.exists():
        db_path.unlink()
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    init_db()
    db = get_session()
    try:
        # Clean any existing rows to ensure isolation
        db.query(Audit).delete()
        db.commit()

        # Insert two rows: one old, one recent
        old_row = Audit(
            request_id="r-old",
            endpoint="/query",
            created_at=datetime.utcnow() - timedelta(days=365),
        )
        new_row = Audit(
            request_id="r-new",
            endpoint="/query",
            created_at=datetime.utcnow(),
        )
        db.add_all([old_row, new_row])
        db.commit()

        deleted = sweep_audit(db, days=30)
        assert deleted == 1

        remaining = db.query(Audit).count()
        assert remaining == 1
    finally:
        db.close()
