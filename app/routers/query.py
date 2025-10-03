import hashlib
import os
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..utils.audit import make_hash
from ..utils.cost import estimate_tokens_and_cost

router = APIRouter()


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

    # Denylist (Phase 0: read from env, simple contains check)
    denylist = [s.strip().lower() for s in os.getenv("DENYLIST", "").split(",") if s.strip()]
    lower_q = payload.question.lower()
    compliance_flag = any(term in lower_q for term in denylist)

    # Stub LLM answer
    if len(payload.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="question too short")

    answer = "This is a stubbed answer. In Phase 1, RAG will ground and add citations."

    # Mock citations if grounded
    citations: List[Citation] = []
    if payload.grounded:
        citations = [
            Citation(source="docs/gdpr_summary.pdf", page=1, snippet="GDPR is a regulation...")
        ]

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

    return QueryResponse(answer=answer, citations=citations, audit=audit)
