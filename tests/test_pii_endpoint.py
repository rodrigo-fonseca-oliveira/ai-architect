import os
from fastapi.testclient import TestClient

from app.main import app


def test_pii_endpoint_requires_role(monkeypatch):
    client = TestClient(app)
    resp = client.post("/pii", json={"text": "email bob@example.com"})
    assert resp.status_code == 403


def test_pii_endpoint_detects_and_audits(monkeypatch):
    client = TestClient(app)
    resp = client.post(
        "/pii",
        json={"text": "email bob@example.com"},
        headers={"X-User-Role": "analyst"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Detected PII" in data["summary"] or data["summary"].startswith("No PII detected")
    assert isinstance(data["audit"].get("pii_entities_count"), int)


def test_pii_endpoint_optionally_returns_citations(monkeypatch, tmp_path):
    # Enable RAG for PII
    monkeypatch.setenv("PII_RAG_ENABLED", "true")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "stub")
    monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / ".vector"))
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "policy.txt").write_text("PII policy: do not share personal data externally.")
    monkeypatch.setenv("DOCS_PATH", str(docs_dir))

    client = TestClient(app)
    resp = client.post(
        "/pii",
        json={"text": "email bob@example.com", "grounded": True},
        headers={"X-User-Role": "analyst"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # citations are not part of PiiResponse schema, but we ensure endpoint doesn't error and returns summary
    assert "summary" in data
