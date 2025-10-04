import hashlib
import os
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..utils.audit import make_hash, write_audit
from ..utils.cost import estimate_tokens_and_cost
from db.session import get_session
from ..services.rag_retriever import RAGRetriever

router = APIRouter()

# Lazy init retriever
_retriever: RAGRetriever | None = None


# Schemas kept local for Phase 0 simplicity
class AuditMeta(BaseModel):
    request_id: str
    user_id: Optional[str] = None
    endpoint: str
    created_at: str
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    compliance_flag: bool = False
    prompt_hash: Optional[str] = None
    response_hash: Optional[str] = None


class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    snippet: Optional[str] = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    grounded: bool = False
    user_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    audit: AuditMeta


@router.post("/query", response_model=QueryResponse)
def post_query(req: Request, payload: QueryRequest):
    start = time.perf_counter()

    # Denylist (Phase 1: env-based)
    denylist = [s.strip().lower() for s in os.getenv("DENYLIST", "").split(",") if s.strip()]
    lower_q = payload.question.lower()
    compliance_flag = any(term in lower_q for term in denylist)

    # Validation
    if len(payload.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="question too short")

    # Initialize retriever if needed and get citations if grounded
    citations: List[Citation] = []
    if payload.grounded:
        # Always create retriever from current env to avoid stale path/provider
        provider = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))
        vector_path = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
        os.makedirs(vector_path, exist_ok=True)
        retriever = __import__("app.services.rag_retriever", fromlist=["RAGRetriever"]).RAGRetriever(
            persist_path=vector_path, provider=provider
        )
        try:
            # Ensure collection has content for the given DOCS_PATH
            docs_path = os.getenv("DOCS_PATH", "./examples")
            retriever.ensure_loaded(docs_path)
            found = retriever.retrieve(payload.question, k=3)
            citations = [Citation(**c) for c in found]
        except Exception:
            citations = []

    # Stub LLM answer (Phase 1 still stubbed; RAG affects citations only)
    answer = "This is a stubbed answer. In Phase 1, RAG provides citations from local docs."

    # Token & cost estimation
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    tp, tc, cost = estimate_tokens_and_cost(model=model, prompt=payload.question, completion=answer)

    latency_ms = int((time.perf_counter() - start) * 1000)

    audit = AuditMeta(
        request_id=getattr(req.state, "request_id", "unknown"),
        user_id=payload.user_id,
        endpoint="/query",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        tokens_prompt=tp,
        tokens_completion=tc,
        cost_usd=round(cost, 6),
        latency_ms=latency_ms,
        compliance_flag=compliance_flag,
        prompt_hash=make_hash(payload.question),
        response_hash=make_hash(answer),
    )

    # Persist audit row, ensuring DB is initialized for current DB_URL
    try:
        from db.session import init_db
        init_db()
    except Exception:
        pass

    from db.session import get_session
    db = get_session()
    try:
        write_audit(
            db,
            request_id=audit.request_id,
            endpoint=audit.endpoint,
            user_id=audit.user_id,
            tokens_prompt=audit.tokens_prompt,
            tokens_completion=audit.tokens_completion,
            cost_usd=audit.cost_usd,
            latency_ms=audit.latency_ms,
            compliance_flag=audit.compliance_flag,
            prompt_hash=audit.prompt_hash,
            response_hash=audit.response_hash,
        )
    finally:
        db.close()

    return QueryResponse(answer=answer, citations=citations, audit=audit)
