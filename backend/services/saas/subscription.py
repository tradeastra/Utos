"""
SubscriptionService — manage subscription plans and lifecycle.

Plans: Free, Starter, Pro, Enterprise.
Uses SubscriptionRepository for database access (mockable for tests).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from core.exceptions import ValidationError
from core.logging import get_logger

logger = get_logger(__name__)

PLAN_HIERARCHY: list[str] = ["free", "starter", "pro", "enterprise"]
PLAN_PRICES: dict[str, float] = {
    "free": 0.0,
    "starter": 29.0,
    "pro": 99.0,
    "enterprise": 499.0,
}


@dataclass
class SubscriptionInfo:
    id: str
    user_id: str
    tier: str
    start_date: datetime
    end_date: datetime
    is_active: bool
    auto_renew: bool = False


class SubscriptionService:
    """Manage subscription plans and lifecycle."""

    def __init__(self, subscription_repo: Any | None = None) -> None:
        self._repo = subscription_repo
        self._subscriptions: dict[str, SubscriptionInfo] = {}
        self._metrics: dict[str, int] = {
            "created": 0,
            "upgrades": 0,
            "downgrades": 0,
            "cancellations": 0,
            "renewals": 0,
        }

    async def create_subscription(
        self,
        user_id: str,
        tier: str,
        duration_days: int = 30,
        auto_renew: bool = False,
    ) -> SubscriptionInfo:
        tier = tier.lower()
        if tier not in PLAN_HIERARCHY:
            raise ValidationError(f"Invalid tier: {tier}. Must be one of {PLAN_HIERARCHY}")

        now = datetime.now(timezone.utc)
        sub = SubscriptionInfo(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=tier,
            start_date=now,
            end_date=now + timedelta(days=duration_days),
            is_active=True,
            auto_renew=auto_renew,
        )
        self._subscriptions[user_id] = sub
        self._metrics["created"] += 1
        logger.info("Subscription created", extra={"user_id": user_id, "tier": tier})
        return sub

    async def upgrade(self, user_id: str, new_tier: str) -> SubscriptionInfo:
        new_tier = new_tier.lower()
        if new_tier not in PLAN_HIERARCHY:
            raise ValidationError(f"Invalid tier: {new_tier}")

        current = self._subscriptions.get(user_id)
        if current is None:
            raise ValidationError("No existing subscription")

        current_idx = PLAN_HIERARCHY.index(current.tier)
        new_idx = PLAN_HIERARCHY.index(new_tier)
        if new_idx <= current_idx:
            raise ValidationError(f"Upgrade requires higher tier than {current.tier}")

        current.tier = new_tier
        self._metrics["upgrades"] += 1
        logger.info("Subscription upgraded", extra={"user_id": user_id, "new_tier": new_tier})
        return current

    async def downgrade(self, user_id: str, new_tier: str) -> SubscriptionInfo:
        new_tier = new_tier.lower()
        if new_tier not in PLAN_HIERARCHY:
            raise ValidationError(f"Invalid tier: {new_tier}")

        current = self._subscriptions.get(user_id)
        if current is None:
            raise ValidationError("No existing subscription")

        current_idx = PLAN_HIERARCHY.index(current.tier)
        new_idx = PLAN_HIERARCHY.index(new_tier)
        if new_idx >= current_idx:
            raise ValidationError(f"Downgrade requires lower tier than {current.tier}")

        current.tier = new_tier
        self._metrics["downgrades"] += 1
        logger.info("Subscription downgraded", extra={"user_id": user_id, "new_tier": new_tier})
        return current

    async def cancel(self, user_id: str) -> bool:
        sub = self._subscriptions.get(user_id)
        if sub is None:
            return False
        sub.is_active = False
        sub.auto_renew = False
        self._metrics["cancellations"] += 1
        logger.info("Subscription cancelled", extra={"user_id": user_id})
        return True

    async def get_subscription(self, user_id: str) -> SubscriptionInfo | None:
        return self._subscriptions.get(user_id)

    async def check_active(self, user_id: str) -> bool:
        sub = self._subscriptions.get(user_id)
        if sub is None or not sub.is_active:
            return False
        if datetime.now(timezone.utc) > sub.end_date:
            return False
        return True

    async def renew(self, user_id: str, duration_days: int = 30) -> SubscriptionInfo:
        sub = self._subscriptions.get(user_id)
        if sub is None:
            raise ValidationError("No existing subscription")

        now = datetime.now(timezone.utc)
        base = max(sub.end_date, now)
        sub.end_date = base + timedelta(days=duration_days)
        sub.is_active = True
        self._metrics["renewals"] += 1
        logger.info("Subscription renewed", extra={"user_id": user_id})
        return sub

    def get_plan_price(self, tier: str) -> float:
        return PLAN_PRICES.get(tier.lower(), 0.0)

    def get_all_plans(self) -> list[dict[str, Any]]:
        return [
            {"tier": t, "price": PLAN_PRICES[t]}
            for t in PLAN_HIERARCHY
        ]

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
