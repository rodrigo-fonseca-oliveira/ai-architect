from app.services.router import route_intent


def test_router_picks_pii_remediation_when_redaction_terms_present():
    q = "Please redact emails and mask SSN: 123-45-6789"
    assert route_intent(q, grounded=False) == "pii_remediation"


def test_router_picks_policy_navigator_on_policy_terms():
    q = "Summarize GDPR policy requirements for retention"
    assert route_intent(q, grounded=False) == "policy_navigator"
