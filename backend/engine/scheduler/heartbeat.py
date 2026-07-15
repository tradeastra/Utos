"""
HeartbeatMonitor — monitors health of all system components.

Registers health check functions for each component and runs them periodically.
Reports unhealthy components but does NOT recover — RecoveryCoordinator handles that.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HealthCheckResult:
    component: str
    healthy: bool
    last_check: datetime
    response_time_ms: float
    error: str | None = None


class HeartbeatMonitor:
    """Monitors health of system components via registered check functions."""

    def __init__(self, check_interval_seconds: int = 30) -> None:
        self._check_interval = check_interval_seconds
        self._checks: dict[str, Callable[[], Any]] = {}
        self._results: dict[str, HealthCheckResult] = {}
        self._metrics: dict[str, int] = {
            "checks_registered": 0,
            "checks_run": 0,
            "checks_healthy": 0,
            "checks_unhealthy": 0,
        }

    def register(self, component: str, check_fn: Callable[[], Any]) -> None:
        self._checks[component] = check_fn
        self._metrics["checks_registered"] += 1
        logger.info(f"Health check registered: {component}")

    def unregister(self, component: str) -> bool:
        if component not in self._checks:
            return False
        del self._checks[component]
        self._results.pop(component, None)
        return True

    async def check(self, component: str) -> HealthCheckResult:
        check_fn = self._checks.get(component)
        if check_fn is None:
            return HealthCheckResult(
                component=component,
                healthy=False,
                last_check=datetime.now(timezone.utc),
                response_time_ms=0.0,
                error="Component not registered",
            )

        start = time.monotonic()
        self._metrics["checks_run"] += 1

        try:
            result = check_fn()
            if isinstance(result, Coroutine):
                result = await result

            elapsed_ms = (time.monotonic() - start) * 1000
            healthy = bool(result) if not isinstance(result, tuple) else bool(result[0])
            error = None
            if isinstance(result, tuple) and len(result) > 1 and result[1]:
                error = str(result[1])

            hr = HealthCheckResult(
                component=component,
                healthy=healthy,
                last_check=datetime.now(timezone.utc),
                response_time_ms=round(elapsed_ms, 2),
                error=error,
            )
            self._results[component] = hr
            if healthy:
                self._metrics["checks_healthy"] += 1
            else:
                self._metrics["checks_unhealthy"] += 1
            return hr

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            hr = HealthCheckResult(
                component=component,
                healthy=False,
                last_check=datetime.now(timezone.utc),
                response_time_ms=round(elapsed_ms, 2),
                error=str(exc),
            )
            self._results[component] = hr
            self._metrics["checks_unhealthy"] += 1
            logger.error(f"Health check failed for {component}: {exc}")
            return hr

    async def check_all(self) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        for component in list(self._checks.keys()):
            result = await self.check(component)
            results.append(result)
        return results

    def get_unhealthy(self) -> list[HealthCheckResult]:
        return [r for r in self._results.values() if not r.healthy]

    def get_healthy(self) -> list[HealthCheckResult]:
        return [r for r in self._results.values() if r.healthy]

    def get_result(self, component: str) -> HealthCheckResult | None:
        return self._results.get(component)

    def get_registered_components(self) -> list[str]:
        return list(self._checks.keys())

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
