import os
from fastapi.testclient import TestClient
from app.main import app


def test_stream_meta_includes_memory_reads_when_enabled():
    os.environ["PROJECT_GUIDE_ENABLED"] = "true"
    os.environ["MEMORY_SHORT_ENABLED"] = "true"
    os.environ["MEMORY_LONG_ENABLED"] = "true"

    client = TestClient(app)
    # Prime short memory by making a prior architect call with same user/session
    client.post("/architect", json={"question": "Seed turn", "user_id": "sse_user", "session_id": "sse_sess"})

    import json
    with client.stream("GET", "/architect/stream", params={"question": "What is RAG?", "user_id": "sse_user", "session_id": "sse_sess"}) as r:
        # Single-pass parse: detect meta event then parse its data line
        import json
        saw_meta = False
        awaiting_data = False
        for line in r.iter_lines():
            if not line:
                continue
            s = line if isinstance(line, str) else line.decode("utf-8", errors="ignore")
            if s.startswith("event: meta"):
                saw_meta = True
                awaiting_data = True
                continue
            if awaiting_data and s.startswith("data: "):
                payload = s[len("data: "):]
                meta = json.loads(payload)
                assert isinstance(meta, dict)
                assert ("memory_short_reads" in meta) or ("memory_long_reads" in meta)
                break
        assert saw_meta, "Did not receive meta event in stream"
