import os
import hashlib
from typing import List, Dict, Any

from app.services.rag_retriever import LocalEmbeddings, OpenAIEmbeddings, StubEmbeddings
from app.utils.logger import get_logger

logger = get_logger(__name__)

PREFIX = os.getenv("MEMORY_COLLECTION_PREFIX", "memory")

# Fallback in-memory store to avoid external dependency in tests/CI
_FACT_STORE: dict[str, list[dict[str, Any]]] = {}


def _get_embedder():
    prov = os.getenv("EMBEDDINGS_PROVIDER", "local").lower()
    if prov == "openai":
        return OpenAIEmbeddings()
    if prov == "stub":
        return StubEmbeddings()
    return LocalEmbeddings()


def retrieve_facts(user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    # naive similarity via cosine on local embeddings if available
    facts = _FACT_STORE.get(user_id, [])
    if not facts:
        return []
    emb = _get_embedder()
    try:
        qvec = emb.embed([query])[0]
    except Exception:
        # If embeddings fail, just return recent facts
        return facts[:top_k]

    def cos(a, b):
        import math
        num = sum(x * y for x, y in zip(a, b))
        da = math.sqrt(sum(x * x for x in a))
        db = math.sqrt(sum(y * y for y in b))
        return (num / (da * db)) if da and db else 0.0

    scored = []
    for f in facts:
        vec = f.get("embedding")
        if not vec:
            try:
                vec = emb.embed([f["text"]])[0]
            except Exception:
                vec = None
        score = cos(qvec, vec) if vec else 0.0
        scored.append((score, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:top_k]]


def ingest_fact(user_id: str, fact: str, metadata: Dict[str, Any] | None = None) -> bool:
    emb = _get_embedder()
    try:
        vec = emb.embed([fact])[0]
    except Exception:
        vec = None
    lst = _FACT_STORE.setdefault(user_id, [])
    _id = hashlib.sha256(fact.encode("utf-8")).hexdigest()
    # idempotent upsert by id
    exists = None
    for i, f in enumerate(lst):
        if f.get("id") == _id:
            exists = i
            break
    item = {"id": _id, "text": fact, "metadata": metadata or {}, "embedding": vec}
    if exists is not None:
        lst[exists] = item
    else:
        lst.append(item)
    return True


def clear_long_memory(user_id: str) -> None:
    if user_id in _FACT_STORE:
        del _FACT_STORE[user_id]
