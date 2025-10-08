from fastapi.testclient import TestClient

from app.main import app


def test_architect_stream_sse_contract(monkeypatch):
    monkeypatch.setenv("PROJECT_GUIDE_ENABLED", "true")
    client = TestClient(app)

    r = client.get("/architect/stream", params={"question": "how does the router work?"})
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/event-stream")
    body = r.content.decode("utf-8", errors="ignore")
    # Should emit at least meta and audit events
    assert "event: meta" in body
    assert "event: audit" in body
