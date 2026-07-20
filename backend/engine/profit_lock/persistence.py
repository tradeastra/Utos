"""
ProfitPersistence — save and load profit lock state to/from database.

Uses TradingInstance.memory_snapshot (JSON column) for state persistence.
Same pattern as GridPersistence.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any

from engine.profit_lock.state import ProfitLockState, ProfitLockStatus


class ProfitPersistence:
    """Serialize/deserialize ProfitLockState to/from a JSON-compatible dict."""

    @staticmethod
    def serialize(state: ProfitLockState) -> dict[str, Any]:
        """Convert ProfitLockState to a JSON-serializable dict."""
        return {
            "instance_id": state.instance_id,
            "status": state.status,
            "enabled": state.enabled,
            "trigger_percentage": str(state.trigger_percentage),
            "trail_percentage": str(state.trail_percentage),
            "entry_price": str(state.entry_price),
            "quantity": str(state.quantity),
            "side": state.side,
            "highest_price": str(state.highest_price) if state.highest_price else None,
            "lock_price": str(state.lock_price) if state.lock_price else None,
            "is_triggered": state.is_triggered,
            "is_executed": state.is_executed,
            "lock_order_id": state.lock_order_id,
            "exchange_account_id": (
                str(state.exchange_account_id) if state.exchange_account_id else None
            ),
            "symbol": state.symbol,
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> ProfitLockState:
        """Convert a serialized dict back to ProfitLockState."""
        return ProfitLockState(
            instance_id=data["instance_id"],
            status=data.get("status", ProfitLockStatus.DISABLED),
            enabled=data.get("enabled", False),
            trigger_percentage=Decimal(data.get("trigger_percentage", "0")),
            trail_percentage=Decimal(data.get("trail_percentage", "0")),
            entry_price=Decimal(data.get("entry_price", "0")),
            quantity=Decimal(data.get("quantity", "0")),
            side=data.get("side", "long"),
            highest_price=(
                Decimal(data["highest_price"]) if data.get("highest_price") else None
            ),
            lock_price=Decimal(data["lock_price"]) if data.get("lock_price") else None,
            is_triggered=data.get("is_triggered", False),
            is_executed=data.get("is_executed", False),
            lock_order_id=data.get("lock_order_id"),
            exchange_account_id=(
                uuid.UUID(data["exchange_account_id"])
                if data.get("exchange_account_id")
                else None
            ),
            symbol=data.get("symbol", ""),
        )

    @staticmethod
    def to_json_string(state: ProfitLockState) -> str:
        return json.dumps(ProfitPersistence.serialize(state))

    @staticmethod
    def from_json_string(json_str: str) -> ProfitLockState:
        return ProfitPersistence.deserialize(json.loads(json_str))
