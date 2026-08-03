"""
Trading instance repository — async CRUD for trading_instances table.
"""

import uuid

from core.domain_types import TradingInstanceStatus
from models.trading_instance import TradingInstance
from sqlalchemy import select

from repositories.base import IRepository


class TradingInstanceRepository(IRepository[TradingInstance]):
    model = TradingInstance

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[TradingInstance]:
        result = await self._session.execute(
            select(TradingInstance).where(TradingInstance.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self, status: TradingInstanceStatus
    ) -> list[TradingInstance]:
        result = await self._session.execute(
            select(TradingInstance).where(TradingInstance.status == status)
        )
        return list(result.scalars().all())

    async def get_by_worker_id(self, worker_id: str) -> list[TradingInstance]:
        result = await self._session.execute(
            select(TradingInstance).where(TradingInstance.worker_id == worker_id)
        )
        return list(result.scalars().all())

    async def get_active_by_symbol_and_account(
        self, symbol: str, exchange_account_id: uuid.UUID
    ) -> list[TradingInstance]:
        """Return instances for this symbol + account that are actively running or paused."""
        active = {
            TradingInstanceStatus.RUNNING,
            TradingInstanceStatus.PAUSED,
            TradingInstanceStatus.RECOVERING,
            TradingInstanceStatus.STOPPING,
        }
        result = await self._session.execute(
            select(TradingInstance).where(
                TradingInstance.symbol == symbol.upper(),
                TradingInstance.exchange_account_id == exchange_account_id,
                TradingInstance.status.in_(active),
                TradingInstance.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
