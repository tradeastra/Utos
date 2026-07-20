"""
Subscription manager for the Market Data Hub.

Key responsibility: deduplicate WebSocket subscriptions. If ten consumers
subscribe to BTCUSDT ticker on Binance, only ONE actual WebSocket subscription
is opened. Unsubscribing a consumer only closes the WebSocket when the last
consumer leaves.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any


class SubscriptionManager:
    """Manages consumer subscriptions and maps them to logical streams."""

    def __init__(
        self,
        subscribe_fn: Callable[[str, str, str, Callable[..., Any]], Any],
        unsubscribe_fn: Callable[[str], Any],
    ) -> None:
        """
        Args:
            subscribe_fn: async function(exchange, symbol, channel, callback) -> ws_sub_id
            unsubscribe_fn: async function(ws_sub_id) -> None
        """
        self._subscribe_fn = subscribe_fn
        self._unsubscribe_fn = unsubscribe_fn

        # logical key -> {"ws_sub_id": str, "refcount": int, "callbacks": dict[str, Callable]}
        self._logical: dict[tuple[str, str, str], dict[str, Any]] = {}

        # consumer sub id -> logical key
        self._consumer_map: dict[str, tuple[str, str, str]] = {}

    def _logical_key(
        self, exchange: str, symbol: str, channel: str
    ) -> tuple[str, str, str]:
        return exchange.lower(), symbol.upper(), channel.lower()

    async def subscribe(
        self,
        exchange: str,
        symbol: str,
        channel: str,
        callback: Callable[..., Any],
    ) -> str:
        """Register a consumer subscription. Open a logical stream if needed."""
        logical = self._logical_key(exchange, symbol, channel)
        consumer_id = str(uuid.uuid4())
        self._consumer_map[consumer_id] = logical

        if logical in self._logical:
            self._logical[logical]["refcount"] += 1
            self._logical[logical]["callbacks"][consumer_id] = callback
            return consumer_id

        ws_sub_id = await self._subscribe_fn(exchange, symbol, channel, callback)
        self._logical[logical] = {
            "ws_sub_id": ws_sub_id,
            "refcount": 1,
            "exchange": exchange.lower(),
            "symbol": symbol.upper(),
            "channel": channel.lower(),
            "callbacks": {consumer_id: callback},
        }
        return consumer_id

    async def unsubscribe(self, consumer_id: str) -> None:
        """Remove a consumer subscription; close logical stream if refcount reaches 0."""
        logical = self._consumer_map.pop(consumer_id, None)
        if logical is None:
            return

        entry = self._logical.get(logical)
        if entry is None:
            return

        entry["callbacks"].pop(consumer_id, None)
        entry["refcount"] -= 1
        if entry["refcount"] <= 0:
            ws_sub_id = entry["ws_sub_id"]
            del self._logical[logical]
            await self._unsubscribe_fn(ws_sub_id)

    def active_count(
        self, exchange: str | None = None, symbol: str | None = None
    ) -> int:
        """Return number of active logical streams, optionally filtered."""
        if exchange is None and symbol is None:
            return len(self._logical)
        ex = exchange.lower() if exchange else None
        sym = symbol.upper() if symbol else None
        return sum(
            1
            for (e, s, _c), entry in self._logical.items()
            if (ex is None or e == ex) and (sym is None or s == sym)
        )

    def consumer_count(self) -> int:
        """Return total active consumer subscriptions."""
        return sum(entry["refcount"] for entry in self._logical.values())

    def logical_keys(self) -> list[tuple[str, str, str]]:
        """Return all active logical subscription keys."""
        return sorted(self._logical.keys())

    def is_active(self, exchange: str, symbol: str, channel: str) -> bool:
        return self._logical_key(exchange, symbol, channel) in self._logical

    async def fan_out(
        self, exchange: str, symbol: str, channel: str, data: Any
    ) -> None:
        """Deliver data to all consumer callbacks for a logical stream."""
        logical = self._logical_key(exchange, symbol, channel)
        entry = self._logical.get(logical)
        if entry is None:
            return
        for callback in list(entry["callbacks"].values()):
            try:
                result = callback(data)
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                pass

    def clear(self) -> None:
        """Reset all tracking (used in tests)."""
        self._logical.clear()
        self._consumer_map.clear()
