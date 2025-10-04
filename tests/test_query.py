from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_query_basic():
    payload = {"question": "What is GDPR?", "grounded": True, "user_id": "u-1"}
    r = client.post("/query", json=payload, headers={"X-User-Role": "analyst"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "audit" in data
    assert data["audit"]["request_id"]
    # if grounded, we expect citations array
    assert isinstance(data.get("citations", []), list)
