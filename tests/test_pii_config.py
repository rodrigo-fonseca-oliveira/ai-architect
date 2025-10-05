from app.services.pii_detector import detect_pii


def test_pii_types_env_disables_email(monkeypatch):
    monkeypatch.setenv("PII_TYPES", "ssn")
    res = detect_pii("email alice@example.com SSN 123-45-6789")
    assert res["counts"].get("email", 0) == 0
    assert res["counts"].get("ssn", 0) == 1
