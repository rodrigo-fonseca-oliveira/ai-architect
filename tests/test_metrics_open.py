from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_metrics_without_role_header_is_accessible_when_no_token():
    # With no METRICS_TOKEN set during tests, /metrics should be open
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
