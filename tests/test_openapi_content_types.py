from fastapi.testclient import TestClient

from app.main import app


def test_openapi_metrics_content_type_plain_text():
    spec = app.openapi()
    metrics = spec["paths"]["/metrics"]["get"]
    content = metrics.get("responses", {}).get("200", {}).get("content", {})
    # It should advertise text/plain
    assert "text/plain" in content


def test_openapi_architect_stream_sse_content_type():
    spec = app.openapi()
    stream = spec["paths"]["/architect/stream"]["get"]
    content = stream.get("responses", {}).get("200", {}).get("content", {})
    # It should advertise text/event-stream
    assert "text/event-stream" in content


def test_openapi_architect_ui_html_content_type():
    spec = app.openapi()
    ui = spec["paths"]["/architect/ui"]["get"]
    content = ui.get("responses", {}).get("200", {}).get("content", {})
    # It should advertise text/html
    assert "text/html" in content
