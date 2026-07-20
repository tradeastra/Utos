"""
Integration tests for Sprint 14: SaaS Platform.

Tests full flow: register → login → subscribe → license check → billing → affiliate.
"""

from decimal import Decimal

import pytest
from services.saas import (
    AffiliateService,
    AuthService,
    BillingService,
    LicenseManager,
    RBACService,
    SubscriptionService,
)


class TestFullSaaSFlow:

    @pytest.mark.asyncio
    async def test_register_to_subscribe(self) -> None:
        auth = AuthService()
        rbac = RBACService()
        sub_svc = SubscriptionService()

        user = await auth.register("trader@example.com", "SecurePass1!", "Trader")
        user_id = user["id"]

        rbac.assign_role(user_id, "trader")
        assert rbac.has_permission(user_id, "trade:create") is True

        sub = await sub_svc.create_subscription(user_id, "pro", duration_days=30)
        assert sub.tier == "pro"
        assert await sub_svc.check_active(user_id) is True

    @pytest.mark.asyncio
    async def test_subscribe_to_license(self) -> None:
        sub_svc = SubscriptionService()
        license_mgr = LicenseManager()

        user_id = "user-1"
        await sub_svc.create_subscription(user_id, "pro")
        sub = await sub_svc.get_subscription(user_id)

        license_mgr.set_tier_resolver(
            lambda uid: sub.tier if uid == user_id else "free"
        )

        assert license_mgr.check_instance_limit(user_id, 5) is True
        assert license_mgr.check_instance_limit(user_id, 10) is False
        assert license_mgr.has_feature(user_id, "automation") is True
        assert license_mgr.has_feature(user_id, "white_label") is False

    @pytest.mark.asyncio
    async def test_subscribe_to_billing(self) -> None:
        sub_svc = SubscriptionService()
        billing = BillingService()

        user_id = "user-1"
        await sub_svc.create_subscription(user_id, "pro")
        price = sub_svc.get_plan_price("pro")

        invoice = await billing.create_invoice(
            user_id, Decimal(str(price)), "USD", "pro"
        )
        result = await billing.process_payment(invoice.id, "manual")
        assert result.status == "success"

        paid = await billing.get_invoice(invoice.id)
        assert paid.status == "paid"

    @pytest.mark.asyncio
    async def test_affiliate_referral_flow(self) -> None:
        auth = AuthService()
        affiliate_svc = AffiliateService()
        sub_svc = SubscriptionService()
        billing = BillingService()

        referrer = await auth.register(
            "affiliate@example.com", "SecurePass1!", "Affiliate"
        )
        referrer_id = referrer["id"]

        await affiliate_svc.register_affiliate(referrer_id, commission_rate=10.0)
        affiliate = affiliate_svc.get_affiliate(referrer_id)

        referred = await auth.register(
            "referred@example.com", "SecurePass1!", "Referred"
        )
        referred_id = referred["id"]

        await affiliate_svc.track_referral(affiliate.referral_code, referred_id)

        await sub_svc.create_subscription(referred_id, "pro")
        price = sub_svc.get_plan_price("pro")
        invoice = await billing.create_invoice(
            referred_id, Decimal(str(price)), "USD", "pro"
        )
        await billing.process_payment(invoice.id, "manual")

        commission = await affiliate_svc.record_commission(
            affiliate.id, Decimal(str(price))
        )
        assert commission.amount > 0

        stats = await affiliate_svc.get_affiliate_stats(referrer_id)
        assert stats.total_referrals == 1
        assert stats.total_earnings > 0


class TestLicenseEnforcement:

    def test_free_tier_cannot_use_automation(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        assert lm.has_feature("user-1", "automation") is False

    def test_pro_tier_can_use_automation(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "pro")
        assert lm.has_feature("user-1", "automation") is True

    def test_enterprise_unlimited_instances(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "enterprise")
        assert lm.check_instance_limit("user-1", 99) is True
        assert lm.check_instance_limit("user-1", 100) is False


class TestRBACWithSubscription:

    @pytest.mark.asyncio
    async def test_admin_has_billing_access(self) -> None:
        rbac = RBACService()
        rbac.assign_role("admin-1", "admin")
        assert rbac.has_permission("admin-1", "billing:read") is True
        assert rbac.has_permission("admin-1", "billing:manage") is False

    @pytest.mark.asyncio
    async def test_super_admin_has_all(self) -> None:
        rbac = RBACService()
        rbac.assign_role("admin-1", "super_admin")
        for perm in [
            "trade:create",
            "user:manage",
            "billing:manage",
            "system:manage",
            "affiliate:manage",
        ]:
            assert rbac.has_permission("admin-1", perm) is True
