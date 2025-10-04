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
- LC_RAG_ENABLED: enable LangChain RetrievalQA path for grounded queries (default: false)
- MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME: MLflow configuration
- ML_BASELINE_DATA, ML_INPUT_DATA: paths for drift script defaults

See .env.example for a complete list and defaults.

Install notes:
- CPU-only Docker builds install sentence-transformers using the PyTorch CPU wheel index so torch resolves to CPU wheels.
- For GPU builds, adjust the Dockerfile to use a CUDA-specific index and compatible torch versions.
