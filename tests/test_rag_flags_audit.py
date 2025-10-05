import os
from fastapi.testclient import TestClient

from app.main import app


def test_rag_flags_propagate_to_audit(tmp_path, monkeypatch):
    # Prepare minimal docs dir
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "gdpr.txt").write_text("GDPR is a regulation about data protection and retention.")
    monkeypatch.setenv("DOCS_PATH", str(docs_dir))

    # Enable flags
    monkeypatch.setenv("RAG_MULTI_QUERY_ENABLED", "true")
    monkeypatch.setenv("RAG_MULTI_QUERY_COUNT", "4")
    monkeypatch.setenv("RAG_HYDE_ENABLED", "true")

    client = TestClient(app)
    resp = client.post(
        "/query",
        json={"question": "What is GDPR data retention policy?", "grounded": True},
        headers={"X-User-Role": "analyst"},
    )
    assert resp.status_code == 200
    data = resp.json()
    audit = data.get("audit", {})

    # Flags must appear in audit
    assert audit.get("rag_multi_query") is True
    # rag_multi_count should be integer >= 1 when enabled
    rcount = audit.get("rag_multi_count")
    assert isinstance(rcount, int) and rcount >= 1
    assert audit.get("rag_hyde") is True

    # Citations should still be present
    assert isinstance(data.get("citations", []), list)
    assert len(data.get("citations", [])) >= 1
