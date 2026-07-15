"""Unit tests for AffiliateService."""

import pytest
from decimal import Decimal

from core.exceptions import ValidationError
from services.saas.affiliate import AffiliateService


class TestRegister:

    @pytest.mark.asyncio
    async def test_register_affiliate(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", commission_rate=10.0)
        assert affiliate.user_id == "user-1"
        assert affiliate.commission_rate == 10.0
        assert len(affiliate.referral_code) > 0
        assert affiliate.is_active is True
        assert svc.get_metrics()["affiliates_registered"] == 1

    @pytest.mark.asyncio
    async def test_register_duplicate(self) -> None:
        svc = AffiliateService()
        await svc.register_affiliate("user-1", 10.0)
        with pytest.raises(ValidationError):
            await svc.register_affiliate("user-1", 10.0)

    @pytest.mark.asyncio
    async def test_register_invalid_rate(self) -> None:
        svc = AffiliateService()
        with pytest.raises(ValidationError):
            await svc.register_affiliate("user-1", -5.0)
        with pytest.raises(ValidationError):
            await svc.register_affiliate("user-1", 150.0)


class TestReferralLink:

    @pytest.mark.asyncio
    async def test_generate_link(self) -> None:
        svc = AffiliateService()
        await svc.register_affiliate("user-1", 10.0)
        link = await svc.generate_referral_link("user-1")
        assert "ref=" in link

    @pytest.mark.asyncio
    async def test_generate_link_not_affiliate(self) -> None:
        svc = AffiliateService()
        with pytest.raises(ValidationError):
            await svc.generate_referral_link("user-1")


class TestTrackReferral:

    @pytest.mark.asyncio
    async def test_track_referral(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", 10.0)
        result = await svc.track_referral(affiliate.referral_code, "user-2")
        assert result is True
        assert svc.get_metrics()["referrals_tracked"] == 1

    @pytest.mark.asyncio
    async def test_track_invalid_code(self) -> None:
        svc = AffiliateService()
        result = await svc.track_referral("INVALID", "user-2")
        assert result is False

    @pytest.mark.asyncio
    async def test_track_duplicate(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", 10.0)
        await svc.track_referral(affiliate.referral_code, "user-2")
        result = await svc.track_referral(affiliate.referral_code, "user-2")
        assert result is False

    @pytest.mark.asyncio
    async def test_track_increments_referral_count(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", 10.0)
        await svc.track_referral(affiliate.referral_code, "user-2")
        await svc.track_referral(affiliate.referral_code, "user-3")
        updated = svc.get_affiliate("user-1")
        assert updated.total_referrals == 2
        assert updated.active_referrals == 2


class TestCommission:

    @pytest.mark.asyncio
    async def test_calculate_commission(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", 10.0)
        commission = await svc.calculate_commission(affiliate.id, Decimal("100.00"))
        assert commission == Decimal("10.00000000")

    @pytest.mark.asyncio
    async def test_record_commission(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", 10.0)
        commission = await svc.record_commission(affiliate.id, Decimal("100.00"), "subscription")
        assert commission.amount > 0
        assert commission.source == "subscription"
        assert svc.get_metrics()["commissions_recorded"] == 1

    @pytest.mark.asyncio
    async def test_commission_updates_earnings(self) -> None:
        svc = AffiliateService()
        affiliate = await svc.register_affiliate("user-1", 10.0)
        await svc.record_commission(affiliate.id, Decimal("100.00"))
        await svc.record_commission(affiliate.id, Decimal("200.00"))
        updated = svc.get_affiliate("user-1")
        assert updated.total_earnings == Decimal("30.00000000")


class TestStatsAndDownline:

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        svc = AffiliateService()
        await svc.register_affiliate("user-1", 15.0)
        affiliate = svc.get_affiliate("user-1")
        await svc.track_referral(affiliate.referral_code, "user-2")
        await svc.record_commission(affiliate.id, Decimal("100.00"))
        stats = await svc.get_affiliate_stats("user-1")
        assert stats.total_referrals == 1
        assert stats.commission_rate == 15.0
        assert stats.total_earnings > 0

    @pytest.mark.asyncio
    async def test_get_stats_not_affiliate(self) -> None:
        svc = AffiliateService()
        stats = await svc.get_affiliate_stats("user-1")
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_downline(self) -> None:
        svc = AffiliateService()
        await svc.register_affiliate("user-1", 10.0)
        affiliate = svc.get_affiliate("user-1")
        await svc.track_referral(affiliate.referral_code, "user-2")
        await svc.track_referral(affiliate.referral_code, "user-3")
        downline = await svc.get_downline("user-1")
        assert len(downline) == 2
        assert "user-2" in downline
        assert "user-3" in downline

    @pytest.mark.asyncio
    async def test_deactivate(self) -> None:
        svc = AffiliateService()
        await svc.register_affiliate("user-1", 10.0)
        assert await svc.deactivate_affiliate("user-1") is True
        assert svc.get_affiliate("user-1").is_active is False
