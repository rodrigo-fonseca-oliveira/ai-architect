import time
from fastapi.testclient import TestClient

from app.main import app


def _get_pii_200_count(client: TestClient) -> float:
    metrics = client.get("/metrics").text.splitlines()
    for line in metrics:
        if line.startswith('app_requests_total{endpoint="/pii",status="200"}'):
            try:
                return float(line.split(" ")[1])
            except Exception:
                return 0.0
    return 0.0


def test_metrics_delta_for_pii_requests(monkeypatch):
    client = TestClient(app)

    before = _get_pii_200_count(client)

    # Make a couple of PII calls
    for _ in range(2):
        resp = client.post(
            "/pii",
            json={"text": "my email is bob@example.com", "include_citations": False},
            headers={"X-User-Role": "analyst"},
        )
        assert resp.status_code == 200

    after = _get_pii_200_count(client)

    assert after >= before + 2 - 1e-6
