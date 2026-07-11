"""
Position repository — async CRUD for positions table.
"""

import uuid

from sqlalchemy import select

from models.position import Position
from repositories.base import IRepository


class PositionRepository(IRepository[Position]):
    model = Position

    async def get_by_trading_instance(self, instance_id: uuid.UUID) -> list[Position]:
        result = await self._session.execute(
            select(Position).where(Position.trading_instance_id == instance_id)
        )
        return list(result.scalars().all())
