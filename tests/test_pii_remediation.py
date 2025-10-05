import os
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_pii_remediation_requires_role():
    r = client.post("/pii_remediation", json={"text": "Contact me at a@b.com and 123-45-6789"})
    assert r.status_code == 403


def test_pii_remediation_happy_path_stub(tmp_path):
    os.environ["PII_REMEDIATION_ENABLED"] = "true"
    os.environ["EMBEDDINGS_PROVIDER"] = "stub"
    headers = {"X-User-Role": "analyst"}
    r = client.post(
        "/pii_remediation",
        json={"text": "Email a@b.com and SSN 123-45-6789 present.", "return_snippets": True, "grounded": True},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("remediation", []), list)
    # when snippets requested, at least some entries should include 'snippet'
    if data.get("remediation"):
        assert any("snippet" in e for e in data["remediation"])
    # citations present when grounded
    assert isinstance(data.get("citations", []), list)
    # audit fields
    assert "audit" in data and isinstance(data["audit"], dict)
    assert isinstance(data["audit"].get("pii_entities_count", 0), int)
