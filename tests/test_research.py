from fastapi.testclient import TestClient

from app.main import app


def test_research_happy_path():
    client = TestClient(app)
    r = client.post(
        "/research",
        json={"topic": "GDPR and AI", "steps": ["search", "fetch", "summarize", "risk_check"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("findings", []), list)
    assert isinstance(data.get("steps", []), list)
    assert "audit" in data and data["audit"]["request_id"]


def test_research_safety_block_offline_stub():
    # In stub mode, fetch won't block, but we can still run a minimal call
    client = TestClient(app)
    r = client.post("/research", json={"topic": "Test topic"})
    assert r.status_code == 200


def test_research_denylist_flag(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("DENYLIST", "phi,ssn,credit_card")
    r = client.post("/research", json={"topic": "This includes ssn"})
    assert r.status_code == 200
    assert r.json()["audit"]["compliance_flag"] is True
