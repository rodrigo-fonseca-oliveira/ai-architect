from typing import Optional, List
import os
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.utils.rbac import parse_role, require_role as require_min_role
from app.utils.audit import make_hash, write_audit
from app.utils.cost import estimate_tokens_and_cost

from app.services.pii_detector import detect_pii

router = APIRouter()


class PiiRequest(BaseModel):
    text: str = Field(min_length=1)
    types: Optional[List[str]] = None
    grounded: bool = False


class PiiResponse(BaseModel):
    summary: str
    entities: List[dict]
    counts: dict
    types_present: List[str]
    audit: dict


@router.post("/pii", response_model=PiiResponse)
def post_pii(req: Request, payload: PiiRequest):
    # RBAC: analyst/admin (minimum analyst)
    # Use dependency function style but we call it here for simplicity
    # If role < analyst, raise 403
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    start = time.perf_counter()
    # Detect
    result = detect_pii(payload.text)
    if result.get("total", 0) > 0:
        parts = [f"{k}({v})" for k, v in sorted(result.get("counts", {}).items())]
        summary = ", ".join(parts)
        answer = f"Detected PII: {summary}."
    else:
        answer = "No PII detected."

    # Optional RAG citations for policy references
    citations = []
    if payload.grounded and os.getenv("PII_RAG_ENABLED", "false").lower() in ("1", "true", "yes", "on"):
        try:
            provider = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))
            vector_path = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
            os.makedirs(vector_path, exist_ok=True)
            from app.services.rag_retriever import RAGRetriever

            retriever = RAGRetriever(persist_path=vector_path, provider=provider)
            docs_path = os.getenv("DOCS_PATH", "./examples")
            retriever.ensure_loaded(docs_path)
            found = retriever.retrieve("PII policy references", k=3)
            citations = found
        except Exception:
            citations = []

    # Cost/tokens
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    tp, tc, cost = estimate_tokens_and_cost(model=model, prompt=payload.text, completion=answer)

    latency_ms = int((time.perf_counter() - start) * 1000)

    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/pii",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tokens_prompt": tp,
        "tokens_completion": tc,
        "cost_usd": round(cost, 6),
        "latency_ms": latency_ms,
        "prompt_hash": make_hash(payload.text),
        "response_hash": make_hash(answer),
        "pii_entities_count": result.get("total", 0),
        "pii_types": result.get("types_present", []),
        "pii_counts": result.get("counts", {}),
    }

    # Persist audit
    try:
        from db.session import init_db, get_session

        init_db()
        db = get_session()
        try:
            write_audit(
                db,
                request_id=audit.get("request_id"),
                endpoint=audit.get("endpoint"),
                user_id=None,
                tokens_prompt=audit.get("tokens_prompt"),
                tokens_completion=audit.get("tokens_completion"),
                cost_usd=audit.get("cost_usd"),
                latency_ms=audit.get("latency_ms"),
                compliance_flag=False,
                prompt_hash=audit.get("prompt_hash"),
                response_hash=audit.get("response_hash"),
            )
        finally:
            db.close()
    except Exception:
        pass

    return PiiResponse(summary=answer, entities=result["entities"], counts=result["counts"], types_present=result["types_present"], audit=audit)
