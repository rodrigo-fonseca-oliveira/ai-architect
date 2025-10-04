from fastapi import APIRouter, Response, Depends
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.utils.metrics import registry
from app.utils.rbac import require_role

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/metrics")
def metrics(role: str = Depends(require_role("admin"))):
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
