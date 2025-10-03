from fastapi import APIRouter, Response
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, Counter

router = APIRouter()

# Minimal metrics: request counter (can be extended later)
registry = CollectorRegistry()
requests_counter = Counter(
    "app_requests_total", "Total HTTP requests processed", registry=registry
)


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/metrics")
def metrics():
    # increment a simple counter to show something
    requests_counter.inc()
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
