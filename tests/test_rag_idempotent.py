import os
from fastapi.testclient import TestClient

from app.main import app


def test_rag_ingest_idempotent(tmp_path, monkeypatch):
    # With LC-only path, ensure idempotent doc scan doesn't error and yields stable citations
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    f = docs_dir / "a.txt"
    f.write_text("hello world")

    # Point DOCS_PATH and query via LC backend to ensure stable behavior
    monkeypatch.setenv("DOCS_PATH", str(docs_dir))
    from app.services.langchain_rag import answer_with_citations
    resp1 = answer_with_citations("hello", k=3)
    resp2 = answer_with_citations("hello", k=3)
    assert resp1.get("citations") == resp2.get("citations")
    assert any("hello" in (c.get("snippet") or "").lower() for c in resp1.get("citations", []))
