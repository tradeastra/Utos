"""
UTOS Trading Engine — FastAPI application entry point.
"""

import asyncio
import os
import subprocess
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from api.v1 import api_router
from core.config import settings
from core.db_health import db_health_service
from core.exceptions import AuthenticationError, AuthorizationError, UTOSException
from core.logging import get_logger, setup_logging
from core.metrics import METRICS_CONTENT_TYPE, get_metrics, init_metrics
from core.middleware import (
    CorrelationIdMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from core.tracing import init_telemetry, shutdown_telemetry
from database.base import close_engine, get_engine, init_engine
from database.session import create_all_tables
from database.redis_client import close_redis, init_redis, redis_ping
import models  # noqa: F401 — ensure all models registered with Base.metadata
from engine import ExecutionEngine
from engine.grid.engine import GridEngine
from engine.profit_lock.engine import ProfitLockEngine
from engine.trading.process_manager import TradingProcessManager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from market.hub.market_hub import MarketHub
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

setup_logging()
logger = get_logger(__name__)

market_hub: MarketHub | None = None
execution_engine: ExecutionEngine | None = None
profit_lock_engine: ProfitLockEngine | None = None
grid_engine: GridEngine | None = None


def _run_alembic(args: list[str], backend_dir: Path) -> subprocess.CompletedProcess:
    """Run an alembic command as subprocess."""
    return subprocess.run(
        ["alembic", *args],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "PYTHONPATH": str(backend_dir)},
    )


async def _run_migrations() -> None:
    """Run alembic upgrade head as a subprocess.

    Uses subprocess to avoid asyncio.run() conflict inside the running event loop.
    If tables were created by create_all_tables (no alembic_version table),
    stamp head first so alembic knows the current state.
    """
    backend_dir = Path(__file__).resolve().parent
    try:
        import sqlalchemy as sa
        from database.base import get_engine

        engine = get_engine()
        need_stamp = False
        if engine:
            async with engine.connect() as conn:
                result = await conn.execute(
                    sa.text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version')"
                    )
                )
                has_alembic = result.scalar()

                if not has_alembic:
                    result2 = await conn.execute(
                        sa.text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                            "WHERE table_name = 'trading_instances')"
                        )
                    )
                    has_tables = result2.scalar()
                    need_stamp = bool(has_tables)

        if need_stamp:
            logger.info("Tables exist without alembic tracking — stamping to 0002 (base tables)")
            stamp_result = _run_alembic(["stamp", "0002"], backend_dir)
            if stamp_result.returncode != 0:
                logger.error(f"Alembic stamp failed: {stamp_result.stderr}")
                return
            logger.info("Alembic stamp completed")

        result = _run_alembic(["upgrade", "head"], backend_dir)
        if result.returncode == 0:
            logger.info("Alembic migration completed successfully")
            if result.stdout.strip():
                logger.info(f"Migration output: {result.stdout.strip()}")
        else:
            logger.error(f"Alembic migration failed (exit {result.returncode})")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("Alembic migration timed out after 60s")
    except FileNotFoundError:
        logger.warning("alembic not found — skipping migration")
    except Exception as exc:
        logger.error(f"Unexpected error during migration: {exc}")


async def _recover_trading_processes() -> None:
    """Recover RUNNING/PAUSED trading processes on startup."""
    try:
        engine = get_engine()
        if engine is None:
            logger.warning("Skipping process recovery: DB engine not initialized")
            return
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            manager = TradingProcessManager(session)
            recovered = await manager.recover()
            await session.commit()
            logger.info(f"Recovered {len(recovered)} trading process(es)")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Process recovery failed: {exc}")


async def _screen_breaker_thresholds() -> None:
    """Background task: pre-compute circuit breaker thresholds for all coins.

    Runs after Market Hub starts. Fetches all coins from active coin groups,
    screens them for continuation rates 70% / 80% / 90%, and persists results
    to the ``breaker_thresholds`` table. This makes thresholds available
    immediately when users open the setup wizard or admin page.

    Failures are logged but do not crash startup — the bot still works with
    fallback thresholds until the next re-screen.
    """
    from decimal import Decimal

    from repositories.coin_group_repository import CoinGroupRepository
    from services.breaker_screening_store import BreakerScreeningStore

    try:
        engine = get_engine()
        if engine is None or market_hub is None:
            logger.warning("Skipping breaker screening: engine or market hub not ready")
            return

        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            # Gather all coins from active coin groups.
            cg_repo = CoinGroupRepository(session)
            groups = await cg_repo.get_all(limit=500)
            symbols: list[str] = []
            for g in groups:
                if not g.is_active:
                    continue
                for c in (g.coins or []):
                    sym = c.upper()
                    # Coin groups store base symbols (BTC, ETH) — append USDT
                    # for screening since the bot trades XXXUSDT pairs.
                    if not sym.endswith("USDT"):
                        sym = sym + "USDT"
                    if sym not in symbols:
                        symbols.append(sym)

            if not symbols:
                logger.warning("Skipping breaker screening: no active coin groups with coins")
                return

            logger.info(
                "Starting breaker threshold screening",
                extra={"symbol_count": len(symbols), "rates": [0.70, 0.80, 0.90]},
            )

            store = BreakerScreeningStore(market_hub)
            await store.rescreen_for_rates(
                db=session,
                symbols=symbols,
                rates=[Decimal("0.70"), Decimal("0.80"), Decimal("0.90")],
            )
            await session.commit()

            logger.info("Breaker threshold screening completed on startup")
    except asyncio.CancelledError:
        logger.info("Breaker screening cancelled during shutdown")
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Breaker screening failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB engine + Redis, recover trading processes, start Market Hub and Execution Engine. Shutdown: close all."""
    global market_hub, execution_engine, profit_lock_engine, grid_engine
    logger.info("Starting UTOS Trading Engine", extra={"version": settings.VERSION})
    init_metrics()
    init_engine()
    engine = get_engine()
    if engine:
        await _run_migrations()
    await init_redis()
    await _recover_trading_processes()
    market_hub = MarketHub()

    # Register Binance adapter (testnet by default for staging safety)
    from exchanges.adapters.binance import BinanceSpotAdapter
    from exchanges.adapter import ExchangeAdapterConfig

    binance_adapter = BinanceSpotAdapter()
    binance_config = ExchangeAdapterConfig(
        exchange_name="binance",
        is_testnet=settings.APP_ENV != "production",
    )
    await binance_adapter.initialize(binance_config)
    market_hub.register_adapter("binance", binance_adapter)

    await market_hub.start()
    execution_engine = ExecutionEngine()
    profit_lock_engine = ProfitLockEngine(execution_engine)
    grid_engine = GridEngine(execution_engine, profit_lock_engine=profit_lock_engine)
    if settings.OTEL_ENABLED:
        init_telemetry(app)

    # Kick off breaker threshold screening in the background.
    # This pre-computes daily-drop circuit breaker thresholds for all
    # coins in active coin groups so the wizard / admin page has data
    # immediately. Runs async — does not block startup.
    screening_task = asyncio.create_task(_screen_breaker_thresholds())

    yield
    logger.info("Shutting down UTOS Trading Engine")
    screening_task.cancel()
    try:
        await screening_task
    except asyncio.CancelledError:
        pass
    if settings.OTEL_ENABLED:
        shutdown_telemetry()
    if market_hub is not None:
        await market_hub.stop()
        market_hub = None
    grid_engine = None
    profit_lock_engine = None
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


def _error_response(
    status_code: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


@app.exception_handler(UTOSException)
async def utos_exception_handler(request: Request, exc: UTOSException) -> JSONResponse:
    if isinstance(exc, AuthenticationError):
        return _error_response(
            401, exc.error_code or "AUTHENTICATION_ERROR", exc.message, exc.details
        )
    if isinstance(exc, AuthorizationError):
        return _error_response(
            403, exc.error_code or "AUTHORIZATION_ERROR", exc.message, exc.details
        )
    return _error_response(
        400, exc.error_code or "BAD_REQUEST", exc.message, exc.details
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=exc)
    detail = str(exc) if settings.DEBUG else None
    return _error_response(
        500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred", detail
    )


app.include_router(api_router, prefix="/api/v1")


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi import Response

    return Response(content=get_metrics(), media_type=METRICS_CONTENT_TYPE)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
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
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "services": {"database": db_ok, "redis": redis_ok},
    }
    return JSONResponse(content=payload, status_code=http_status)


@app.get("/live", tags=["health"])
async def liveness() -> JSONResponse:
    """Liveness probe — process is alive and can handle requests."""
    return JSONResponse(
        content={
            "status": "alive",
            "version": settings.VERSION,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        },
        status_code=200,
    )


@app.get("/ready", tags=["health"])
async def readiness() -> JSONResponse:
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
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "services": {"database": db_ok, "redis": redis_ok},
    }
    return JSONResponse(content=payload, status_code=http_status)


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "message": "UTOS Trading Engine API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/db/health", tags=["monitoring"])
async def db_health() -> JSONResponse:
    """Database health — pool stats, slow queries, replication lag, migration version, backup age."""
    health = await db_health_service.collect_all()
    status = "healthy"
    if health["backup_age_hours"] is not None and health["backup_age_hours"] > 24:
        status = "degraded"
    if health["replication_lag_seconds"] > 5:
        status = "degraded"
    http_status = (
        200 if status == "healthy" else 200
    )  # Always 200 — this is informational

    return JSONResponse(
        content={"status": status, **health},
        status_code=http_status,
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG
    )
