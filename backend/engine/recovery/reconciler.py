"""
Layer 3: RuntimeReconciler — reconciles local state against exchange live state.

Detects and resolves divergences between local Grid/Portfolio state
and the actual state on the exchange.

Key operations:
- find_missing_orders: orders in local state but NOT on exchange (need re-placement)
- find_orphan_orders: orders on exchange but NOT in local state (need cancellation or adoption)
- reconcile_grid: full grid reconciliation
- reconcile_portfolio: full portfolio reconciliation
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain_types import (
    GridLevel,
    GridLevelStatus,
    GridState,
    OrderResult,
    OrderStatus,
    PositionEntry,
)
from core.logging import get_logger

from engine.risk.portfolio import PortfolioManager, Position

logger = get_logger(__name__)


@dataclass
class ReconciliationResult:
    """Result of a reconciliation operation."""

    component: str  # "grid" | "portfolio" | "profit_lock"
    action: str  # "restored" | "cancelled" | "skipped" | "failed"
    count: int
    details: list[str] = field(default_factory=list)


class RuntimeReconciler:
    """Layer 3: Reconciles local state with exchange live state.

    Does NOT call exchange API directly — receives live data via parameters.
    Does NOT modify exchange state — only updates local state and reports.
    """

    def __init__(
        self,
        portfolio: PortfolioManager | None = None,
    ) -> None:
        self._portfolio = portfolio or PortfolioManager()
        self._metrics: dict[str, int] = {
            "grid_reconciliations": 0,
            "portfolio_reconciliations": 0,
            "missing_orders_found": 0,
            "orphan_orders_found": 0,
            "positions_added": 0,
            "positions_closed": 0,
            "reconciliation_failures": 0,
        }

    def find_missing_orders(
        self, grid_state: GridState, live_orders: list[OrderResult]
    ) -> list[GridLevel]:
        """Find grid levels that have order IDs in local state but NOT on exchange.

        These orders were likely cancelled by the exchange or lost during disconnect.
        They need to be re-placed if the grid is still active.
        """
        live_order_ids = {
            o.exchange_order_id
            for o in live_orders
            if o.status not in (OrderStatus.FILLED.value, OrderStatus.CANCELLED.value)
        }

        missing: list[GridLevel] = []
        for level in grid_state.levels:
            if level.status == GridLevelStatus.OPEN and (
                level.buy_order_id
                and level.buy_order_id not in live_order_ids
                or level.sell_order_id
                and level.sell_order_id not in live_order_ids
            ):
                missing.append(level)

        self._metrics["missing_orders_found"] += len(missing)
        return missing

    def find_orphan_orders(
        self, grid_state: GridState, live_orders: list[OrderResult]
    ) -> list[OrderResult]:
        """Find orders on exchange that are NOT tracked in local grid state.

        These could be:
        - Orders from a previous session that weren't cleaned up
        - Orders placed manually on the exchange
        - Orders from a crashed session
        """
        local_order_ids: set[str] = set()
        for level in grid_state.levels:
            if level.buy_order_id:
                local_order_ids.add(level.buy_order_id)
            if level.sell_order_id:
                local_order_ids.add(level.sell_order_id)

        orphans: list[OrderResult] = []
        for order in live_orders:
            if (
                order.status
                not in (OrderStatus.FILLED.value, OrderStatus.CANCELLED.value)
                and order.exchange_order_id not in local_order_ids
            ):
                orphans.append(order)

        self._metrics["orphan_orders_found"] += len(orphans)
        return orphans

    async def reconcile_grid(
        self,
        instance_id: str,
        grid_state: GridState,
        live_orders: list[OrderResult],
    ) -> ReconciliationResult:
        """Full grid reconciliation.

        1. Find filled orders on exchange → mark grid levels as FILLED
        2. Find cancelled orders on exchange → mark grid levels as WAITING
        3. Find missing orders (local has order_id, exchange doesn't) → mark for re-placement
        4. Find orphan orders (exchange has, local doesn't) → report for manual review
        """
        logger.info(
            "Starting grid reconciliation",
            extra={"instance_id": instance_id, "levels": len(grid_state.levels)},
        )
        self._metrics["grid_reconciliations"] += 1
        details: list[str] = []
        action_count = 0

        live_order_map: dict[str, OrderResult] = {
            o.exchange_order_id: o for o in live_orders
        }

        # Phase 1: Update level statuses based on exchange state
        for level in grid_state.levels:
            if level.buy_order_id and level.buy_order_id in live_order_map:
                exchange_order = live_order_map[level.buy_order_id]
                if exchange_order.status == OrderStatus.FILLED.value:
                    if level.status != GridLevelStatus.FILLED:
                        level.status = GridLevelStatus.FILLED
                        action_count += 1
                        details.append(
                            f"Level {level.level} buy order filled on exchange"
                        )
                elif (
                    exchange_order.status == OrderStatus.CANCELLED.value
                    and level.status == GridLevelStatus.OPEN
                ):
                    level.status = GridLevelStatus.WAITING
                    level.buy_order_id = None
                    action_count += 1
                    details.append(
                        f"Level {level.level} buy order cancelled on exchange"
                    )

            if level.sell_order_id and level.sell_order_id in live_order_map:
                exchange_order = live_order_map[level.sell_order_id]
                if exchange_order.status == OrderStatus.FILLED.value:
                    if level.status != GridLevelStatus.TP_HIT:
                        level.status = GridLevelStatus.TP_HIT
                        action_count += 1
                        details.append(
                            f"Level {level.level} sell order filled on exchange"
                        )
                elif (
                    exchange_order.status == OrderStatus.CANCELLED.value
                    and level.status == GridLevelStatus.OPEN
                ):
                    level.sell_order_id = None
                    action_count += 1
                    details.append(
                        f"Level {level.level} sell order cancelled on exchange"
                    )

        # Phase 2: Find missing and orphan orders
        missing = self.find_missing_orders(grid_state, live_orders)
        if missing:
            for lvl in missing:
                details.append(
                    f"Level {lvl.level} has missing order (needs re-placement)"
                )

        orphans = self.find_orphan_orders(grid_state, live_orders)
        if orphans:
            for o in orphans:
                details.append(
                    f"Orphan order {o.exchange_order_id} found on exchange (manual review)"
                )

        action = "restored" if action_count > 0 else "skipped"
        result = ReconciliationResult(
            component="grid",
            action=action,
            count=action_count + len(missing) + len(orphans),
            details=details,
        )
        logger.info(
            "Grid reconciliation complete",
            extra={
                "instance_id": instance_id,
                "action": action,
                "count": result.count,
            },
        )
        return result

    async def reconcile_portfolio(
        self,
        instance_id: str,
        local_positions: list[Position],
        exchange_positions: list[PositionEntry],
    ) -> ReconciliationResult:
        """Full portfolio reconciliation.

        1. Find positions on exchange but NOT in local state → add them
        2. Find positions in local state but NOT on exchange → close them
        3. Report any quantity differences
        """
        logger.info(
            "Starting portfolio reconciliation",
            extra={
                "instance_id": instance_id,
                "local": len(local_positions),
                "exchange": len(exchange_positions),
            },
        )
        self._metrics["portfolio_reconciliations"] += 1
        details: list[str] = []
        action_count = 0

        local_symbols = {p.symbol for p in local_positions if not p.closed}
        exchange_symbols = {p.symbol for p in exchange_positions}

        # Phase 1: Add missing positions (on exchange but not locally)
        missing_on_local = exchange_symbols - local_symbols
        for ep in exchange_positions:
            if ep.symbol in missing_on_local:
                try:
                    self._portfolio.register_position(
                        instance_id=f"{instance_id}-reconciled-{ep.symbol}",
                        account_id=f"reconciled-{instance_id}",
                        exchange="reconciled",
                        symbol=ep.symbol,
                        side=ep.side,
                        entry_price=ep.entry_price,
                        quantity=ep.quantity,
                    )
                    action_count += 1
                    self._metrics["positions_added"] += 1
                    details.append(
                        f"Added missing position {ep.symbol} ({ep.side}, qty={ep.quantity})"
                    )
                except Exception as exc:
                    details.append(f"Failed to add position {ep.symbol}: {exc}")

        # Phase 2: Close stale positions (locally but not on exchange)
        stale = local_symbols - exchange_symbols
        for pos in local_positions:
            if not pos.closed and pos.symbol in stale:
                try:
                    self._portfolio.close_position(pos.instance_id)
                    action_count += 1
                    self._metrics["positions_closed"] += 1
                    details.append(
                        f"Closed stale position {pos.symbol} (not on exchange)"
                    )
                except Exception as exc:
                    details.append(f"Failed to close position {pos.symbol}: {exc}")

        action = "restored" if action_count > 0 else "skipped"
        result = ReconciliationResult(
            component="portfolio",
            action=action,
            count=action_count,
            details=details,
        )
        logger.info(
            "Portfolio reconciliation complete",
            extra={
                "instance_id": instance_id,
                "action": action,
                "count": action_count,
            },
        )
        return result

    def get_portfolio_manager(self) -> PortfolioManager:
        return self._portfolio

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
