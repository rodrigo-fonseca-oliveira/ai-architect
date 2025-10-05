import hashlib
import os
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..utils.audit import make_hash, write_audit
from ..utils.cost import estimate_tokens_and_cost
from db.session import get_session
# legacy RAGRetriever removed; using LangChain-only path
from app.utils.rbac import parse_role, is_allowed_grounded_query

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
    # Optional extras (not persisted to DB today)
    rag_backend: Optional[str] = None
    router_backend: Optional[str] = None
    router_intent: Optional[str] = None
    # PII detection extras (router intent)
    pii_entities_count: Optional[int] = None
    pii_types: Optional[list] = None
    pii_counts: Optional[dict] = None
    # Memory extras (omitted if flags disabled)
    memory_short_reads: Optional[int] = None
    memory_short_writes: Optional[int] = None
    summary_updated: Optional[bool] = None
    memory_long_reads: Optional[int] = None
    memory_long_writes: Optional[int] = None


class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    snippet: Optional[str] = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    grounded: bool = False
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    intent: Optional[str] = Field(default="auto", description="auto|qa|pii_detect|risk_score|other")


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    audit: dict


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

    # Initialize citations and backend marker
    citations: List[Citation] = []
    rag_backend = "langchain"

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

    if intent == "pii_detect":
        try:
            from app.services.pii_detector import detect_pii

            result = detect_pii(payload.question)
            # Summarize in the human answer
            if result.get("total", 0) > 0:
                parts = [f"{k}({v})" for k, v in sorted(result.get("counts", {}).items())]
                answer_summary = ", ".join(parts)
                answer = f"Detected PII: {answer_summary}."
            else:
                answer = "No PII detected."
            # Temporarily stash PII result in local var for audit enrichment later
            req.state._pii_result = result  # type: ignore[attr-defined]
        except Exception:
            answer = "PII detection unavailable."
    elif intent == "qa" and payload.grounded:
        if not is_allowed_grounded_query(role):
            raise HTTPException(status_code=403, detail="grounded query not allowed for this role")
        # LangChain-only RetrievalQA path
        try:
            from app.services.langchain_rag import answer_with_citations

            result = answer_with_citations(payload.question, k=3)
            citations = [Citation(**c) for c in result.get("citations", [])]
        except Exception:
            citations = []

    # Stub answer baseline; branches may override earlier (e.g., pii_detect)
    if 'answer' not in locals():
        answer = "This is a stubbed answer. In Phase 1, RAG provides citations from local docs."

    # Short-term memory read/Long-term memory read integration
    short_enabled = os.getenv("MEMORY_SHORT_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    long_enabled = os.getenv("MEMORY_LONG_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    memory_short_reads = 0
    memory_short_writes = 0
    summary_updated = False
    memory_long_reads = 0
    memory_long_writes = 0
    uid = payload.user_id or "anonymous"
    sid = getattr(payload, 'session_id', None) or "default"

    memory_short_pruned = 0
    if short_enabled:
        try:
            from app.memory.short_memory import init_short_memory, load_turns, load_summary
            init_short_memory()
            turns = load_turns(uid, sid)
            memory_short_reads = len(turns)
            memory_short_pruned = int(getattr(load_turns, "_last_pruned", 0))
            prefix = load_summary(uid, sid) or "\n".join(f"{r}: {c}" for r, c in turns)
            if prefix:
                payload.question = f"{prefix}\n\nUser: {payload.question}"
            try:
                # bump cumulative short pruning counter
                from app.routers import memory as memory_router_mod
                memory_router_mod._memory_short_pruned_total += int(memory_short_pruned)
            except Exception:
                pass
        except Exception:
            pass

    memory_long_pruned = 0
    if long_enabled:
        try:
            from app.memory.long_memory import retrieve_facts
            facts = retrieve_facts(uid, payload.question)
            memory_long_reads = len(facts)
            memory_long_pruned = int(getattr(retrieve_facts, "_last_pruned", 0))
            if facts:
                snippet = "\n".join(f"- {f['text']}" for f in facts)
                payload.question = f"Relevant facts:\n{snippet}\n\nQuestion: {payload.question}"
            try:
                # bump cumulative long pruning counter
                from app.routers import memory as memory_router_mod
                memory_router_mod._memory_long_pruned_total += int(memory_long_pruned)
            except Exception:
                pass
        except Exception:
            pass

    # Token & cost estimation
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    tp, tc, cost = estimate_tokens_and_cost(model=model, prompt=payload.question, completion=answer)

    # Save to memory after answering (writes and counters)
    if short_enabled:
        try:
            from app.memory.short_memory import save_turn, update_summary_if_needed
            save_turn(uid, sid, "user", payload.question)
            save_turn(uid, sid, "assistant", answer)
            memory_short_writes = 2
            summary_updated = update_summary_if_needed(uid, sid)
        except Exception:
            pass
    if long_enabled:
        try:
            from app.memory.long_memory import ingest_fact
            for sent in answer.split("."):
                sent = sent.strip()
                if len(sent) > 50:
                    ingest_fact(uid, sent)
                    memory_long_writes += 1
        except Exception:
            pass

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
        memory_short_reads=None,
        memory_short_writes=None,
        summary_updated=None,
        memory_long_reads=None,
        memory_long_writes=None,
    )
    # attach as attribute for response consumers
    audit_dict = audit.model_dump()
    audit_dict["prompt_version"] = prompt_version
    audit_dict["rag_backend"] = rag_backend
    try:
        from app.services.router import get_backend_meta
        audit.router_backend = get_backend_meta()
        audit.router_intent = intent
        audit_dict["router_backend"] = audit.router_backend
        audit_dict["router_intent"] = audit.router_intent
    except Exception:
        pass

    # Attach PII extras when present
    if intent == "pii_detect":
        try:
            pii_result = getattr(req.state, "_pii_result", None)
            if pii_result is not None:
                audit.pii_entities_count = int(pii_result.get("total", 0))
                audit.pii_types = pii_result.get("types_present", [])
                audit.pii_counts = pii_result.get("counts", {})
                audit_dict["pii_entities_count"] = audit.pii_entities_count
                audit_dict["pii_types"] = audit.pii_types
                audit_dict["pii_counts"] = audit.pii_counts
        except Exception:
            pass

    # Attach Memory extras
    if short_enabled:
        audit_dict["memory_short_reads"] = int(memory_short_reads)
        audit_dict["memory_short_writes"] = int(memory_short_writes)
        audit_dict["summary_updated"] = bool(summary_updated)
        audit_dict["memory_short_pruned"] = int(memory_short_pruned)
    else:
        for k in ("memory_short_reads", "memory_short_writes", "summary_updated", "memory_short_pruned"):
            audit_dict.pop(k, None)
    if long_enabled:
        audit_dict["memory_long_reads"] = int(memory_long_reads)
        audit_dict["memory_long_writes"] = int(memory_long_writes)
        audit_dict["memory_long_pruned"] = int(memory_long_pruned)
        audit.memory_long_reads = int(memory_long_reads)
        audit.memory_long_writes = int(memory_long_writes)
    else:
        for k in ("memory_long_reads", "memory_long_writes", "memory_long_pruned"):
            audit_dict.pop(k, None)
        audit.memory_long_reads = None
        audit.memory_long_writes = None

    # ensure memory extras are present in audit model when flags are enabled
    audit.memory_short_reads = int(memory_short_reads) if short_enabled else None
    audit.memory_short_writes = int(memory_short_writes) if short_enabled else None
    audit.summary_updated = bool(summary_updated) if short_enabled else None
    # Explicitly clear long memory fields when flag is disabled to ensure they don't serialize
    if long_enabled:
        audit.memory_long_reads = int(memory_long_reads)
        audit.memory_long_writes = int(memory_long_writes)
    else:
        audit.memory_long_reads = None
        audit.memory_long_writes = None

    # Rebuild dict for logging with memory extras visible
    audit_dict = audit.model_dump()
    # build response audit dict filtered by flags for correct field presence
    response_audit = audit_dict.copy()
    # ensure rag_backend present
    try:
        response_audit['rag_backend'] = rag_backend
    except Exception:
        pass
    if not short_enabled:
        for k in ("memory_short_reads", "memory_short_writes", "summary_updated", "memory_short_pruned"):
            response_audit.pop(k, None)
    if not long_enabled:
        for k in ("memory_long_reads", "memory_long_writes", "memory_long_pruned"):
            response_audit.pop(k, None)

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
        for k in ("router_backend", "router_intent", "risk_score_label", "risk_score_value"):
            if k in audit_dict:
                extra[k] = audit_dict.get(k)
        # attach memory extras when set
        for k in ("memory_short_reads", "memory_short_writes", "summary_updated", "memory_long_reads", "memory_long_writes"):
            if k in audit_dict:
                extra[k] = audit_dict.get(k)
        logger.info(str({k: v for k, v in extra.items() if v is not None}))
    except Exception:
        pass

    return QueryResponse(answer=answer, citations=citations, audit=response_audit)
