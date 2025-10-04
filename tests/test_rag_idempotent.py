import os
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag_retriever import RAGRetriever, StubEmbeddings


def test_rag_ingest_idempotent(tmp_path, monkeypatch):
    # Use stub embeddings for speed and determinism
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "stub")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    f = docs_dir / "a.txt"
    f.write_text("hello world")

    retriever = RAGRetriever(persist_path=str(tmp_path / "vectorstore"), provider="stub")

    n1 = retriever.ingest(str(docs_dir))
    assert n1 == 1
    count1 = retriever.collection.count()

    # Re-ingest the same file; count should not increase
    n2 = retriever.ingest(str(docs_dir))
    assert n2 == 1
    count2 = retriever.collection.count()

    assert count2 == count1

    # Modify file; count should increase
    f.write_text("hello world!!!")
    n3 = retriever.ingest(str(docs_dir))
    assert n3 == 1
    count3 = retriever.collection.count()

    assert count3 == count2 + 1
