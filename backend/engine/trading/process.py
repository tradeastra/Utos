"""Runtime trading process object."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.context import ProcessMemory
from core.domain_types import TradingInstanceStatus
from exchanges.adapter import IExchangeAdapter


@dataclass
class TradingProcess:
    """Runtime representation of a trading process backed by a TradingInstance."""

    instance_id: uuid.UUID
    user_id: uuid.UUID
    exchange_account_id: uuid.UUID
    strategy_id: uuid.UUID
    symbol: str
    exchange_name: str
    status: TradingInstanceStatus
    adapter: IExchangeAdapter
    memory: ProcessMemory
    worker_id: str
    lock_value: str
    redis: Any = field(repr=False)
    subscription_id: str | None = None  # MarketHub subscription id (for unsubscribe)

    def set_status(self, status: TradingInstanceStatus) -> None:
        """Update both runtime status and process memory."""
        self.status = status
        self.memory.status = status.value
        self.memory.last_updated = datetime.now(tz=UTC)

    def update_memory(
        self,
        memory: ProcessMemory | None = None,
        **kwargs: Any,
    ) -> None:
        """Replace or patch the in-memory process state."""
        if memory is not None:
            self.memory = memory
        for key, value in kwargs.items():
            if hasattr(self.memory, key):
                setattr(self.memory, key, value)
        self.memory.last_updated = datetime.now(tz=UTC)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot for Redis and DB."""
        return {
            "instance_id": str(self.instance_id),
            "user_id": str(self.user_id),
            "exchange_account_id": str(self.exchange_account_id),
            "strategy_id": str(self.strategy_id),
            "symbol": self.symbol,
            "exchange_name": self.exchange_name,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "lock_value": self.lock_value,
            "memory": self.memory.to_dict(),
        }

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any],
        adapter: IExchangeAdapter,
        redis: Any,
    ) -> TradingProcess:
        """Rebuild a TradingProcess from a snapshot."""
        return cls(
            instance_id=uuid.UUID(snapshot["instance_id"]),
            user_id=uuid.UUID(snapshot["user_id"]),
            exchange_account_id=uuid.UUID(snapshot["exchange_account_id"]),
            strategy_id=uuid.UUID(snapshot["strategy_id"]),
            symbol=snapshot["symbol"],
            exchange_name=snapshot["exchange_name"],
            status=TradingInstanceStatus(snapshot["status"]),
            adapter=adapter,
            memory=ProcessMemory.from_dict(snapshot["memory"]),
            worker_id=snapshot["worker_id"],
            lock_value=snapshot["lock_value"],
            redis=redis,
        )

    def __repr__(self) -> str:
        return f"<TradingProcess id={self.instance_id} status={self.status.value} symbol={self.symbol}>"
