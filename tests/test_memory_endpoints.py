import os
import tempfile

from fastapi.testclient import TestClient

# Ensure short memory DB path is writable in tests
TMPDIR = tempfile.mkdtemp()
os.environ["MEMORY_DB_PATH"] = os.path.join(TMPDIR, "mem_short.db")

from app.main import app

client = TestClient(app)


def test_short_memory_endpoints_requires_role():
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    # guest forbidden
    r = client.get("/memory/short", params={"user_id": "u", "session_id": "s"})
    assert r.status_code == 403
    r = client.delete("/memory/short", params={"user_id": "u", "session_id": "s"})
    assert r.status_code == 403


def test_long_memory_endpoints_requires_role():
    os.environ["MEMORY_LONG_ENABLED"] = "true"
    r = client.get("/memory/long", params={"user_id": "u"})
    assert r.status_code == 403
    r = client.delete("/memory/long", params={"user_id": "u"})
    assert r.status_code == 403


def test_short_memory_list_and_clear():
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    headers = {"X-User-Role": "analyst"}
    # add some context via /query
    client.post("/query", json={"question": "hello", "user_id": "u", "session_id": "s"})
    # list
    r = client.get(
        "/memory/short", params={"user_id": "u", "session_id": "s"}, headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert "turns" in data and isinstance(data["turns"], list)
    # clear
    r2 = client.delete(
        "/memory/short", params={"user_id": "u", "session_id": "s"}, headers=headers
    )
    assert r2.status_code == 200
    assert r2.json()["cleared"] is True


def test_long_memory_list_and_clear():
    os.environ["MEMORY_LONG_ENABLED"] = "true"
    headers = {"X-User-Role": "admin"}
    # stimulate long memory via /query
    client.post(
        "/query",
        json={
            "question": "Tell me something long enough to ingest into memory store because it exceeds fifty characters in length.",
            "user_id": "lu",
        },
    )
    r = client.get("/memory/long", params={"user_id": "lu"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("facts", []), list)
    r2 = client.delete("/memory/long", params={"user_id": "lu"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["cleared"] is True
