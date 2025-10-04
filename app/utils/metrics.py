from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()

request_count = Counter(
    "app_requests_total",
    "Total HTTP requests processed",
    labelnames=("endpoint", "status"),
    registry=registry,
)

request_latency = Histogram(
    "app_request_latency_seconds",
    "Request latency in seconds",
    labelnames=("endpoint",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    registry=registry,
)

tokens_total = Counter(
    "app_tokens_total",
    "Total tokens accounted",
    labelnames=("endpoint",),
    registry=registry,
)

cost_usd_total = Counter(
    "app_cost_usd_total",
    "Total cost in USD (estimated)",
    labelnames=("endpoint",),
    registry=registry,
)
