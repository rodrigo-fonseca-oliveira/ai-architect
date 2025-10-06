from fastapi.testclient import TestClient
from app.main import app

def test_architect_ui_serves_chat_page():
    client = TestClient(app)
    r = client.get('/architect/ui')
    assert r.status_code == 200
    html = r.text
    # Basic smoke checks for new UI elements
    assert 'AI Architect' in html
    assert 'architect/stream' in html or 'EventSource' in html
    assert 'featureCta' in html
