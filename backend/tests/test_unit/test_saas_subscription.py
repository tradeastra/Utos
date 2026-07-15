"""Unit tests for SubscriptionService."""

import pytest

from core.exceptions import ValidationError
from services.saas.subscription import SubscriptionService


class TestCreate:

    @pytest.mark.asyncio
    async def test_create_subscription(self) -> None:
        svc = SubscriptionService()
        sub = await svc.create_subscription("user-1", "pro", duration_days=30)
        assert sub.user_id == "user-1"
        assert sub.tier == "pro"
        assert sub.is_active is True
        assert svc.get_metrics()["created"] == 1

    @pytest.mark.asyncio
    async def test_create_invalid_tier(self) -> None:
        svc = SubscriptionService()
        with pytest.raises(ValidationError):
            await svc.create_subscription("user-1", "premium")


class TestUpgrade:

    @pytest.mark.asyncio
    async def test_upgrade(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "free")
        sub = await svc.upgrade("user-1", "starter")
        assert sub.tier == "starter"
        assert svc.get_metrics()["upgrades"] == 1

    @pytest.mark.asyncio
    async def test_upgrade_same_tier(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro")
        with pytest.raises(ValidationError):
            await svc.upgrade("user-1", "pro")

    @pytest.mark.asyncio
    async def test_upgrade_lower_tier(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro")
        with pytest.raises(ValidationError):
            await svc.upgrade("user-1", "free")

    @pytest.mark.asyncio
    async def test_upgrade_no_subscription(self) -> None:
        svc = SubscriptionService()
        with pytest.raises(ValidationError):
            await svc.upgrade("user-1", "pro")


class TestDowngrade:

    @pytest.mark.asyncio
    async def test_downgrade(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro")
        sub = await svc.downgrade("user-1", "starter")
        assert sub.tier == "starter"
        assert svc.get_metrics()["downgrades"] == 1

    @pytest.mark.asyncio
    async def test_downgrade_higher_tier(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "free")
        with pytest.raises(ValidationError):
            await svc.downgrade("user-1", "pro")


class TestCancel:

    @pytest.mark.asyncio
    async def test_cancel(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro")
        assert await svc.cancel("user-1") is True
        sub = await svc.get_subscription("user-1")
        assert sub.is_active is False
        assert sub.auto_renew is False

    @pytest.mark.asyncio
    async def test_cancel_no_subscription(self) -> None:
        svc = SubscriptionService()
        assert await svc.cancel("user-1") is False


class TestCheckActive:

    @pytest.mark.asyncio
    async def test_check_active(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro", duration_days=30)
        assert await svc.check_active("user-1") is True

    @pytest.mark.asyncio
    async def test_check_active_no_subscription(self) -> None:
        svc = SubscriptionService()
        assert await svc.check_active("user-1") is False

    @pytest.mark.asyncio
    async def test_check_active_cancelled(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro")
        await svc.cancel("user-1")
        assert await svc.check_active("user-1") is False


class TestRenew:

    @pytest.mark.asyncio
    async def test_renew(self) -> None:
        svc = SubscriptionService()
        await svc.create_subscription("user-1", "pro", duration_days=30)
        sub = await svc.renew("user-1", duration_days=60)
        assert sub.is_active is True
        assert svc.get_metrics()["renewals"] == 1


class TestPlans:

    def test_plan_prices(self) -> None:
        svc = SubscriptionService()
        assert svc.get_plan_price("free") == 0.0
        assert svc.get_plan_price("pro") == 99.0

    def test_all_plans(self) -> None:
        svc = SubscriptionService()
        plans = svc.get_all_plans()
        assert len(plans) == 4
