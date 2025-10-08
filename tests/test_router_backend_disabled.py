from fastapi.testclient import TestClient

from app.main import app


def test_router_backend_marker_when_disabled(monkeypatch):
    # Explicitly disable router
    monkeypatch.setenv("ROUTER_ENABLED", "false")
    client = TestClient(app)
    r = client.post("/query", json={"question": "Hello", "grounded": False})
    assert r.status_code == 200
    aud = r.json().get("audit", {})
    assert aud.get("router_backend") in (None, "simple")
    assert aud.get("router_intent") in (None, "qa")
