from app.services.pii_detector import detect_pii


def test_detect_email_and_mask():
    text = "Contact me at alice.smith+test@example.org for details."
    res = detect_pii(text)
    assert res["counts"].get("email", 0) == 1
    ent = next(e for e in res["entities"] if e["type"] == "email")
    assert "@" in ent["value_preview"] or ent["value_preview"].startswith("al")
    assert "example.org"[-2:] == ent["value_preview"][-2:]


def test_detect_ssn():
    text = "My SSN is 123-45-6789."
    res = detect_pii(text)
    assert res["counts"].get("ssn", 0) == 1


def test_credit_card_luhn_validation():
    # 4111 1111 1111 1111 is a common Visa test number
    text = "card 4111 1111 1111 1111"
    res = detect_pii(text)
    assert res["counts"].get("credit_card", 0) == 1


def test_router_integration_audit_fields(monkeypatch, client=None):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("ROUTER_ENABLED", "true")
    payload = {"question": "Email is bob@example.com", "grounded": False}

    client = TestClient(app)
    resp = client.post("/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    audit = data["audit"]
    assert audit.get("router_intent") == "pii_detect"
    assert isinstance(audit.get("pii_entities_count"), int)
    assert isinstance(audit.get("pii_types"), list)
