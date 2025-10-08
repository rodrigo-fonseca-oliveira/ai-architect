from fastapi.testclient import TestClient

from app.main import app


def test_predict_schema_after_training(monkeypatch, tmp_path):
    # Train a model to ensure schema exists
    monkeypatch.setenv("MLFLOW_TRACKING_URI", str(tmp_path / ".mlruns"))
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "ai-architect-test")

    import subprocess
import sys

    subprocess.check_call([sys.executable, "ml/train.py"])  # create run/model

    client = TestClient(app)
    r = client.get("/predict/schema", headers={"X-User-Role": "analyst"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("features", []), list)
    assert data.get("run_id")
    assert data.get("experiment")
