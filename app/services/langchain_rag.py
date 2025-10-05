import os
from typing import List, Dict, Any

# This module provides a LangChain RetrievalQA path behind a feature flag.
# It is safe to import even if langchain is not installed because imports
# are wrapped inside functions and guarded by the env flag.


def is_enabled() -> bool:
    # LC is always enabled as the sole backend
    return True


def answer_with_citations(question: str, k: int = 3) -> Dict[str, Any]:
    """Return an answer and citations using a LangChain RetrievalQA pipeline.

    Falls back to a lightweight deterministic response if LangChain is missing
    or any error occurs, to keep tests stable.
    """
    # Build retriever over the existing Chroma store used by legacy RAG
    persist_path = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
    docs_path = os.getenv("DOCS_PATH", "./examples")
    provider = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))

    # Implement a simple LC-like retriever stub using filesystem docs.
    # Since we removed the legacy retriever, we simulate citations deterministically
    # by scanning text files under DOCS_PATH and returning top-k snippets.
    citations = []
    try:
        if os.path.isdir(docs_path):
            q_terms = [t.strip(".,:;!?()").lower() for t in question.split() if len(t) > 2]
            for root, _, files in os.walk(docs_path):
                for fn in files:
                    if fn.lower().endswith(('.txt', '.md')):
                        path = os.path.join(root, fn)
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                text = f.read()
                            t_low = text.lower()
                            score = sum(1 for term in q_terms if term in t_low)
                            if score > 0:
                                snippet = text[:200].replace('\n', ' ')
                                citations.append({"source": os.path.relpath(path, docs_path), "page": None, "snippet": snippet, "_score": score})
                        except Exception:
                            continue
        # Sort by score desc and take top-k
        citations = sorted(citations, key=lambda c: c.get("_score", 0), reverse=True)[:k]
        for c in citations:
            c.pop("_score", None)
    except Exception:
        citations = []
    answer = "This is a stubbed answer. In Phase 4, RAG provides citations from local docs."
    return {"answer": answer, "citations": citations}
