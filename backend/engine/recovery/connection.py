"""
Layer 1: ConnectionRecovery — handles all connection-level recovery.

Manages Redis, PostgreSQL, Exchange, and WebSocket reconnection.
Queues orders during disconnect and replays them on reconnect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueuedOrder:
    """An order queued during exchange disconnect."""

    instance_id: str
    account_id: str
    exchange: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionRecovery:
    """Layer 1: Handles all connection-level recovery.

    Does NOT know about Grid, Profit Lock, or Portfolio internals.
    Only manages connection state and order queueing.
    """

    def __init__(
        self,
        redis_health_check: Callable[[], bool] | None = None,
        postgres_health_check: Callable[[], bool] | None = None,
        resubscribe_fn: Callable[[str, list[str]], bool] | None = None,
        resync_prices_fn: Callable[[list[str]], dict[str, Decimal]] | None = None,
        place_order_fn: Callable[[QueuedOrder], Any] | None = None,
    ) -> None:
        self._redis_health = redis_health_check
        self._postgres_health = postgres_health_check
        self._resubscribe_fn = resubscribe_fn
        self._resync_prices_fn = resync_prices_fn
        self._place_order_fn = place_order_fn

        self._redis_connected: bool = True
        self._postgres_connected: bool = True
        self._exchange_connected: dict[str, bool] = {}  # exchange -> bool
        self._subscribed_symbols: dict[str, list[str]] = {}  # account_id -> symbols
        self._order_queue: list[QueuedOrder] = []
        self._reconnect_attempts: dict[str, int] = {}  # exchange -> count
        self._max_reconnect_attempts = 5
        self._metrics: dict[str, int] = {
            "redis_recoveries": 0,
            "postgres_recoveries": 0,
            "exchange_reconnects": 0,
            "orders_queued": 0,
            "orders_replayed": 0,
            "orders_replayed_failed": 0,
        }

    def register_subscriptions(self, account_id: str, symbols: list[str]) -> None:
        self._subscribed_symbols[account_id] = list(symbols)

    async def recover_redis(self) -> bool:
        """Attempt to recover Redis connection."""
        logger.info("Starting Redis recovery")
        self._metrics["redis_recoveries"] += 1

        if self._redis_health is not None:
            try:
                self._redis_connected = self._redis_health()
            except Exception as exc:
                logger.error(f"Redis health check failed: {exc}")
                self._redis_connected = False
        else:
            self._redis_connected = True

        if self._redis_connected:
            logger.info("Redis recovery successful")
        else:
            logger.error("Redis recovery failed")
        return self._redis_connected

    async def recover_postgres(self) -> bool:
        """Attempt to recover PostgreSQL connection."""
        logger.info("Starting PostgreSQL recovery")
        self._metrics["postgres_recoveries"] += 1

        if self._postgres_health is not None:
            try:
                self._postgres_connected = self._postgres_health()
            except Exception as exc:
                logger.error(f"PostgreSQL health check failed: {exc}")
                self._postgres_connected = False
        else:
            self._postgres_connected = True

        if self._postgres_connected:
            logger.info("PostgreSQL recovery successful")
        else:
            logger.error("PostgreSQL recovery failed")
        return self._postgres_connected

    async def on_exchange_disconnect(self, exchange: str, account_id: str) -> None:
        """Called when exchange connection is lost."""
        logger.warning(
            "Exchange disconnected",
            extra={"exchange": exchange, "account_id": account_id},
        )
        self._exchange_connected[exchange] = False
        self._reconnect_attempts[exchange] = 0

    async def on_exchange_reconnect(self, exchange: str, account_id: str) -> bool:
        """Called when exchange connection is restored."""
        logger.info(
            "Exchange reconnecting",
            extra={"exchange": exchange, "account_id": account_id},
        )
        self._metrics["exchange_reconnects"] += 1
        self._exchange_connected[exchange] = True
        self._reconnect_attempts[exchange] = 0

        symbols = self._subscribed_symbols.get(account_id, [])
        if symbols:
            await self.resubscribe_all(account_id, symbols)
            await self.resync_prices(symbols)

        await self.replay_queued_orders()
        return True

    async def resubscribe_all(self, account_id: str, symbols: list[str]) -> bool:
        """Re-subscribe to all symbols after reconnect."""
        logger.info(
            "Re-subscribing to symbols",
            extra={"account_id": account_id, "count": len(symbols)},
        )
        if self._resubscribe_fn is not None:
            try:
                return self._resubscribe_fn(account_id, symbols)
            except Exception as exc:
                logger.error(f"Re-subscribe failed: {exc}")
                return False
        self._subscribed_symbols[account_id] = list(symbols)
        return True

    async def resync_prices(self, symbols: list[str]) -> dict[str, Decimal]:
        """Re-sync prices after reconnect."""
        logger.info("Re-syncing prices", extra={"symbols": symbols})
        if self._resync_prices_fn is not None:
            try:
                return self._resync_prices_fn(symbols)
            except Exception as exc:
                logger.error(f"Price re-sync failed: {exc}")
                return {}
        return {}

    def queue_order(self, order: QueuedOrder) -> None:
        """Queue an order during exchange disconnect."""
        self._order_queue.append(order)
        self._metrics["orders_queued"] += 1
        logger.info(
            "Order queued",
            extra={
                "instance_id": order.instance_id,
                "symbol": order.symbol,
                "queue_size": len(self._order_queue),
            },
        )

    async def replay_queued_orders(self) -> list[Any]:
        """Replay all queued orders after reconnect."""
        if not self._order_queue:
            return []

        results: list[Any] = []
        queue = list(self._order_queue)
        self._order_queue.clear()

        for order in queue:
            try:
                if self._place_order_fn is not None:
                    result = self._place_order_fn(order)
                    results.append(result)
                    self._metrics["orders_replayed"] += 1
                    logger.info(
                        "Queued order replayed",
                        extra={"instance_id": order.instance_id, "symbol": order.symbol},
                    )
                else:
                    logger.warning(
                        "No place_order_fn set, skipping replay",
                        extra={"instance_id": order.instance_id},
                    )
            except Exception as exc:
                self._metrics["orders_replayed_failed"] += 1
                logger.error(
                    f"Failed to replay queued order: {exc}",
                    extra={"instance_id": order.instance_id, "symbol": order.symbol},
                )

        return results

    def is_exchange_connected(self, exchange: str) -> bool:
        return self._exchange_connected.get(exchange, True)

    def is_redis_connected(self) -> bool:
        return self._redis_connected

    def is_postgres_connected(self) -> bool:
        return self._postgres_connected

    def get_queue_size(self) -> int:
        return len(self._order_queue)

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
