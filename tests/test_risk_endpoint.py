from fastapi.testclient import TestClient
from app.main import app


def test_risk_endpoint_requires_role():
    client = TestClient(app)
    resp = client.post("/risk", json={"text": "breach"})
    assert resp.status_code == 403


def test_risk_endpoint_returns_score():
    client = TestClient(app)
    resp = client.post("/risk", json={"text": "critical breach"}, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] in ("low", "medium", "high")
    assert 0.0 <= data["value"] <= 1.0
    assert isinstance(data["audit"], dict)
