import os
from fastapi.testclient import TestClient

from app.main import app


def test_research_live_mode_respects_allowlist(monkeypatch):
    # Enable live mode but restrict allowlist to a domain that does NOT match example.com
    monkeypatch.setenv("AGENT_LIVE_MODE", "true")
    monkeypatch.setenv("AGENT_URL_ALLOWLIST", "https://allowed.test")

    client = TestClient(app)

    r = client.post(
        "/research",
        json={
            "topic": "network test",
            "steps": ["search", "fetch"],
        },
        headers={"X-User-Role": "analyst"},
    )
    assert r.status_code == 200
    data = r.json()
    # Find the fetch step and ensure count is 0 since allowlist doesn't match example.com
    fetch_steps = [s for s in data.get("steps", []) if s.get("name") == "fetch"]
    assert fetch_steps, "fetch step missing in audit steps"
    out = fetch_steps[0].get("outputs", {})
    # outputs.preview contains a string preview that includes count
    # In our agent._audit_step we put outputs={"preview":str(outputs)[:200]} where outputs was {"count": len(contents)}
    # So we validate that no contents were fetched
    # If preview contains a dict-like string, simply check for 'count': 0 presence
    assert "'count': 0" in out.get("preview", "") or out.get("preview", "").endswith("0}")
