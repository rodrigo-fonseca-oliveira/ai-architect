import types

import pytest
from sqlalchemy.orm import Session

from app.utils.audit import write_audit


class DummySession:
    def __init__(self):
        self._added = []
        self._committed = False
        self._rolled_back = False

    def add(self, obj):
        self._added.append(obj)

    def commit(self):
        raise RuntimeError("DB down")

    def refresh(self, obj):
        pass

    def rollback(self):
        self._rolled_back = True


def test_write_audit_gracefully_handles_commit_failure(monkeypatch):
    db = DummySession()
    record = write_audit(
        db,
        request_id="req-x",
        endpoint="/test",
        user_id="u",
        compliance_flag=False,
    )
    # Even on failure, we should have constructed a record and rolled back
    assert hasattr(record, "endpoint")
    assert db._rolled_back is True
