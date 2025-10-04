from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_metrics_text():
    r = client.get("/metrics", headers={"X-User-Role": "admin"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert b"app_requests_total" in r.content
