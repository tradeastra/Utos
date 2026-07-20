"""
RecoveryCoordinator — orchestrates recovery across all 4 layers.

NOT a God Object — delegates to:
- Layer 1: ConnectionRecovery
- Layer 2: StateRecovery
- Layer 3: RuntimeReconciler
- Layer 4: Chaos tests (in test suite)

The coordinator manages the recovery lifecycle:
1. Register instances that need recovery
2. Execute recovery in order: connection → state → reconciliation
3. Track recovery status per instance
4. Emit recovery events
5. Persist checkpoints for resumability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.exceptions import RecoveryError
from core.logging import get_logger

from engine.recovery.connection import ConnectionRecovery
from engine.recovery.persistence import RecoveryCheckpoint, RecoveryPersistence
from engine.recovery.reconciler import ReconciliationResult, RuntimeReconciler
from engine.recovery.state import StateRecovery

logger = get_logger(__name__)


@dataclass
class InstanceContext:
    """Context for a Trading Instance that needs recovery."""

    instance_id: str
    account_id: str
    exchange: str
    symbol: str
    has_grid: bool = False
    has_profit_lock: bool = False


@dataclass
class RecoveryReport:
    """Full recovery report for a single instance."""

    instance_id: str
    started_at: datetime
    completed_at: datetime | None
    connection_ok: bool
    state_ok: bool
    reconciliation_ok: bool
    errors: list[str] = field(default_factory=list)
    reconciliation_results: list[ReconciliationResult] = field(default_factory=list)


@dataclass
class RecoveryStatus:
    """Current recovery status for an instance."""

    instance_id: str
    state: str  # "idle" | "recovering" | "completed" | "failed"
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None


class RecoveryCoordinator:
    """Orchestrates recovery across all 4 layers.

    Delegates to specialized modules — does NOT implement recovery logic itself.
    """

    def __init__(
        self,
        connection_recovery: ConnectionRecovery,
        state_recovery: StateRecovery,
        reconciler: RuntimeReconciler,
        persistence: RecoveryPersistence | None = None,
    ) -> None:
        self._connection = connection_recovery
        self._state = state_recovery
        self._reconciler = reconciler
        self._persistence = persistence or RecoveryPersistence()

        self._instances: dict[str, InstanceContext] = {}
        self._statuses: dict[str, RecoveryStatus] = {}
        self._metrics: dict[str, int] = {
            "recoveries_started": 0,
            "recoveries_completed": 0,
            "recoveries_failed": 0,
            "instances_registered": 0,
        }

    def register_instance(self, instance_id: str, context: InstanceContext) -> None:
        """Register an instance that may need recovery."""
        self._instances[instance_id] = context
        self._statuses[instance_id] = RecoveryStatus(
            instance_id=instance_id,
            state="idle",
            started_at=None,
            completed_at=None,
            last_error=None,
        )
        self._metrics["instances_registered"] += 1
        logger.info(
            "Instance registered for recovery",
            extra={"instance_id": instance_id, "has_grid": context.has_grid},
        )

    async def recover_instance(self, instance_id: str) -> RecoveryReport:
        """Execute full recovery for a single instance.

        Order: connection → state → reconciliation
        Each layer fails independently — errors are collected, not raised.
        """
        if instance_id not in self._instances:
            raise RecoveryError(f"Instance {instance_id} not registered for recovery")

        context = self._instances[instance_id]
        started_at = datetime.now(UTC)
        self._metrics["recoveries_started"] += 1

        self._statuses[instance_id] = RecoveryStatus(
            instance_id=instance_id,
            state="recovering",
            started_at=started_at,
            completed_at=None,
            last_error=None,
        )

        logger.info(
            "Recovery started",
            extra={"instance_id": instance_id, "exchange": context.exchange},
        )

        report = RecoveryReport(
            instance_id=instance_id,
            started_at=started_at,
            completed_at=None,
            connection_ok=False,
            state_ok=False,
            reconciliation_ok=False,
        )

        # Layer 1: Connection Recovery
        try:
            redis_ok = await self._connection.recover_redis()
            postgres_ok = await self._connection.recover_postgres()
            report.connection_ok = redis_ok and postgres_ok
            if not report.connection_ok:
                report.errors.append(
                    f"Connection recovery partial: redis={redis_ok}, postgres={postgres_ok}"
                )
            self._persistence.save_checkpoint(
                instance_id,
                RecoveryCheckpoint(
                    instance_id=instance_id,
                    created_at=datetime.now(UTC),
                    phase="connection",
                    data={"redis_ok": redis_ok, "postgres_ok": postgres_ok},
                ),
            )
        except Exception as exc:
            report.errors.append(f"Connection recovery failed: {exc}")
            logger.error(
                f"Connection recovery failed: {exc}", extra={"instance_id": instance_id}
            )

        # Layer 2: State Recovery
        try:
            process_ok = await self._state.recover_trading_process(instance_id)
            grid_state = None
            profit_lock_state = None

            if context.has_grid:
                grid_state = await self._state.recover_grid(instance_id)

            if context.has_profit_lock:
                profit_lock_state = await self._state.recover_profit_lock(instance_id)

            portfolio_positions = await self._state.recover_portfolio(instance_id)

            report.state_ok = process_ok
            if not process_ok:
                report.errors.append("Trading process recovery failed")

            self._persistence.save_checkpoint(
                instance_id,
                RecoveryCheckpoint(
                    instance_id=instance_id,
                    created_at=datetime.now(UTC),
                    phase="state",
                    data={
                        "process_ok": process_ok,
                        "grid_recovered": grid_state is not None,
                        "profit_lock_recovered": profit_lock_state is not None,
                        "portfolio_count": len(portfolio_positions),
                    },
                ),
            )
        except Exception as exc:
            report.errors.append(f"State recovery failed: {exc}")
            logger.error(
                f"State recovery failed: {exc}", extra={"instance_id": instance_id}
            )

        # Layer 3: Runtime Reconciliation
        try:
            if context.has_grid:
                grid_state = await self._state.recover_grid(instance_id)
                if grid_state is not None:
                    live_orders: list[Any] = []
                    grid_result = await self._reconciler.reconcile_grid(
                        instance_id, grid_state, live_orders
                    )
                    report.reconciliation_results.append(grid_result)

            local_positions = self._state.get_portfolio_manager().get_positions()
            exchange_positions: list[Any] = []
            portfolio_result = await self._reconciler.reconcile_portfolio(
                instance_id, local_positions, exchange_positions
            )
            report.reconciliation_results.append(portfolio_result)

            report.reconciliation_ok = all(
                r.action != "failed" for r in report.reconciliation_results
            )

            self._persistence.save_checkpoint(
                instance_id,
                RecoveryCheckpoint(
                    instance_id=instance_id,
                    created_at=datetime.now(UTC),
                    phase="reconciliation",
                    data={
                        "results": [
                            {
                                "component": r.component,
                                "action": r.action,
                                "count": r.count,
                            }
                            for r in report.reconciliation_results
                        ],
                    },
                ),
            )
        except Exception as exc:
            report.errors.append(f"Reconciliation failed: {exc}")
            logger.error(
                f"Reconciliation failed: {exc}", extra={"instance_id": instance_id}
            )

        # Finalize
        report.completed_at = datetime.now(UTC)

        if not report.errors:
            self._statuses[instance_id] = RecoveryStatus(
                instance_id=instance_id,
                state="completed",
                started_at=started_at,
                completed_at=report.completed_at,
                last_error=None,
            )
            self._metrics["recoveries_completed"] += 1
            self._persistence.clear_checkpoint(instance_id)
            logger.info(
                "Recovery completed successfully",
                extra={"instance_id": instance_id},
            )
        else:
            self._statuses[instance_id] = RecoveryStatus(
                instance_id=instance_id,
                state="failed" if len(report.errors) > 2 else "completed",
                started_at=started_at,
                completed_at=report.completed_at,
                last_error=report.errors[0] if report.errors else None,
            )
            if self._statuses[instance_id].state == "failed":
                self._metrics["recoveries_failed"] += 1
            else:
                self._metrics["recoveries_completed"] += 1
            logger.warning(
                "Recovery completed with errors",
                extra={
                    "instance_id": instance_id,
                    "errors": len(report.errors),
                },
            )

        return report

    async def recover_all(self) -> dict[str, RecoveryReport]:
        """Recover all registered instances."""
        results: dict[str, RecoveryReport] = {}
        for instance_id in list(self._instances.keys()):
            results[instance_id] = await self.recover_instance(instance_id)
        return results

    def get_recovery_status(self, instance_id: str) -> RecoveryStatus:
        return self._statuses.get(
            instance_id,
            RecoveryStatus(
                instance_id=instance_id,
                state="idle",
                started_at=None,
                completed_at=None,
                last_error=None,
            ),
        )

    def get_registered_instances(self) -> list[str]:
        return list(self._instances.keys())

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
