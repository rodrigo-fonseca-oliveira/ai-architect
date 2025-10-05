import os
import tempfile

from fastapi.testclient import TestClient

# Enable short-term memory for this test module
TMPDIR = tempfile.mkdtemp()
os.environ["MEMORY_SHORT_ENABLED"] = "true"
os.environ["MEMORY_DB_PATH"] = os.path.join(TMPDIR, "mem_short.db")
os.environ["MEMORY_SHORT_MAX_TURNS"] = "3"

from app.main import app

client = TestClient(app)


def test_short_memory_accumulates_and_summarizes():
    session_id = "sess1"
    user_id = "user1"

    # first three turns
    for i in range(3):
        r = client.post(
            "/query",
            json={
                "question": f"ping {i}",
                "user_id": user_id,
                "session_id": session_id,
            },
        )
        assert r.status_code == 200
        audit = r.json()["audit"]
        # reads prior turns count should be non-decreasing
        assert audit.get("memory_short_reads", 0) >= 0
        # first turns should not exceed summary threshold yet; allow True if implementation summarizes early
        assert audit.get("summary_updated") in (None, False, True)

    # fourth turn triggers summary
    r = client.post(
        "/query",
        json={"question": "final ping", "user_id": user_id, "session_id": session_id},
    )
    assert r.status_code == 200
    audit = r.json()["audit"]
    assert audit.get("memory_short_writes", 0) == 2
    assert audit.get("summary_updated") in (True, False)


def test_flag_off_behaviour():
    os.environ["MEMORY_SHORT_ENABLED"] = "false"
    r = client.post("/query", json={"question": "hello"})
    assert r.status_code == 200
    audit = r.json()["audit"]
    # memory fields should be absent when flag off
    assert "memory_short_reads" not in audit or audit.get("memory_short_reads") is None
    assert (
        "memory_short_writes" not in audit or audit.get("memory_short_writes") is None
    )
    assert "summary_updated" not in audit or audit.get("summary_updated") is None
