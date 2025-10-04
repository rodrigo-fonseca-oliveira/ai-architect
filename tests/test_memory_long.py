import os
import tempfile
from fastapi.testclient import TestClient

# Use stub embeddings for deterministic behavior
os.environ["EMBEDDINGS_PROVIDER"] = "stub"
VS_DIR = tempfile.mkdtemp()
os.environ["VECTORSTORE_PATH"] = VS_DIR

from app.main import app
client = TestClient(app)


def test_long_memory_reads_and_writes():
    os.environ["MEMORY_LONG_ENABLED"] = "true"
    user_id = "longuser"

    r1 = client.post("/query", json={
        "question": "Tell me a story about A. The response should be fairly long to allow ingestion of facts into memory store where sentences exceed fifty characters in length.",
        "user_id": user_id
    })
    assert r1.status_code == 200
    audit1 = r1.json()["audit"]
    # When long memory is enabled, audit extras should include counters
    assert audit1.get("memory_long_reads") is not None
    assert audit1.get("memory_long_writes") is not None

    r2 = client.post("/query", json={
        "question": "Follow up?",
        "user_id": user_id
    })
    assert r2.status_code == 200
    audit2 = r2.json()["audit"]
    assert "memory_long_reads" in audit2


def test_flag_off_long_memory():
    os.environ["MEMORY_LONG_ENABLED"] = "false"
    r = client.post("/query", json={"question": "hello"}, headers={"X-User-Role": "guest"})
    assert r.status_code == 200
    aud = r.json()["audit"]
    assert "memory_long_reads" not in aud
    assert "memory_long_writes" not in aud
