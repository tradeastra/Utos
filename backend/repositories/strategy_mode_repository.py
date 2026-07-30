"""StrategyMode repository — CRUD for strategy mode definitions."""

from models.strategy_mode import StrategyMode
from repositories.base import IRepository
from sqlalchemy import select


class StrategyModeRepository(IRepository[StrategyMode]):
    model = StrategyMode

    async def get_all_ordered(self) -> list[StrategyMode]:
        """Return all strategy modes ordered by ``sort_order`` then ``mode``."""
        result = await self._session.execute(
            select(StrategyMode).order_by(StrategyMode.sort_order, StrategyMode.mode)
        )
        return list(result.scalars().all())

    async def get_all_active_ordered(self) -> list[StrategyMode]:
        """Return active strategy modes ordered by ``sort_order`` then ``mode``."""
        result = await self._session.execute(
            select(StrategyMode)
            .where(StrategyMode.is_active.is_(True))
            .order_by(StrategyMode.sort_order, StrategyMode.mode)
        )
        return list(result.scalars().all())

    async def get_by_mode(self, mode: str) -> StrategyMode | None:
        """Look up a strategy mode by its (case-insensitive) code, e.g. 'A'."""
        result = await self._session.execute(
            select(StrategyMode).where(StrategyMode.mode == mode.upper())
        )
        return result.scalar_one_or_none()
