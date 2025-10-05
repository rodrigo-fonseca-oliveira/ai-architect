import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.skip(reason="ML path paused for launch; enabling later with MLflow integration")
def test_risk_ml_enabled_changes_method_and_label(monkeypatch):
    monkeypatch.setenv("RISK_ML_ENABLED", "true")
    monkeypatch.setenv("RISK_THRESHOLD", "0.6")
    client = TestClient(app)

    payload = {
        "text": "Critical incident with severe impact and vulnerability exposed."
    }
    resp = client.post("/risk", json=payload, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    data = resp.json()

    # ML path should be used
    assert data["audit"].get("risk_score_method") == "ml"
    assert data["label"] in ("medium", "high")
    # Value should be in [0,1]
    assert 0.0 <= data["value"] <= 1.0
