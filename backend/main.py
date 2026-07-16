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
from core.metrics import init_metrics, get_metrics, METRICS_CONTENT_TYPE
from core.middleware import (
    CorrelationIdMiddleware,
    MetricsMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)
from core.tracing import init_telemetry, shutdown_telemetry
from database.base import close_engine, get_engine, init_engine
from database.redis_client import close_redis, init_redis, redis_ping
from engine import ExecutionEngine
from engine.trading.process_manager import TradingProcessManager
from market.hub.market_hub import MarketHub
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

setup_logging()
logger = get_logger(__name__)

market_hub: MarketHub | None = None
execution_engine: ExecutionEngine | None = None


async def _recover_trading_processes() -> None:
    """Recover RUNNING/PAUSED trading processes on startup."""
    try:
        engine = get_engine()
        if engine is None:
            logger.warning("Skipping process recovery: DB engine not initialized")
            return
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            manager = TradingProcessManager(session)
            recovered = await manager.recover()
            await session.commit()
            logger.info(f"Recovered {len(recovered)} trading process(es)")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Process recovery failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB engine + Redis, recover trading processes, start Market Hub and Execution Engine. Shutdown: close all."""
    global market_hub, execution_engine
    logger.info("Starting UTOS Trading Engine", extra={"version": settings.VERSION})
    init_metrics()
    init_engine()
    await init_redis()
    await _recover_trading_processes()
    market_hub = MarketHub()
    await market_hub.start()
    execution_engine = ExecutionEngine()
    if settings.OTEL_ENABLED:
        init_telemetry(app)
    yield
    logger.info("Shutting down UTOS Trading Engine")
    if settings.OTEL_ENABLED:
        shutdown_telemetry()
    if market_hub is not None:
        await market_hub.stop()
        market_hub = None
    execution_engine = None
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
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)


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


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi import Response
    return Response(content=get_metrics(), media_type=METRICS_CONTENT_TYPE)


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


@app.get("/live", tags=["health"])
async def liveness() -> dict:
    """Liveness probe — process is alive and can handle requests."""
    return JSONResponse(
        content={
            "status": "alive",
            "version": settings.VERSION,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
        status_code=200,
    )


@app.get("/ready", tags=["health"])
async def readiness() -> dict:
    """Readiness probe — all dependencies are connected and ready to serve."""
    from database.base import get_engine
    from sqlalchemy import text

    db_ok = False
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB readiness check failed", extra={"error": str(exc)})

    redis_ok = await redis_ping()

    ready = db_ok and redis_ok
    http_status = 200 if ready else 503

    payload = {
        "status": "ready" if ready else "not_ready",
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