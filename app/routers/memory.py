from typing import Optional, List, Dict, Any
import os
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.utils.rbac import parse_role, require_role

router = APIRouter()


class MemoryShortResponse(BaseModel):
    turns: list
    summary: Optional[str] = None
    audit: dict


class MemoryLongResponse(BaseModel):
    facts: list
    audit: dict


@router.get("/memory/short", response_model=MemoryShortResponse)
def get_short_memory(req: Request, user_id: str, session_id: str):
    # RBAC
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")

    enabled = os.getenv("MEMORY_SHORT_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    turns = []
    summary = None
    reads = 0
    pruned_short = 0
    if enabled:
        try:
            from app.memory.short_memory import init_short_memory, load_turns, load_summary
            init_short_memory()
            turns = load_turns(user_id, session_id)
            # read pruned count if the loader attached it
            pruned_short = int(getattr(load_turns, "_last_pruned", 0))
            reads = len(turns)
            summary = load_summary(user_id, session_id)
        except Exception:
            turns = []
            summary = None
            pruned_short = 0
    else:
        # If disabled, surface empty but 200
        turns = []
        summary = None

    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/short",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_short_reads": reads if enabled else None,
        "memory_short_pruned": pruned_short if enabled else None,
    }
    # Remove None keys
    audit = {k: v for k, v in audit.items() if v is not None}
    return {"turns": turns, "summary": summary, "audit": audit}


@router.delete("/memory/short", response_model=dict)
def delete_short_memory(req: Request, user_id: str, session_id: str):
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")

    enabled = os.getenv("MEMORY_SHORT_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    cleared = False
    if enabled:
        try:
            from app.memory.short_memory import init_short_memory
            from app.memory.short_memory import clear_short_memory  # type: ignore
        except Exception:
            clear_short_memory = None  # type: ignore
        try:
            init_short_memory()
            if clear_short_memory:
                clear_short_memory(user_id, session_id)  # type: ignore
                cleared = True
        except Exception:
            cleared = False

    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/short",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_short_writes": 1 if (enabled and cleared) else None,
    }
    audit = {k: v for k, v in audit.items() if v is not None}
    return {"cleared": bool(cleared), "audit": audit}


@router.get("/memory/long", response_model=MemoryLongResponse)
def get_long_memory(req: Request, user_id: str, q: Optional[str] = None):
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")

    enabled = os.getenv("MEMORY_LONG_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    facts = []
    reads = 0
    pruned_long = 0
    if enabled:
        try:
            from app.memory.long_memory import retrieve_facts
            query = q or ""
            facts = retrieve_facts(user_id, query)
            pruned_long = int(getattr(retrieve_facts, "_last_pruned", 0))
            reads = len(facts)
        except Exception:
            facts = []
            pruned_long = 0
    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/long",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_long_reads": reads if enabled else None,
        "memory_long_pruned": pruned_long if enabled else None,
    }
    audit = {k: v for k, v in audit.items() if v is not None}
    return {"facts": facts, "audit": audit}


@router.delete("/memory/long", response_model=dict)
def delete_long_memory(req: Request, user_id: str):
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")

    enabled = os.getenv("MEMORY_LONG_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    cleared = False
    if enabled:
        try:
            from app.memory.long_memory import clear_long_memory  # type: ignore
            clear_long_memory(user_id)  # type: ignore
            cleared = True
        except Exception:
            cleared = False
    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/long",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_long_writes": 1 if (enabled and cleared) else None,
    }
    audit = {k: v for k, v in audit.items() if v is not None}
    return {"cleared": bool(cleared), "audit": audit}


@router.get("/memory/long/export", response_model=MemoryLongResponse)
def export_long_memory(req: Request, user_id: str):
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")
    enabled = os.getenv("MEMORY_LONG_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    facts: List[Dict[str, Any]] = []
    reads = 0
    pruned_long = 0
    if enabled:
        try:
            from app.memory.long_memory import _FACT_STORE, MEMORY_LONG_RETENTION_DAYS
            import time as _t
            facts = list(_FACT_STORE.get(user_id, []))
            # apply retention pruning for export view, count how many would be pruned
            if MEMORY_LONG_RETENTION_DAYS and MEMORY_LONG_RETENTION_DAYS > 0:
                cutoff = _t.time() - (MEMORY_LONG_RETENTION_DAYS * 86400)
                before = len(facts)
                facts = [f for f in facts if f.get("created_at", 0) >= cutoff]
                pruned_long = before - len(facts)
            # enrich with export extras
            for f in facts:
                vec = f.get("embedding")
                f["embedding_present"] = bool(vec is not None)
                f["embedding_dim"] = (len(vec) if isinstance(vec, list) else None)
            reads = len(facts)
        except Exception:
            facts = []
            pruned_long = 0
    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/long/export",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_long_reads": reads if enabled else None,
        "memory_long_pruned": pruned_long if enabled else None,
    }
    audit = {k: v for k, v in audit.items() if v is not None}
    return {"facts": facts, "audit": audit}


class MemoryImportPayload(BaseModel):
    facts: List[Dict[str, Any]]


@router.post("/memory/long/import", response_model=dict)
def import_long_memory(req: Request, user_id: str, payload: MemoryImportPayload):
    role = parse_role(req)
    if role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")
    enabled = os.getenv("MEMORY_LONG_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    imported = 0
    pruned_long = 0
    if enabled:
        try:
            from app.memory.long_memory import ingest_fact
            for f in payload.facts:
                text = f.get("text")
                if not text:
                    continue
                meta = f.get("metadata") or {}
                ingest_fact(user_id, text, meta)
                # track evictions triggered by import
                pruned_long += int(getattr(ingest_fact, "_last_evicted", 0) or 0)
                imported += 1
        except Exception:
            imported = 0
            pruned_long = 0
    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/long/import",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_long_writes": imported if enabled else None,
    }
    audit = {k: v for k, v in audit.items() if v is not None}
    return {"imported": imported, "audit": audit}
