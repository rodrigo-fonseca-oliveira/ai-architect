import json
from fastapi.testclient import TestClient

from app.main import app


def test_router_rules_precedence(monkeypatch):
    monkeypatch.setenv("ROUTER_ENABLED", "true")
    rules = {
        "rules": [
            {"intent": "qa", "keywords_any": ["policy"], "priority": 10},
            {"intent": "pii_detect", "keywords_any": ["policy", "pii", "ssn"], "priority": 100},
        ],
        "default_intent": "qa",
    }
    monkeypatch.setenv("ROUTER_RULES_JSON", json.dumps(rules))
    client = TestClient(app)
    resp = client.post("/query", json={"question": "Is policy about SSN?", "grounded": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"].get("router_intent") == "pii_detect"


def test_router_rules_default(monkeypatch):
    monkeypatch.setenv("ROUTER_ENABLED", "true")
    rules = {
        "rules": [
            {"intent": "risk_score", "keywords_any": ["danger"], "priority": 50}
        ],
        "default_intent": "qa",
    }
    monkeypatch.setenv("ROUTER_RULES_JSON", json.dumps(rules))
    client = TestClient(app)
    resp = client.post("/query", json={"question": "Hello world", "grounded": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"].get("router_intent") == "qa"


def test_router_backend_meta(monkeypatch):
    monkeypatch.setenv("ROUTER_ENABLED", "true")
    monkeypatch.delenv("ROUTER_RULES_JSON", raising=False)
    client = TestClient(app)
    resp = client.post("/query", json={"question": "policy update", "grounded": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"].get("router_backend") in ("rules_v2", "rules_v1", "rules")
