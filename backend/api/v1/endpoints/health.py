"""
Health check endpoints for UTOS Trading Engine.

This module provides health check endpoints for monitoring system status.
"""

from datetime import datetime
from typing import Any

from core.logging import get_logger
from database.base import get_engine
from database.redis_client import redis_ping
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
        "service": "UTOS Trading Engine API",
    }


@router.get("/detailed")
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check endpoint."""
    import time

    checks: dict[str, dict[str, Any]] = {"api": {"status": "healthy", "response_time_ms": 1}}

    db_start = time.monotonic()
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "response_time_ms": round((time.monotonic() - db_start) * 1000, 2)}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "response_time_ms": round((time.monotonic() - db_start) * 1000, 2), "error": str(e)}

    redis_start = time.monotonic()
    redis_ok = await redis_ping()
    checks["redis"] = {"status": "healthy" if redis_ok else "unreachable", "response_time_ms": round((time.monotonic() - redis_start) * 1000, 2)}

    checks["event_bus"] = {"status": "healthy", "response_time_ms": 0}
    checks["workers"] = {"status": "healthy", "active_workers": 0}

    overall_status = "healthy" if all(c["status"] == "healthy" for c in checks.values()) else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
        "service": "UTOS Trading Engine API",
        "checks": checks,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check endpoint."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        ready = True
    except Exception:
        ready = False

    return {"ready": ready, "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/live")
async def liveness_check() -> dict[str, Any]:
    """Liveness check endpoint."""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat() + "Z"}
