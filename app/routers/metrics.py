import os

from fastapi import APIRouter, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.utils.metrics import registry

router = APIRouter()

# Optional token-based protection for /metrics
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "").strip()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/metrics")
def metrics(
    x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token")
):
    # If a token is configured, enforce it; otherwise allow open access
    if METRICS_TOKEN:
        if not x_metrics_token or x_metrics_token != METRICS_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="forbidden"
            )
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
