from fastapi.testclient import TestClient

from app.main import app


def test_metrics_requires_admin():
    c = TestClient(app)
    r = c.get("/metrics")
    assert r.status_code == 403
    r = c.get("/metrics", headers={"X-User-Role": "admin"})
    assert r.status_code == 200


def test_predict_requires_analyst_or_admin():
    c = TestClient(app)
    # guest forbidden
    r = c.post("/predict", json={"features": {"f0": 0.1}})
    assert r.status_code == 403


def test_query_grounded_guest_forbidden():
    c = TestClient(app)
    r = c.post("/query", json={"question": "What is GDPR?", "grounded": True})
    assert r.status_code == 403
    # analyst allowed
    r = c.post(
        "/query",
        json={"question": "What is GDPR?", "grounded": True},
        headers={"X-User-Role": "analyst"},
    )
    assert r.status_code == 200


def test_research_fetch_guest_forbidden():
    c = TestClient(app)
    r = c.post(
        "/research",
        json={"topic": "gdpr", "steps": ["search", "fetch", "summarize"]},
    )
    assert r.status_code == 403
    # analyst allowed
    r = c.post(
        "/research",
        json={"topic": "gdpr", "steps": ["search", "fetch", "summarize"]},
        headers={"X-User-Role": "analyst"},
    )
    assert r.status_code == 200
