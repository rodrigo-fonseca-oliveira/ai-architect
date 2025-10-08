from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_is_not_counted_in_request_counters():
    client = TestClient(app)
    # Trigger at least one non-metrics request to ensure counters exist
    r = client.get("/healthz")
    assert r.status_code == 200

    # Scrape metrics (this should not increment app_requests_total for /metrics)
    metrics_text = client.get("/metrics").text
    lines = metrics_text.splitlines()

    # Ensure no counter sample is emitted for /metrics endpoint
    assert not any(
        line.startswith('app_requests_total{endpoint="/metrics"') for line in lines
    ), "app_requests_total should not include /metrics endpoint"
