import os
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_memory_status_requires_admin():
    r = client.get("/memory/status")
    assert r.status_code == 403
    r2 = client.get("/memory/status", headers={"X-User-Role": "analyst"})
    assert r2.status_code == 403


def test_memory_status_happy_path(tmp_path):
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    os.environ["MEMORY_LONG_ENABLED"] = "true"
    os.environ["MEMORY_DB_PATH"] = str(tmp_path / "short.db")
    # do a couple of interactions to create some memory
    client.post("/query", json={"question": "hello world with enough characters to store in memory context for testing.", "user_id": "sx", "session_id": "s1"})
    client.post("/query", json={"question": "another hello long long long question to create turns", "user_id": "sx", "session_id": "s1"})
    # status
    r = client.get("/memory/status", headers={"X-User-Role": "admin"})
    assert r.status_code == 200
    data = r.json()
    assert "config" in data and isinstance(data["config"], dict)
    assert "short_memory" in data and "sessions" in data["short_memory"]
    assert "long_memory" in data and "users" in data["long_memory"]
    assert "counters" in data and "memory_short_pruned_total" in data["counters"]
    assert "audit" in data and data["audit"].get("endpoint") == "/memory/status"
