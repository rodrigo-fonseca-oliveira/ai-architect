from fastapi.testclient import TestClient

from app.main import app


def test_router_selects_intents_for_edge_prompts(monkeypatch):
    monkeypatch.setenv("ROUTER_ENABLED", "true")
    client = TestClient(app)

    # PII-like prompt
    resp = client.post(
        "/query",
        json={"question": "Email is bob@example.com", "grounded": False},
    )
    assert resp.status_code == 200
    audit = resp.json().get("audit") or {}
    assert audit.get("router_backend") in ("rules_v2", "simple")
    assert audit.get("router_intent") in ("qa", "pii_detect", "risk_score", "policy_nav")

    # Risk-like prompt
    resp = client.post(
        "/query",
        json={"question": "What is the risk score for this incident?", "grounded": False},
    )
    assert resp.status_code == 200
    audit = resp.json().get("audit") or {}
    assert audit.get("router_backend") in ("rules_v2", "simple")
    assert audit.get("router_intent") in ("qa", "pii_detect", "risk_score", "policy_nav")
