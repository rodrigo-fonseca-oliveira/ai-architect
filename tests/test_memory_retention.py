import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_module(module):
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    os.environ["MEMORY_LONG_ENABLED"] = "true"


def test_short_memory_retention_and_cap(tmp_path):
    os.environ["MEMORY_DB_PATH"] = str(tmp_path / "short.db")
    os.environ["SHORT_MEMORY_RETENTION_DAYS"] = "1"
    os.environ["SHORT_MEMORY_MAX_TURNS_PER_SESSION"] = "3"
    headers = {"X-User-Role": "analyst"}
    # add turns via /query; simulate multiple messages
    for i in range(5):
        client.post(
            "/query",
            json={
                "question": f"msg {i} with some content that is long enough to be processed.",
                "user_id": "u1",
                "session_id": "s1",
            },
        )
    # list turns should be capped to 3
    r = client.get(
        "/memory/short", params={"user_id": "u1", "session_id": "s1"}, headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("turns", []), list)
    # turns are returned as role/content pairs; our cap applies in DB per-turn basis when enforcing
    assert len(data["turns"]) <= 3
    # audit includes pruned count
    assert "memory_short_pruned" in data["audit"]
    assert isinstance(data["audit"]["memory_short_pruned"], int)


def test_long_memory_retention_and_maxfacts():
    os.environ["MEMORY_LONG_MAX_FACTS"] = "2"
    os.environ["MEMORY_LONG_RETENTION_DAYS"] = "1"
    headers = {"X-User-Role": "admin"}
    uid = "u2"
    # ingest 3 facts via /query answers; ensure sentences > 50 chars
    for i in range(3):
        q = f"Please provide an elaborate statement number {i} that will definitely exceed fifty characters in its length to be ingested."
        client.post("/query", json={"question": q, "user_id": uid})
    # export
    r = client.get("/memory/long/export", params={"user_id": uid}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    facts = body.get("facts", [])
    assert len(facts) <= 2  # max facts enforced
    # audit includes pruned count and export fields present
    assert "memory_long_pruned" in body["audit"]
    if facts:
        f0 = facts[0]
        assert "id" in f0 and "text" in f0 and "created_at" in f0 and "metadata" in f0
        assert "embedding_present" in f0 and "embedding_dim" in f0
    # import roundtrip to another user
    r2 = client.post(
        "/memory/long/import",
        params={"user_id": uid + "_copy"},
        json={"facts": [{"text": f.get("text", "")} for f in facts]},
        headers=headers,
    )
    assert r2.status_code == 200
    rb = r2.json()
    assert rb.get("imported", 0) == len(facts)
    assert "memory_long_pruned" in rb["audit"]
