import os

import mlflow
import mlflow.sklearn


class MLflowClientWrapper:
    def __init__(self, tracking_uri: str | None = None, experiment: str | None = None):
        self.tracking_uri = tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "./.mlruns"
        )
        self.experiment = experiment or os.getenv(
            "MLFLOW_EXPERIMENT_NAME", "ai-architect"
        )
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment)

    def load_latest_model(self, artifact_path: str = "model"):
        # Find latest run in experiment and load its model artifact
        exp = mlflow.get_experiment_by_name(self.experiment)
        if not exp:
            raise RuntimeError("MLflow experiment not found")
        runs = mlflow.search_runs(
            exp.experiment_id, order_by=["start_time DESC"], max_results=1
        )
        if runs.empty:
            raise RuntimeError("No runs found in MLflow experiment")
        run_id = runs.iloc[0]["run_id"]
        uri = f"runs:/{run_id}/{artifact_path}"
        model = mlflow.sklearn.load_model(uri)
        return model, run_id
