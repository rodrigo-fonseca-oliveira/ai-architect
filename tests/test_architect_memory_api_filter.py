import os
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def enable_architect():
    old = os.environ.get("PROJECT_GUIDE_ENABLED")
    os.environ["PROJECT_GUIDE_ENABLED"] = "true"
    yield
    if old is not None:
        os.environ["PROJECT_GUIDE_ENABLED"] = old
    else:
        os.environ.pop("PROJECT_GUIDE_ENABLED", None)


def test_audit_filters_memory_fields_when_disabled(enable_architect):
    # Ensure memory is disabled
    os.environ["MEMORY_SHORT_ENABLED"] = "false"
    os.environ["MEMORY_LONG_ENABLED"] = "false"

    client = TestClient(app)
    resp = client.post("/architect", json={"question": "How do I configure RAG?"})
    assert resp.status_code == 200
    audit = resp.json().get("audit", {})

    # Memory fields should be absent
    assert not any(k.startswith("memory_short_") for k in audit.keys())
    assert not any(k.startswith("memory_long_") for k in audit.keys())
    assert "summary_updated" not in audit


def test_audit_includes_memory_fields_when_enabled(enable_architect):
    # Enable memory
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    os.environ["MEMORY_LONG_ENABLED"] = "true"

    client = TestClient(app)
    resp = client.post("/architect", json={"question": "Explain memory flags"})
    assert resp.status_code == 200
    audit = resp.json().get("audit", {})

    # Memory fields should be present
    assert any(k.startswith("memory_short_") for k in audit.keys())
    assert any(k.startswith("memory_long_") for k in audit.keys())
