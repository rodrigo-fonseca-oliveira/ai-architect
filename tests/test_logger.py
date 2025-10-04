import json
import logging
from io import StringIO

from app.utils.logger import get_logger
from app.utils.logger import JsonFormatter


def test_logger_includes_request_id_and_exc_info():
    logger = get_logger("app.test")

    # Attach a temporary handler to capture formatted JSON
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    try:
        try:
            1 / 0
        except Exception:
            logger.error("boom", extra={"request_id": "req-123"}, exc_info=True)
        handler.flush()
        out = buf.getvalue()
        assert "req-123" in out
        assert "boom" in out
        assert "Traceback" in out
    finally:
        logger.removeHandler(handler)
