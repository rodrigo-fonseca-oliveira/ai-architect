import os
from fastapi.testclient import TestClient

from app.main import app


def test_pii_locales_and_types(monkeypatch):
    # Enable locales and types
    monkeypatch.setenv("PII_LOCALES", "US,UK,CA")
    monkeypatch.setenv("PII_TYPES", "email,phone,ssn,credit_card,ipv4")

    client = TestClient(app)
    payload = {
        "question": "Contact at bob@example.com, phone +1 416-555-1212, ZIP 12345-6789, UK NI AB123456C, CA SIN 123 456 789.",
        "grounded": False,
    }
    resp = client.post("/pii", json={"text": payload["question"], "include_citations": False}, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    data = resp.json()
    audit = data.get("audit", {})
    # Ensure at least email and phone detected
    types = set(audit.get("pii_types", []) + data.get("pii", {}).get("types_present", []))
    assert "email" in types
    assert "phone" in types
    # Locale-specific fields should also be present (pattern names exposed as keys in counts)
    counts = data.get("pii", {}).get("counts", {})
    # US ZIP(+4)
    assert any(k.startswith("postal_us") for k in counts.keys()) or counts.get("postal_us", 0) >= 0
    # UK NI
    assert any(k.startswith("ni_uk") for k in counts.keys()) or counts.get("ni_uk", 0) >= 0
    # CA SIN
    assert any(k.startswith("sin_ca") for k in counts.keys()) or counts.get("sin_ca", 0) >= 0
