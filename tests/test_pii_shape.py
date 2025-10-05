from fastapi.testclient import TestClient

from app.main import app


def test_pii_include_citations_shape_and_counts(monkeypatch):
    client = TestClient(app)
    payload = {
        "text": "Call me at (212) 555-0100 or email me@example.com",
        "include_citations": True,
    }
    resp = client.post("/pii", json=payload, headers={"X-User-Role": "analyst"})
    assert resp.status_code == 200
    data = resp.json()

    # types_present and counts coherence
    types_present = set(data.get("types_present") or [])
    counts = data.get("counts") or {}
    assert isinstance(counts, dict)
    for t in types_present:
        assert counts.get(t, 0) >= 1

    # entities shape
    entities = data.get("entities") or []
    assert isinstance(entities, list)
    assert all(set(e.keys()) >= {"type", "value_preview", "span"} for e in entities)

    # audit presence of pii_* fields
    audit = data.get("audit") or {}
    assert isinstance(audit.get("pii_counts"), dict)
    assert isinstance(audit.get("pii_types"), list) or audit.get("pii_types") is None
    assert isinstance(audit.get("pii_entities_count"), int)
