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
from app.utils.rbac import parse_role, is_allowed_grounded_query

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
    # Optional extras (not persisted to DB today)
    rag_backend: Optional[str] = None
    router_backend: Optional[str] = None
    router_intent: Optional[str] = None


class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    snippet: Optional[str] = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    grounded: bool = False
    user_id: Optional[str] = None
    intent: Optional[str] = Field(default="auto", description="auto|qa|pii_detect|risk_score|other")


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

    # RBAC grounded policy
    role = parse_role(req)

    # Initialize retriever if needed and get citations if grounded
    citations: List[Citation] = []
    rag_backend = "legacy"

    # Optional router (feature-flagged)
    intent = (payload.intent or "auto").lower()
    if os.getenv("ROUTER_ENABLED", "false").lower() in ("1", "true", "yes", "on"):
        if intent == "auto":
            try:
                from app.services.router import route_intent

                intent = route_intent(payload.question, payload.grounded)
            except Exception:
                intent = "qa"
    else:
        # router disabled: default to qa behavior
        intent = "qa"

    if intent == "qa" and payload.grounded:
        if not is_allowed_grounded_query(role):
            raise HTTPException(status_code=403, detail="grounded query not allowed for this role")
        # Feature flag for LangChain RetrievalQA path
        lc_enabled = os.getenv("LC_RAG_ENABLED", "false").lower() in ("1", "true", "yes", "on")
        if lc_enabled:
            rag_backend = "langchain"
            try:
                from app.services.langchain_rag import answer_with_citations

                result = answer_with_citations(payload.question, k=3)
                citations = [Citation(**c) for c in result.get("citations", [])]
            except Exception:
                citations = []
        else:
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

    # Prompt registry (non-disruptive): record prompt name/version in audit
    from app.utils.prompts import load_prompt, PromptNotFound
    prompt_name = "query"
    prompt_version = os.getenv("PROMPT_QUERY_VERSION")
    try:
        loaded = load_prompt(prompt_name, version=prompt_version)
        prompt_version = f"{prompt_name}:{loaded.get('version')}"
    except Exception:
        prompt_version = f"{prompt_name}:unknown"

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
    # attach as attribute for response consumers
    audit_dict = audit.model_dump()
    audit_dict["prompt_version"] = prompt_version
    audit_dict["rag_backend"] = rag_backend
    try:
        from app.services.router import get_backend_meta
        audit_dict["router_backend"] = get_backend_meta()
        audit_dict["router_intent"] = intent
    except Exception:
        pass
    audit = AuditMeta(**audit_dict)

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

    # Update metrics
    try:
        from app.utils.metrics import tokens_total, cost_usd_total
        tokens_total.labels(endpoint="/query").inc((tp or 0) + (tc or 0))
        cost_usd_total.labels(endpoint="/query").inc(float(audit.cost_usd or 0.0))
    except Exception:
        pass

    # Structured logging enrichment for observability
    try:
        from app.utils.logger import get_logger

        logger = get_logger("app")
        extra = {
            "event": "query_result",
            "request_id": getattr(req.state, "request_id", None),
            "rag_backend": rag_backend,
        }
        # attach router extras when present
        if "router_backend" in audit_dict:
            extra["router_backend"] = audit_dict.get("router_backend")
        if "router_intent" in audit_dict:
            extra["router_intent"] = audit_dict.get("router_intent")
        logger.info(str({k: v for k, v in extra.items() if v is not None}))
    except Exception:
        pass

    return QueryResponse(answer=answer, citations=citations, audit=audit)
