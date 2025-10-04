import json
import logging
import os
from typing import Any, Dict

LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


class JsonFormatter(logging.Formatter):
    def _safe_serialize(self, value: Any) -> Any:
        try:
            json.dumps(value)
            return value
        except Exception:
            return str(value)

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Include common attributes if present
        if hasattr(record, "request_id"):
            payload["request_id"] = getattr(record, "request_id")
        if hasattr(record, "extra") and isinstance(getattr(record, "extra"), dict):
            for k, v in getattr(record, "extra").items():
                payload[k] = self._safe_serialize(v)
        # Exceptions
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        # Ensure JSON-safe
        payload = {k: self._safe_serialize(v) for k, v in payload.items()}
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "app", level: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    # Resolve level from argument or env
    env_level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    env_level = LEVELS.get(env_level_name, logging.INFO)
    logger.setLevel(env_level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
