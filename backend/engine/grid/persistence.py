"""
GridPersistence — save and load grid state to/from database.

Uses TradingInstance.memory_snapshot (JSON column) for state persistence.
This module is optional — the GridEngine works without it (in-memory only).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from core.domain_types import GridLevel, GridLevelStatus, GridState


class GridPersistence:
    """Serialize/deserialize GridState to/from a JSON-compatible dict."""

    @staticmethod
    def serialize(state: GridState) -> dict[str, Any]:
        """Convert GridState to a JSON-serializable dict."""
        return {
            "instance_id": state.instance_id,
            "status": state.status,
            "upper_price": str(state.upper_price),
            "lower_price": str(state.lower_price),
            "grid_count": state.grid_count,
            "grid_spacing": str(state.grid_spacing),
            "investment_per_grid": str(state.investment_per_grid),
            "total_cycles": state.total_cycles,
            "total_profit": str(state.total_profit),
            "symbol": state.symbol,
            "current_price": str(state.current_price) if state.current_price else None,
            "exchange_account_id": (
                str(state.exchange_account_id) if state.exchange_account_id else None
            ),
            "levels": [
                {
                    "level": lv.level,
                    "buy_price": str(lv.buy_price),
                    "sell_price": str(lv.sell_price),
                    "quantity": str(lv.quantity),
                    "buy_order_id": lv.buy_order_id,
                    "sell_order_id": lv.sell_order_id,
                    "status": (
                        lv.status.value
                        if isinstance(lv.status, GridLevelStatus)
                        else str(lv.status)
                    ),
                }
                for lv in state.levels
            ],
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> GridState:
        """Convert a serialized dict back to GridState."""
        levels: list[GridLevel] = []
        for lv_data in data.get("levels", []):
            status_str = lv_data["status"]
            try:
                status = GridLevelStatus(status_str)
            except ValueError:
                status = GridLevelStatus.WAITING
            levels.append(
                GridLevel(
                    level=lv_data["level"],
                    buy_price=Decimal(lv_data["buy_price"]),
                    sell_price=Decimal(lv_data["sell_price"]),
                    quantity=Decimal(lv_data["quantity"]),
                    buy_order_id=lv_data.get("buy_order_id"),
                    sell_order_id=lv_data.get("sell_order_id"),
                    status=status,
                )
            )

        return GridState(
            instance_id=data["instance_id"],
            status=data["status"],
            upper_price=Decimal(data["upper_price"]),
            lower_price=Decimal(data["lower_price"]),
            grid_count=data["grid_count"],
            grid_spacing=Decimal(data["grid_spacing"]),
            investment_per_grid=Decimal(data["investment_per_grid"]),
            levels=levels,
            total_cycles=data.get("total_cycles", 0),
            total_profit=Decimal(data.get("total_profit", "0")),
            symbol=data.get("symbol", ""),
            current_price=(
                Decimal(data["current_price"]) if data.get("current_price") else None
            ),
            exchange_account_id=data.get("exchange_account_id"),
        )

    @staticmethod
    def to_json_string(state: GridState) -> str:
        return json.dumps(GridPersistence.serialize(state))

    @staticmethod
    def from_json_string(json_str: str) -> GridState:
        return GridPersistence.deserialize(json.loads(json_str))
