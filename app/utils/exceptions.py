from typing import Any, Dict

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _payload(
    status: int, error: str, detail: Any, request_id: str | None
) -> Dict[str, Any]:
    return {
        "status": status,
        "error": error,
        "detail": detail,
        "request_id": request_id,
    }


def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        _payload(exc.status_code, exc.detail or "HTTP error", exc.detail, req_id),
        status_code=exc.status_code,
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        _payload(422, "Validation error", exc.errors(), req_id), status_code=422
    )


def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        _payload(500, "Internal Server Error", str(exc), req_id), status_code=500
    )
