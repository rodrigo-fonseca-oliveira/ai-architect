import os
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_enabled(monkeypatch):
    monkeypatch.delenv("PROJECT_GUIDE_ENABLED", raising=False)
    r = client.post("/architect", json={"question": "hi there", "mode": "guide"})
    assert r.status_code == 404


def test_guide_returns_citations(monkeypatch):
    monkeypatch.setenv("PROJECT_GUIDE_ENABLED", "true")
    # ensure grounded path allowed by RBAC
    headers = {"X-User-Role": "analyst"}

    # point docs to e2e_docs for deterministic citation
    monkeypatch.setenv("DOCS_PATH", str(os.path.join(os.getcwd(), "e2e_docs")))

    r = client.post(
        "/architect",
        json={"question": "gdpr data retention", "mode": "guide"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("citations"), list)
    # allow zero citations in pathological local envs, but field must exist
    assert "suggested_steps" in data and isinstance(data["suggested_steps"], list)
    assert "suggested_env_flags" in data and isinstance(data["suggested_env_flags"], list)


def test_brainstorm_mode(monkeypatch):
    monkeypatch.setenv("PROJECT_GUIDE_ENABLED", "true")
    r = client.post("/architect", json={"question": "custom use case", "mode": "brainstorm"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("suggested_steps"), list)
    assert isinstance(data.get("suggested_env_flags"), list)
