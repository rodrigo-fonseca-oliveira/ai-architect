import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.schemas.predict import PredictRequest, PredictResponse
from app.services.mlflow_client import MLflowClientWrapper
from app.utils.audit import make_hash, write_audit
from app.utils.cost import estimate_tokens_and_cost
from db.session import init_db, get_session

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def post_predict(req: Request, payload: PredictRequest):
    start = time.perf_counter()

    if not isinstance(payload.features, dict) or not payload.features:
        raise HTTPException(status_code=400, detail="features must be a non-empty object")

    client = MLflowClientWrapper()
    try:
        model, run_id = client.load_latest_model()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"model load failed: {e}")

    # Prepare features: ensure order matches training
    # This is a toy predictor: accept numeric-like values only
    try:
        import numpy as np

        x = payload.features
        # Keep stable order by sorting keys (toy example)
        keys = sorted(x.keys())
        vals = [float(x[k]) if x[k] is not None else 0.0 for k in keys]
        arr = np.array(vals).reshape(1, -1)
        pred = model.predict(arr)[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"prediction failed: {e}")

    # Audit + cost
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    tp, tc, cost = estimate_tokens_and_cost(model=model_name, prompt=str(payload.features), completion=str(pred))

    latency_ms = int((time.perf_counter() - start) * 1000)
    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "user_id": payload.user_id,
        "endpoint": "/predict",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tokens_prompt": tp,
        "tokens_completion": tc,
        "cost_usd": round(cost, 6),
        "latency_ms": latency_ms,
        "compliance_flag": False,
        "prompt_hash": make_hash(str(payload.features)),
        "response_hash": make_hash(str(pred)),
    }

    try:
        init_db()
    except Exception:
        pass
    db = get_session()
    try:
        write_audit(
            db,
            request_id=audit["request_id"],
            endpoint=audit["endpoint"],
            user_id=audit["user_id"],
            tokens_prompt=audit["tokens_prompt"],
            tokens_completion=audit["tokens_completion"],
            cost_usd=audit["cost_usd"],
            latency_ms=audit["latency_ms"],
            compliance_flag=audit["compliance_flag"],
            prompt_hash=audit["prompt_hash"],
            response_hash=audit["response_hash"],
        )
    finally:
        db.close()

    return PredictResponse(
        prediction=str(pred),
        model_version=run_id,
        metrics={},
        audit=audit,
    )
