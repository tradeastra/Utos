"""
UTOS Trading Engine — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1 import api_router
from core.config import settings
from core.exceptions import AuthenticationError, AuthorizationError, UTOSException
from core.logging import get_logger, setup_logging
from database.base import close_engine, init_engine
from database.redis_client import close_redis, init_redis, redis_ping

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB engine + Redis. Shutdown: close both."""
    logger.info("Starting UTOS Trading Engine", extra={"version": settings.VERSION})
    init_engine()
    await init_redis()
    yield
    logger.info("Shutting down UTOS Trading Engine")
    await close_engine()
    await close_redis()


app = FastAPI(
    title="UTOS Trading Engine API",
    description="Unified Trading Operating System — Sprint 01",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


@app.exception_handler(UTOSException)
async def utos_exception_handler(request: Request, exc: UTOSException) -> JSONResponse:
    if isinstance(exc, AuthenticationError):
        return _error_response(401, exc.error_code or "AUTHENTICATION_ERROR", exc.message, exc.details)
    if isinstance(exc, AuthorizationError):
        return _error_response(403, exc.error_code or "AUTHORIZATION_ERROR", exc.message, exc.details)
    return _error_response(400, exc.error_code or "BAD_REQUEST", exc.message, exc.details)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=exc)
    detail = str(exc) if settings.DEBUG else None
    return _error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred", detail)


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Health check — verifies DB engine and Redis connectivity."""
    from database.base import get_engine
    from sqlalchemy import text

    db_ok = False
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB health check failed", extra={"error": str(exc)})

    redis_ok = await redis_ping()

    overall = "healthy" if (db_ok and redis_ok) else "degraded"
    http_status = 200 if overall == "healthy" else 503

    payload = {
        "status": overall,
        "version": settings.VERSION,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "services": {"database": db_ok, "redis": redis_ok},
    }
    return JSONResponse(content=payload, status_code=http_status)


@app.get("/", tags=["root"])
async def root() -> dict:
    return {"message": "UTOS Trading Engine API", "version": settings.VERSION, "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)