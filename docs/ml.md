# ML and Drift

## Training
- Script: ml/train.py
- MLflow env vars:
  - MLFLOW_TRACKING_URI
  - MLFLOW_EXPERIMENT_NAME
- Tests run training via `sys.executable` to use the active venv.

## Drift (PSI)
- Script: ml/drift.py
- PSI implementation:
  - Shared bin edges between baseline and new arrays
  - Epsilon smoothing to avoid zero division
- Usage:
  - python ml/drift.py --baseline ml/data/baseline.csv --input ml/data/new_batch.csv --threshold 0.2
- Exit codes:
  - 0: no retrain recommended
  - 1: retrain recommended (PSI > threshold)

## Notes
- CPU-only installs by default:
  - Dockerfile installs sentence-transformers using the PyTorch CPU wheel index, which ensures CPU torch wheels are selected.
  - To switch to GPU later, modify Dockerfile to use a CUDA-specific index URL and matching torch/torchvision/torchaudio versions.
- Ensure numeric columns are aligned between baseline and input.
- Data/model cards: see docs/model_card.md and docs/data_card.md
