from fastapi.testclient import TestClient

from app.main import app


def test_predict_no_model_returns_400(monkeypatch, tmp_path):
    # Fresh tracking dir and experiment name -> no runs available
    monkeypatch.setenv("MLFLOW_TRACKING_URI", str(tmp_path / ".mlruns"))
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "ai-architect-test")

    client = TestClient(app)
    payload = {"features": {"f0": 0.1, "f1": 0.2}}
    r = client.post("/predict", json=payload, headers={"X-User-Role": "analyst"})
    assert r.status_code == 400
    assert "model load failed" in r.text.lower()
