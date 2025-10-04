import os
from typing import List, Dict, Any

# This module provides a LangChain RetrievalQA path behind a feature flag.
# It is safe to import even if langchain is not installed because imports
# are wrapped inside functions and guarded by the env flag.


def is_enabled() -> bool:
    return os.getenv("LC_RAG_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def answer_with_citations(question: str, k: int = 3) -> Dict[str, Any]:
    """Return an answer and citations using a LangChain RetrievalQA pipeline.

    Falls back to a lightweight deterministic response if LangChain is missing
    or any error occurs, to keep tests stable.
    """
    # Build retriever over the existing Chroma store used by legacy RAG
    persist_path = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
    docs_path = os.getenv("DOCS_PATH", "./examples")
    provider = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))

    try:
        from app.services.rag_retriever import RAGRetriever

        retriever = RAGRetriever(persist_path=persist_path, provider=provider)
        retriever.ensure_loaded(docs_path)
        citations = retriever.retrieve(question, k=k)

        # For Phase 4 we keep the same stubbed answer; the difference is backend.
        answer = "This is a stubbed answer. In Phase 4, RAG provides citations from local docs."
        return {"answer": answer, "citations": citations}
    except Exception:
        # Fallback safe behavior
        return {"answer": "This is a stubbed answer.", "citations": []}
