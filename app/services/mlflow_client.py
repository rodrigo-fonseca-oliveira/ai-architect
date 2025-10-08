import os
import json
from typing import List, Optional

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
        # Configurable artifact names with sensible defaults
        self.model_artifact = os.getenv("MLFLOW_MODEL_ARTIFACT_PATH", "model")
        self.feature_order_artifact = os.getenv(
            "MLFLOW_FEATURE_ORDER_ARTIFACT", "feature_order.json"
        )
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment)

    def _get_latest_run_id(self) -> str:
        exp = mlflow.get_experiment_by_name(self.experiment)
        if not exp:
            raise RuntimeError("MLflow experiment not found")
        runs = mlflow.search_runs(
            exp.experiment_id, order_by=["start_time DESC"], max_results=1
        )
        if runs.empty:
            raise RuntimeError("No runs found in MLflow experiment")
        return runs.iloc[0]["run_id"]

    def load_latest_model(self, artifact_path: str | None = None):
        # Find latest run in experiment and load its model artifact
        run_id = self._get_latest_run_id()
        apath = artifact_path or self.model_artifact
        uri = f"runs:/{run_id}/{apath}"
        model = mlflow.sklearn.load_model(uri)
        return model, run_id

    def get_feature_order(self, run_id: Optional[str] = None) -> Optional[List[str]]:
        """Try to download feature_order.json from the given run and return the list."""
        try:
            rid = run_id or self._get_latest_run_id()
            artifact_uri = f"runs:/{rid}/{self.feature_order_artifact}"
            # mlflow 2.x
            from mlflow.artifacts import download_artifacts  # lazy import

            local_path = download_artifacts(artifact_uri)
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            fo = data.get("feature_order")
            if isinstance(fo, list) and all(isinstance(x, str) for x in fo):
                return fo
        except Exception:
            return None
        return None

    def get_experiment_name(self) -> str:
        return self.experiment
