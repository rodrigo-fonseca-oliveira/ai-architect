from fastapi.testclient import TestClient

from app.main import app


def test_router_pii_detect_intent(monkeypatch):
    monkeypatch.setenv("ROUTER_ENABLED", "true")
    # LC flag removed; default behavior unchanged
    client = TestClient(app)
    payload = {"question": "Is an SSN considered PII?", "grounded": False}
    resp = client.post("/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"].get("router_intent") == "pii_detect"


def test_router_prefers_qa_for_grounded_with_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("ROUTER_ENABLED", "true")
    # LC default; no flags required
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "doc.txt").write_text("Security policy requires encryption at rest.")
    monkeypatch.setenv("DOCS_PATH", str(docs_dir))

    client = TestClient(app)
    resp = client.post(
        "/query",
        json={"question": "What is the security policy?", "grounded": True},
        headers={"X-User-Role": "analyst"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"].get("router_intent") == "qa"
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) >= 1


def test_router_disabled_default_behavior(monkeypatch):
    monkeypatch.delenv("ROUTER_ENABLED", raising=False)
    client = TestClient(app)
    resp = client.post("/query", json={"question": "Hello", "grounded": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"].get("router_intent") in (None, "qa")
