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
