# Testing Cheat Sheet

## One-time setup (local)
python -m venv .venv
. .venv/bin/activate
pip install -e .

## Full test suite
.venv/bin/python -m pytest -q

## Verbose output and show logs
.venv/bin/python -m pytest -vv -s

## Run a single file / test
.venv/bin/python -m pytest -q tests/test_predict.py
.venv/bin/python -m pytest -q tests/test_predict.py::test_predict_after_train

## Re-run only failed tests
.venv/bin/python -m pytest --lf

## Stop at first failure
.venv/bin/python -m pytest -x

## Show slow tests
.venv/bin/python -m pytest --durations=10

## With environment variables
MLFLOW_TRACKING_URI=.mlruns MLFLOW_EXPERIMENT_NAME=ai-risk-monitor-test \
  .venv/bin/python -m pytest -q

METRICS_TOKEN=secret \
  .venv/bin/python -m pytest -q tests/test_rbac.py::test_metrics_protected_with_token

## Keyword expression
.venv/bin/python -m pytest -k "rag and idempotent"

## Coverage (optional)
pip install pytest-cov
.venv/bin/python -m pytest --cov=app --cov=ml --cov=db --cov-report=term-missing

## Lint/format (optional)
pip install ruff
.venv/bin/ruff check .
.venv/bin/ruff format .

## Type check (optional)
pip install mypy
.venv/bin/mypy app
