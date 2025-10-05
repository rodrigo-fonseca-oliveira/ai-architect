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
- ROUTER_ENABLED: enable simple Router Agent (rules-based) to select intent (default: false)
- PII_TYPES: comma-separated list of detectors to enable (default: email,phone,ssn,credit_card,ipv4)
- RISK_ML_ENABLED: optional flag to use ML-based risk scorer instead of heuristics (future; default: false)
- MEMORY_SHORT_ENABLED: enable short-term memory (default: false)
- MEMORY_DB_PATH: SQLite path for short memory (default: ./data/memory_short.db)
- MEMORY_SHORT_MAX_TURNS: max turns before summary (default: 10)
- SHORT_MEMORY_RETENTION_DAYS: prune short-term turns older than N days (default: 0=disabled)
- SHORT_MEMORY_MAX_TURNS_PER_SESSION: cap short-term turns per session (default: 0=disabled)
- MEMORY_LONG_ENABLED: enable long-term memory (default: false)
- MEMORY_COLLECTION_PREFIX: long-memory collection prefix (default: memory)
- MEMORY_LONG_RETENTION_DAYS: prune facts older than N days (default: 0=disabled)
- MEMORY_LONG_MAX_FACTS: keep at most N facts per user (default: 0=disabled)
- MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME: MLflow configuration
- ML_BASELINE_DATA, ML_INPUT_DATA: paths for drift script defaults

See .env.example for a complete list and defaults.

Install notes:
- CPU-only Docker builds install sentence-transformers using the PyTorch CPU wheel index so torch resolves to CPU wheels.
- For GPU builds, adjust the Dockerfile to use a CUDA-specific index and compatible torch versions.
