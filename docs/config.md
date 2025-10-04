# Configuration

Environment variables (selected):

- APP_ENV: runtime profile (default: local)
- LOG_LEVEL: logging level (default: INFO)
- REQUEST_ID_HEADER: request ID header name (default: X-Request-ID)
- METRICS_TOKEN: if set, /metrics requires header X-Metrics-Token with this value
- DB_URL: database URL (default: sqlite:////data/audit.db)
- VECTORSTORE_PATH: path for vector store persistence
- DOCS_PATH: path to example docs for ingestion
- EMBEDDINGS_PROVIDER: local|openai|stub
- EMBEDDINGS_MODEL: sentence-transformers model or OpenAI embedding model name
- MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME: MLflow configuration
- ML_BASELINE_DATA, ML_INPUT_DATA: paths for drift script defaults

See .env.example for a complete list and defaults.
