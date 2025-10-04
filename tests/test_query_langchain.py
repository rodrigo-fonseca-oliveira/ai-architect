import os
from fastapi.testclient import TestClient

from app.main import app


def test_query_langchain_backend_with_flag(monkeypatch, tmp_path):
    # Enable LC path
    monkeypatch.setenv("LC_RAG_ENABLED", "true")
    # Use stub embeddings to avoid heavy deps
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "stub")
    # Point to a temp vector store and docs
    monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / ".vector"))
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    sample = docs_dir / "sample.txt"
    sample.write_text("Policy: Data should be encrypted at rest.")
    monkeypatch.setenv("DOCS_PATH", str(docs_dir))

    client = TestClient(app)
    resp = client.post(
        "/query",
        json={"question": "What is the policy?", "grounded": True},
        headers={"X-User-Role": "analyst"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert isinstance(data["citations"], list)
    # With stub retriever through LC wrapper, we should still get at least one citation
    assert len(data["citations"]) >= 1
