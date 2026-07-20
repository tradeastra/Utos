"""
LicenseManager — enforce plan limits and feature flags.

Does NOT call engines — only checks limits based on subscription tier.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from core.exceptions import AuthorizationError
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PlanLimits:
    tier: str
    max_instances: int
    max_exchange_accounts: int
    max_symbols: int
    max_workers: int
    feature_flags: list[str] = field(default_factory=list)


_DEFAULT_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        tier="free",
        max_instances=1,
        max_exchange_accounts=1,
        max_symbols=2,
        max_workers=1,
        feature_flags=["basic_grid"],
    ),
    "starter": PlanLimits(
        tier="starter",
        max_instances=3,
        max_exchange_accounts=2,
        max_symbols=10,
        max_workers=3,
        feature_flags=["basic_grid", "profit_lock", "trailing_profit", "notifications"],
    ),
    "pro": PlanLimits(
        tier="pro",
        max_instances=10,
        max_exchange_accounts=5,
        max_symbols=50,
        max_workers=10,
        feature_flags=[
            "basic_grid",
            "profit_lock",
            "trailing_profit",
            "notifications",
            "automation",
            "advanced_risk",
            "priority_support",
        ],
    ),
    "enterprise": PlanLimits(
        tier="enterprise",
        max_instances=100,
        max_exchange_accounts=20,
        max_symbols=500,
        max_workers=100,
        feature_flags=[
            "basic_grid",
            "profit_lock",
            "trailing_profit",
            "notifications",
            "automation",
            "advanced_risk",
            "priority_support",
            "custom_strategies",
            "dedicated_support",
            "white_label",
        ],
    ),
}

ADDON_PRICES: dict[str, float] = {
    "trailing_profit": 19.0,
}

ADDON_DESCRIPTIONS: dict[str, str] = {
    "trailing_profit": "Trailing Profit — automatically trail price upward and lock in profit on every buy fill.",
}


class LicenseManager:
    """Enforce plan limits and feature flags per subscription tier."""

    def __init__(
        self,
        tier_resolver: Callable[[str], str] | None = None,
        addon_resolver: Callable[[str], set[str]] | None = None,
    ) -> None:
        self._limits: dict[str, PlanLimits] = dict(_DEFAULT_LIMITS)
        self._tier_resolver = tier_resolver or (lambda user_id: "free")
        self._addon_resolver = addon_resolver or (lambda user_id: set())
        self._metrics: dict[str, int] = {
            "checks_instance": 0,
            "checks_exchange": 0,
            "checks_symbol": 0,
            "checks_worker": 0,
            "checks_feature": 0,
            "denied": 0,
        }

    def set_plan_limits(self, tier: str, limits: PlanLimits) -> None:
        self._limits[tier.lower()] = limits
        logger.info("Plan limits set", extra={"tier": tier})

    def get_plan_limits(self, tier: str) -> PlanLimits:
        return self._limits.get(tier.lower(), self._limits["free"])

    def set_tier_resolver(self, resolver: Callable[[str], str]) -> None:
        self._tier_resolver = resolver

    def check_instance_limit(self, user_id: str, current_count: int) -> bool:
        self._metrics["checks_instance"] += 1
        tier = self._tier_resolver(user_id)
        limits = self.get_plan_limits(tier)
        if current_count >= limits.max_instances:
            self._metrics["denied"] += 1
            logger.warning(
                "Instance limit exceeded",
                extra={
                    "user_id": user_id,
                    "tier": tier,
                    "current": current_count,
                    "max": limits.max_instances,
                },
            )
            return False
        return True

    def check_exchange_account_limit(self, user_id: str, current_count: int) -> bool:
        self._metrics["checks_exchange"] += 1
        tier = self._tier_resolver(user_id)
        limits = self.get_plan_limits(tier)
        if current_count >= limits.max_exchange_accounts:
            self._metrics["denied"] += 1
            return False
        return True

    def check_symbol_limit(self, user_id: str, current_count: int) -> bool:
        self._metrics["checks_symbol"] += 1
        tier = self._tier_resolver(user_id)
        limits = self.get_plan_limits(tier)
        if current_count >= limits.max_symbols:
            self._metrics["denied"] += 1
            return False
        return True

    def check_worker_limit(self, user_id: str, current_count: int) -> bool:
        self._metrics["checks_worker"] += 1
        tier = self._tier_resolver(user_id)
        limits = self.get_plan_limits(tier)
        if current_count >= limits.max_workers:
            self._metrics["denied"] += 1
            return False
        return True

    def has_feature(self, user_id: str, feature_flag: str) -> bool:
        self._metrics["checks_feature"] += 1
        tier = self._tier_resolver(user_id)
        limits = self.get_plan_limits(tier)
        if feature_flag in limits.feature_flags:
            return True
        addons = self._addon_resolver(user_id)
        return feature_flag in addons

    def has_addon(self, user_id: str, addon_key: str) -> bool:
        addons = self._addon_resolver(user_id)
        return addon_key in addons

    def enforce_instance_limit(self, user_id: str, current_count: int) -> None:
        if not self.check_instance_limit(user_id, current_count):
            raise AuthorizationError(
                f"Instance limit reached for tier {self._tier_resolver(user_id)}"
            )

    def enforce_feature(self, user_id: str, feature_flag: str) -> None:
        if not self.has_feature(user_id, feature_flag):
            raise AuthorizationError(
                f"Feature '{feature_flag}' not available for your plan"
            )

    def get_all_plans(self) -> list[PlanLimits]:
        return [self._limits[t] for t in ["free", "starter", "pro", "enterprise"]]

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
