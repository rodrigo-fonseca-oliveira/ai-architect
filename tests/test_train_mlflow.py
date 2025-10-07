import subprocess


def test_train_mlflow(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", str(tmp_path / ".mlruns"))
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "ai-architect-test")

    import sys

    res = subprocess.run(
        [sys.executable, "ml/train.py"], capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr
    assert "Run ID:" in res.stdout
