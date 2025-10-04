import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .routers.metrics import router as metrics_router
from .routers.query import router as query_router
from .routers.research import router as research_router
from .utils.logger import get_logger
from .utils.metrics import request_count, request_latency

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "local")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REQUEST_ID_HEADER = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")

logger = get_logger(level=LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info({"event": "startup", "env": APP_ENV})
    # Initialize DB tables
    try:
        from db.session import init_db
        init_db()
    except Exception as e:
        logger.error({"event": "db_init_error", "error": str(e)})
    yield
    logger.info({"event": "shutdown"})


app = FastAPI(title="AI Risk & Compliance Monitor", version="0.1.0", lifespan=lifespan)

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next: Callable):
    start = time.perf_counter()
    req_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    # Attach to request state for downstream
    request.state.request_id = req_id

    response: Response = Response(status_code=500)
    endpoint = request.url.path
    try:
        response = await call_next(request)
    except Exception as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            {
                "event": "request_error",
                "method": request.method,
                "path": endpoint,
                "error": str(e),
                "request_id": req_id,
                "latency_ms": duration_ms,
            }
        )
        request_count.labels(endpoint=endpoint, status="500").inc()
        request_latency.labels(endpoint=endpoint).observe(duration_ms / 1000.0)
        raise
    else:
        duration_ms = int((time.perf_counter() - start) * 1000)
        request_count.labels(endpoint=endpoint, status=str(response.status_code)).inc()
        request_latency.labels(endpoint=endpoint).observe(duration_ms / 1000.0)
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            {
                "event": "request",
                "method": request.method,
                "path": endpoint,
                "status_code": getattr(response, "status_code", -1),
                "request_id": req_id,
                "latency_ms": duration_ms,
            }
        )
        response.headers[REQUEST_ID_HEADER] = req_id
    return response


# Routers
app.include_router(metrics_router)
app.include_router(query_router)
app.include_router(research_router)
