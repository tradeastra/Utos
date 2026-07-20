"""
Layer 2: StateRecovery — rebuilds in-memory state from persistent storage.

Recovers Trading Process, Grid, Profit Lock, and Portfolio state
from database (PostgreSQL) and persistence layers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.domain_types import GridState, PositionEntry
from core.logging import get_logger

from engine.grid.persistence import GridPersistence
from engine.profit_lock.persistence import ProfitPersistence
from engine.profit_lock.state import ProfitLockState
from engine.risk.portfolio import PortfolioManager, Position

logger = get_logger(__name__)


class StateRecovery:
    """Layer 2: Rebuilds in-memory state from persistent storage.

    Does NOT know about exchange API — uses callbacks for DB access.
    """

    def __init__(
        self,
        load_instance_fn: Callable[[str], dict[str, Any]] | None = None,
        load_grid_snapshot_fn: Callable[[str], str | None] | None = None,
        load_profit_lock_snapshot_fn: Callable[[str], str | None] | None = None,
        fetch_exchange_positions_fn: Callable[[str], list[PositionEntry]] | None = None,
        portfolio: PortfolioManager | None = None,
    ) -> None:
        self._load_instance_fn = load_instance_fn
        self._load_grid_snapshot_fn = load_grid_snapshot_fn
        self._load_profit_lock_snapshot_fn = load_profit_lock_snapshot_fn
        self._fetch_exchange_positions_fn = fetch_exchange_positions_fn
        self._portfolio = portfolio or PortfolioManager()
        self._recovered_instances: set[str] = set()
        self._metrics: dict[str, int] = {
            "processes_recovered": 0,
            "grids_recovered": 0,
            "profit_locks_recovered": 0,
            "portfolios_recovered": 0,
            "recovery_failures": 0,
        }

    async def recover_trading_process(self, instance_id: str) -> bool:
        """Recover Trading Process state from database."""
        logger.info("Recovering trading process", extra={"instance_id": instance_id})

        if self._load_instance_fn is None:
            logger.warning("No load_instance_fn set, skipping process recovery")
            return True

        try:
            data = self._load_instance_fn(instance_id)
            if data is None:
                logger.warning(
                    "No instance data found",
                    extra={"instance_id": instance_id},
                )
                self._metrics["recovery_failures"] += 1
                return False

            self._recovered_instances.add(instance_id)
            self._metrics["processes_recovered"] += 1
            logger.info(
                "Trading process recovered",
                extra={"instance_id": instance_id, "status": data.get("status")},
            )
            return True
        except Exception as exc:
            self._metrics["recovery_failures"] += 1
            logger.error(
                f"Failed to recover trading process: {exc}",
                extra={"instance_id": instance_id},
            )
            return False

    async def recover_grid(self, instance_id: str) -> GridState | None:
        """Recover Grid State from persistence snapshot."""
        logger.info("Recovering grid state", extra={"instance_id": instance_id})

        if self._load_grid_snapshot_fn is None:
            logger.warning("No load_grid_snapshot_fn set, skipping grid recovery")
            return None

        try:
            json_str = self._load_grid_snapshot_fn(instance_id)
            if json_str is None:
                logger.info(
                    "No grid snapshot found",
                    extra={"instance_id": instance_id},
                )
                return None

            grid_state = GridPersistence.from_json_string(json_str)
            self._metrics["grids_recovered"] += 1
            logger.info(
                "Grid state recovered",
                extra={
                    "instance_id": instance_id,
                    "status": grid_state.status,
                    "levels": len(grid_state.levels),
                },
            )
            return grid_state
        except Exception as exc:
            self._metrics["recovery_failures"] += 1
            logger.error(
                f"Failed to recover grid state: {exc}",
                extra={"instance_id": instance_id},
            )
            return None

    async def recover_profit_lock(self, instance_id: str) -> ProfitLockState | None:
        """Recover Profit Lock State from persistence snapshot."""
        logger.info("Recovering profit lock state", extra={"instance_id": instance_id})

        if self._load_profit_lock_snapshot_fn is None:
            logger.warning(
                "No load_profit_lock_snapshot_fn set, skipping profit lock recovery"
            )
            return None

        try:
            json_str = self._load_profit_lock_snapshot_fn(instance_id)
            if json_str is None:
                logger.info(
                    "No profit lock snapshot found",
                    extra={"instance_id": instance_id},
                )
                return None

            state = ProfitPersistence.from_json_string(json_str)
            self._metrics["profit_locks_recovered"] += 1
            logger.info(
                "Profit lock state recovered",
                extra={
                    "instance_id": instance_id,
                    "enabled": state.enabled,
                    "status": state.status,
                },
            )
            return state
        except Exception as exc:
            self._metrics["recovery_failures"] += 1
            logger.error(
                f"Failed to recover profit lock state: {exc}",
                extra={"instance_id": instance_id},
            )
            return None

    async def recover_portfolio(self, instance_id: str) -> list[Position]:
        """Recover portfolio positions from exchange."""
        logger.info("Recovering portfolio", extra={"instance_id": instance_id})

        if self._fetch_exchange_positions_fn is None:
            logger.warning(
                "No fetch_exchange_positions_fn set, skipping portfolio recovery"
            )
            return []

        try:
            exchange_positions = self._fetch_exchange_positions_fn(instance_id)
            rebuilt: list[Position] = []

            for _i, ep in enumerate(exchange_positions):
                position = self._portfolio.register_position(
                    instance_id=instance_id,
                    account_id=f"recovered-{instance_id}",
                    exchange="recovered",
                    symbol=ep.symbol,
                    side=ep.side,
                    entry_price=ep.entry_price,
                    quantity=ep.quantity,
                )
                rebuilt.append(position)

            self._metrics["portfolios_recovered"] += 1
            logger.info(
                "Portfolio recovered",
                extra={"instance_id": instance_id, "positions": len(rebuilt)},
            )
            return rebuilt
        except Exception as exc:
            self._metrics["recovery_failures"] += 1
            logger.error(
                f"Failed to recover portfolio: {exc}",
                extra={"instance_id": instance_id},
            )
            return []

    def get_portfolio_manager(self) -> PortfolioManager:
        return self._portfolio

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
