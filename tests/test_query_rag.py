import os
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


def test_query_with_rag_citations(tmp_path, monkeypatch):
    # Prepare temp docs and vectorstore
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "gdpr.txt").write_text("GDPR is a regulation in EU about data protection.")

    vec_dir = tmp_path / ".vector"
    monkeypatch.setenv("DOCS_PATH", str(docs_dir))
    monkeypatch.setenv("VECTORSTORE_PATH", str(vec_dir))
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "stub")  # deterministic, offline

    # Ingest
    from scripts.ingest_docs import main as ingest_main

    ingest_main()

    client = TestClient(app)
    r = client.post(
        "/query",
        json={"question": "What is GDPR?", "grounded": True},
        headers={"X-User-Role": "analyst"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("citations", []), list)
    # Expect at least one citation present after ingestion
    assert len(data.get("citations", [])) >= 1
