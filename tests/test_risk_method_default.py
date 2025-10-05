import os
from fastapi.testclient import TestClient
from app.main import app


def test_risk_method_heuristic_by_default(monkeypatch):
    # Ensure flag is unset/false
    monkeypatch.delenv("RISK_ML_ENABLED", raising=False)
    monkeypatch.setenv("RISK_THRESHOLD", "0.6")

    client = TestClient(app)

    payload = {"text": "some benign info"}
    resp = client.post("/risk", json=payload, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["audit"].get("risk_score_method") == "heuristic"
    assert data["label"] in ("low", "medium", "high")
    assert 0.0 <= data["value"] <= 1.0
