"""
AffiliateService — referral system with commission tracking.

Manages affiliate registration, referral links, commission calculation,
and downline tracking. Does NOT modify user accounts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AffiliateRecord:
    id: str
    user_id: str
    commission_rate: float
    total_earnings: Decimal = Decimal("0")
    total_referrals: int = 0
    active_referrals: int = 0
    is_active: bool = True
    referral_code: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Commission:
    id: str
    affiliate_id: str
    amount: Decimal
    source: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AffiliateStats:
    total_referrals: int
    total_earnings: Decimal
    active_referrals: int
    commission_rate: float


class AffiliateService:
    """Affiliate/MLM service — referrals and commission tracking."""

    def __init__(self, affiliate_repo: Any | None = None) -> None:
        self._repo = affiliate_repo
        self._affiliates: dict[str, AffiliateRecord] = {}
        self._commissions: list[Commission] = []
        self._referral_map: dict[str, str] = {}  # referral_code -> affiliate_id
        self._referred_by: dict[str, str] = {}  # referred_user_id -> affiliate_id
        self._metrics: dict[str, int] = {
            "affiliates_registered": 0,
            "referrals_tracked": 0,
            "commissions_recorded": 0,
        }

    async def register_affiliate(
        self,
        user_id: str,
        commission_rate: float = 10.0,
    ) -> AffiliateRecord:
        if commission_rate < 0 or commission_rate > 100:
            raise ValidationError("Commission rate must be between 0 and 100")

        if user_id in self._affiliates:
            raise ValidationError("User is already an affiliate")

        referral_code = self._generate_referral_code(user_id)
        affiliate = AffiliateRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            commission_rate=commission_rate,
            referral_code=referral_code,
        )
        self._affiliates[user_id] = affiliate
        self._referral_map[referral_code] = affiliate.id
        self._metrics["affiliates_registered"] += 1
        logger.info(
            "Affiliate registered",
            extra={"user_id": user_id, "referral_code": referral_code},
        )
        return affiliate

    async def generate_referral_link(
        self, user_id: str, base_url: str = "https://utos.app"
    ) -> str:
        affiliate = self._affiliates.get(user_id)
        if affiliate is None:
            raise ValidationError("User is not an affiliate")
        return f"{base_url}/register?ref={affiliate.referral_code}"

    async def track_referral(self, referral_code: str, referred_user_id: str) -> bool:
        affiliate_id = self._referral_map.get(referral_code)
        if affiliate_id is None:
            return False
        if referred_user_id in self._referred_by:
            return False

        self._referred_by[referred_user_id] = affiliate_id
        affiliate = self._find_affiliate_by_id(affiliate_id)
        if affiliate:
            affiliate.total_referrals += 1
            affiliate.active_referrals += 1

        self._metrics["referrals_tracked"] += 1
        logger.info(
            "Referral tracked",
            extra={
                "referral_code": referral_code,
                "referred_user_id": referred_user_id,
            },
        )
        return True

    async def calculate_commission(self, affiliate_id: str, amount: Decimal) -> Decimal:
        affiliate = self._find_affiliate_by_id(affiliate_id)
        if affiliate is None:
            return Decimal("0")
        return (
            Decimal(str(amount))
            * Decimal(str(affiliate.commission_rate))
            / Decimal("100")
        ).quantize(Decimal("0.00000001"))

    async def record_commission(
        self,
        affiliate_id: str,
        amount: Decimal,
        source: str = "subscription",
    ) -> Commission:
        commission_amount = await self.calculate_commission(affiliate_id, amount)
        commission = Commission(
            id=str(uuid.uuid4()),
            affiliate_id=affiliate_id,
            amount=commission_amount,
            source=source,
        )
        self._commissions.append(commission)

        affiliate = self._find_affiliate_by_id(affiliate_id)
        if affiliate:
            affiliate.total_earnings += commission_amount

        self._metrics["commissions_recorded"] += 1
        logger.info(
            "Commission recorded",
            extra={"affiliate_id": affiliate_id, "amount": str(commission_amount)},
        )
        return commission

    async def get_affiliate_stats(self, user_id: str) -> AffiliateStats | None:
        affiliate = self._affiliates.get(user_id)
        if affiliate is None:
            return None
        return AffiliateStats(
            total_referrals=affiliate.total_referrals,
            total_earnings=affiliate.total_earnings,
            active_referrals=affiliate.active_referrals,
            commission_rate=affiliate.commission_rate,
        )

    async def get_downline(self, user_id: str) -> list[str]:
        affiliate = self._affiliates.get(user_id)
        if affiliate is None:
            return []
        return [
            referred_id
            for referred_id, aff_id in self._referred_by.items()
            if aff_id == affiliate.id
        ]

    async def deactivate_affiliate(self, user_id: str) -> bool:
        affiliate = self._affiliates.get(user_id)
        if affiliate is None:
            return False
        affiliate.is_active = False
        return True

    def get_affiliate(self, user_id: str) -> AffiliateRecord | None:
        return self._affiliates.get(user_id)

    def get_commissions(self, affiliate_id: str) -> list[Commission]:
        return [c for c in self._commissions if c.affiliate_id == affiliate_id]

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    def _find_affiliate_by_id(self, affiliate_id: str) -> AffiliateRecord | None:
        for affiliate in self._affiliates.values():
            if affiliate.id == affiliate_id:
                return affiliate
        return None

    def _generate_referral_code(self, user_id: str) -> str:
        return user_id[:8].upper() + uuid.uuid4().hex[:4].upper()
