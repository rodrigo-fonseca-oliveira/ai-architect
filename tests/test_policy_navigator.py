import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_policy_navigator_requires_role():
    r = client.post(
        "/policy_navigator", json={"question": "What are data retention requirements?"}
    )
    assert r.status_code == 403


def test_policy_navigator_happy_path(tmp_path):
    os.environ["POLICY_NAV_ENABLED"] = "true"
    # use stub embeddings for determinism
    os.environ["EMBEDDINGS_PROVIDER"] = "stub"
    headers = {"X-User-Role": "analyst"}
    r = client.post(
        "/policy_navigator",
        json={
            "question": "Outline GDPR obligations and AI policy considerations for data minimization."
        },
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "recommendation" in data and isinstance(data["recommendation"], str)
    assert "citations" in data and isinstance(data["citations"], list)
    assert "audit" in data and isinstance(data["audit"], dict)
    steps = data["audit"].get("steps", [])
    assert any(s.get("name") == "decompose" for s in steps)
    assert any(s.get("name") == "retrieve" for s in steps)
    assert any(s.get("name") == "synthesize" for s in steps)
