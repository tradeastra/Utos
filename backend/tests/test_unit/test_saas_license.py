"""Unit tests for LicenseManager."""

import pytest
from core.exceptions import AuthorizationError
from services.saas.license import LicenseManager, PlanLimits


class TestPlanLimits:

    def test_default_limits(self) -> None:
        lm = LicenseManager()
        free = lm.get_plan_limits("free")
        assert free.max_instances == 1
        assert free.max_exchange_accounts == 1
        pro = lm.get_plan_limits("pro")
        assert pro.max_instances == 10
        enterprise = lm.get_plan_limits("enterprise")
        assert enterprise.max_instances == 100

    def test_custom_limits(self) -> None:
        lm = LicenseManager()
        custom = PlanLimits("custom", 50, 10, 100, 50, ["all"])
        lm.set_plan_limits("custom", custom)
        assert lm.get_plan_limits("custom").max_instances == 50

    def test_unknown_tier_defaults_to_free(self) -> None:
        lm = LicenseManager()
        limits = lm.get_plan_limits("nonexistent")
        assert limits.max_instances == 1


class TestInstanceLimit:

    def test_within_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "pro")
        assert lm.check_instance_limit("user-1", 5) is True

    def test_at_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        assert lm.check_instance_limit("user-1", 1) is False

    def test_over_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        assert lm.check_instance_limit("user-1", 5) is False

    def test_enforce_raises(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        with pytest.raises(AuthorizationError):
            lm.enforce_instance_limit("user-1", 1)


class TestExchangeAccountLimit:

    def test_within_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "starter")
        assert lm.check_exchange_account_limit("user-1", 1) is True

    def test_at_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "starter")
        assert lm.check_exchange_account_limit("user-1", 2) is False


class TestSymbolLimit:

    def test_within_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "pro")
        assert lm.check_symbol_limit("user-1", 40) is True

    def test_at_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "pro")
        assert lm.check_symbol_limit("user-1", 50) is False


class TestWorkerLimit:

    def test_within_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "enterprise")
        assert lm.check_worker_limit("user-1", 50) is True

    def test_at_limit(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        assert lm.check_worker_limit("user-1", 1) is False


class TestFeatureFlags:

    def test_has_feature(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "pro")
        assert lm.has_feature("user-1", "automation") is True

    def test_no_feature(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        assert lm.has_feature("user-1", "automation") is False

    def test_enforce_feature_raises(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "free")
        with pytest.raises(AuthorizationError):
            lm.enforce_feature("user-1", "automation")

    def test_enforce_feature_ok(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "enterprise")
        lm.enforce_feature("user-1", "white_label")

    def test_enterprise_has_all_features(self) -> None:
        lm = LicenseManager(tier_resolver=lambda uid: "enterprise")
        for flag in [
            "basic_grid",
            "profit_lock",
            "notifications",
            "automation",
            "advanced_risk",
            "priority_support",
            "custom_strategies",
            "dedicated_support",
            "white_label",
        ]:
            assert lm.has_feature("user-1", flag) is True


class TestGetAllPlans:

    def test_get_all_plans(self) -> None:
        lm = LicenseManager()
        plans = lm.get_all_plans()
        assert len(plans) == 4
        tiers = [p.tier for p in plans]
        assert "free" in tiers
        assert "enterprise" in tiers
