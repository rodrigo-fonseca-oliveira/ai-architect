# Observability

## Metrics
- Endpoint: GET /metrics
- Content type: Prometheus exposition format
- Protection: Open by default. If METRICS_TOKEN is set, callers must send header `X-Metrics-Token: $METRICS_TOKEN`.

### Exported metrics
- app_requests_total{endpoint, status}
- app_request_latency_seconds{endpoint}
- app_tokens_total{endpoint}
- app_cost_usd_total{endpoint}

Notes:
- /metrics itself is excluded from request counters to avoid scrape feedback.

## Prometheus
Minimal scrape config (prometheus.yml):

scrape_configs:
  - job_name: 'ai-monitor'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    # If METRICS_TOKEN is set in the API, you can pass it via headers:
    # scheme: http
    # headers:
    #   X-Metrics-Token: ${METRICS_TOKEN}

## Grafana
- Default: http://localhost:3000 (admin/admin)
- Datasource: Prometheus at http://prometheus:9090
- Import dashboards or provision them via compose mounts.

## Logging
- JSON logs include: level, message, logger, request_id (if present), and exception info.
- Set log level via LOG_LEVEL (default INFO).
