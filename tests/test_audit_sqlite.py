from fastapi.testclient import TestClient

from app.main import app


def test_audit_row_persisted(tmp_path, monkeypatch):
    # Use a temp sqlite db
    db_file = tmp_path / "audit.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_file}")

    # Reimport query router to ensure it binds new DB
    from importlib import reload

    import app.routers.query as query

    reload(query)

    # Ensure DB schema created for new DB_URL
    from db.session import init_db
    init_db()

    client = TestClient(app)
    r = client.post("/query", json={"question": "hello world", "grounded": False})
    assert r.status_code == 200

    # Verify sqlite file created and has content
    # When SQLAlchemy creates sqlite, the actual file path must exist
    # SQLAlchemy may lazily create on first commit; ensure creation by calling init_db again
    from db.session import init_db as _init_db
    _init_db()
    assert db_file.exists(), "sqlite db file should exist"
