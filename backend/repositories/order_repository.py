"""
Order repository — async CRUD for orders table.
"""

import uuid

from core.domain_types import OrderStatus
from models.order import Order
from sqlalchemy import select

from repositories.base import IRepository


class OrderRepository(IRepository[Order]):
    model = Order

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[Order]:
        result = await self._session.execute(
            select(Order).where(Order.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_trading_instance(self, instance_id: uuid.UUID) -> list[Order]:
        result = await self._session.execute(
            select(Order).where(Order.trading_instance_id == instance_id)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: OrderStatus) -> list[Order]:
        result = await self._session.execute(
            select(Order).where(Order.status == status)
        )
        return list(result.scalars().all())

    async def get_by_exchange_order_id(self, exchange_order_id: str) -> Order | None:
        result = await self._session.execute(
            select(Order).where(Order.exchange_order_id == exchange_order_id)
        )
        return result.scalar_one_or_none()
