import os
from fastapi.testclient import TestClient

from app.main import app


def test_metrics_open_when_no_token(monkeypatch):
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    c = TestClient(app)
    r = c.get("/metrics")
    assert r.status_code == 200


def test_metrics_protected_with_token(monkeypatch):
    # Ensure the router reads the new env by reloading the module
    monkeypatch.setenv("METRICS_TOKEN", "secret")
    import importlib
    from app.routers import metrics as metrics_module

    importlib.reload(metrics_module)

    c = TestClient(app)
    # Missing or wrong token -> 403
    r = c.get("/metrics")
    assert r.status_code == 403
    r = c.get("/metrics", headers={"X-Metrics-Token": "wrong"})
    assert r.status_code == 403
    # Correct token -> 200
    r = c.get("/metrics", headers={"X-Metrics-Token": "secret"})
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
