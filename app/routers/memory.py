from typing import Optional
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
    if enabled:
        try:
            from app.memory.short_memory import init_short_memory, load_turns, load_summary
            init_short_memory()
            turns = load_turns(user_id, session_id)
            reads = len(turns)
            summary = load_summary(user_id, session_id)
        except Exception:
            turns = []
            summary = None
    else:
        # If disabled, surface empty but 200
        turns = []
        summary = None

    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/short",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_short_reads": reads if enabled else None,
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
    if enabled:
        try:
            from app.memory.long_memory import retrieve_facts
            query = q or ""
            facts = retrieve_facts(user_id, query)
            reads = len(facts)
        except Exception:
            facts = []
    audit = {
        "request_id": getattr(req.state, "request_id", "unknown"),
        "endpoint": "/memory/long",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory_long_reads": reads if enabled else None,
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
