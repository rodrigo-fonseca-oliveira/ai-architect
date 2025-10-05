from fastapi.testclient import TestClient

from app.main import app


def test_short_memory_clear_semantics_with_prior_turns(monkeypatch):
    monkeypatch.setenv("MEMORY_SHORT_ENABLED", "true")
    # cap turns per session to force pruning paths to be exercised
    monkeypatch.setenv("SHORT_MEMORY_MAX_TURNS_PER_SESSION", "5")
    client = TestClient(app)

    # Drive a couple of turns
    for q in ("hello", "world"):
        resp = client.post(
            "/query",
            json={
                "question": q,
                "user_id": "u",
                "session_id": "s",
            },
        )
        assert resp.status_code == 200

    # List (should show some turns)
    resp = client.get("/memory/short", params={"user_id": "u", "session_id": "s"}, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    turns_before = len(resp.json().get("turns") or [])
    assert turns_before >= 1

    # Clear
    resp = client.delete("/memory/short", params={"user_id": "u", "session_id": "s"}, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    cleared = resp.json().get("cleared")
    assert cleared is True
