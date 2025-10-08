from fastapi.testclient import TestClient

from app.main import app


def test_pii_types_payload_overrides_env(monkeypatch):
    # Ensure env would enable email by default
    monkeypatch.setenv("PII_TYPES", "email,ssn")
    client = TestClient(app)
    text = "email alice@example.com SSN 123-45-6789"

    # Request-level override: only ssn
    r = client.post(
        "/pii",
        json={"text": text, "types": ["ssn"]},
        headers={"X-User-Role": "analyst"},
    )
    assert r.status_code == 200
    data = r.json()
    # Email should be suppressed, SSN detected
    assert data.get("counts", {}).get("email", 0) == 0
    assert data.get("counts", {}).get("ssn", 0) >= 1
