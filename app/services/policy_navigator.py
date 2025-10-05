import os
import time
from typing import List, Dict, Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


def decompose(question: str, max_subqs: int | None = None) -> List[str]:
    q = question.strip()
    parts = []
    # naive decomposition: split by '?' and '.'; filter short parts
    for sep in ['?', '.', ';']:
        q = q.replace(sep, '.')
    for chunk in [p.strip() for p in q.split('.') if p.strip()]:
        if len(chunk) >= 10:
            parts.append(chunk)
    if not parts:
        parts = [question]
    maxn = max_subqs or int(os.getenv("POLICY_NAV_MAX_SUBQS", "3"))
    return parts[:maxn]


def retrieve(subq: str, k: int = 3) -> List[Dict[str, Any]]:
    # reuse existing RAG retriever path (non-LangChain for determinism by default)
    provider = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))
    vector_path = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
    os.makedirs(vector_path, exist_ok=True)
    from app.services.rag_retriever import RAGRetriever
    retriever = RAGRetriever(persist_path=vector_path, provider=provider)
    # ensure docs available
    docs_path = os.getenv("DOCS_PATH", "./examples")
    try:
        retriever.ensure_loaded(docs_path)
    except Exception:
        pass
    try:
        found = retriever.retrieve(subq, k=k)
    except Exception:
        found = []
    return found


def synthesize(question: str, subqs: List[str], per_subq_citations: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    # naive synthesis: summarize findings and provide a recommendation
    lines = [f"Policy navigator for: {question}"]
    all_citations: List[Dict[str, Any]] = []
    for idx, (sq, cites) in enumerate(zip(subqs, per_subq_citations), start=1):
        lines.append(f"Sub-question {idx}: {sq}")
        if cites:
            lines.append("Evidence:")
            for c in cites:
                src = c.get("source", "unknown")
                snip = c.get("snippet", "")
                lines.append(f"- {src}: {snip}")
                all_citations.append({"source": src, "snippet": snip, "page": c.get("page")})
    lines.append("Recommendation: Follow organization policy and best practices based on the above evidence.")
    answer = "\n".join(lines)
    return {"answer": answer, "citations": all_citations}
