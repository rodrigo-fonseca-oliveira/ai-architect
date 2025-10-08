from fastapi.testclient import TestClient

from app.main import app


def _train(monkeypatch, tmp_path):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", str(tmp_path / ".mlruns"))
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "ai-architect-test")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "ml/train.py"])  # create run/model


def test_predict_missing_feature(monkeypatch, tmp_path):
    _train(monkeypatch, tmp_path)
    client = TestClient(app)
    # Omitting one feature from the expected set
    payload = {"features": {"f0": 0.1, "f1": 0.2, "f2": 0.3}}
    r = client.post("/predict", json=payload, headers={"X-User-Role": "analyst"})
    assert r.status_code == 400
    assert "missing features" in r.text


def test_predict_extra_feature(monkeypatch, tmp_path):
    _train(monkeypatch, tmp_path)
    client = TestClient(app)
    # Add an extra feature not present in training
    payload = {"features": {"f0": 0.1, "f1": 0.2, "f2": 0.3, "f_extra": 1.0}}
    r = client.post("/predict", json=payload, headers={"X-User-Role": "analyst"})
    assert r.status_code == 400
    assert "unknown features" in r.text


def test_predict_shuffled_keys_ok(monkeypatch, tmp_path):
    _train(monkeypatch, tmp_path)
    client = TestClient(app)
    # Correct set, shuffled order
    payload = {"features": {"f3": 0.0, "f1": 0.2, "f0": 0.1, "f2": -0.1, "f4": 0.0, "f5": 0.0, "f6": 0.0, "f7": 0.1}}
    r = client.post("/predict", json=payload, headers={"X-User-Role": "analyst"})
    assert r.status_code == 200
    data = r.json()
    assert "prediction" in data
