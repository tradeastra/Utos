"""SaaS services package: auth, rbac, subscription, license, billing, affiliate."""

from services.saas.affiliate import AffiliateService, AffiliateRecord, AffiliateStats, Commission
from services.saas.auth import AuthService, TokenPair, MFAState
from services.saas.billing import (
    BillingProvider,
    BillingService,
    Invoice,
    ManualProvider,
    MidtransProvider,
    PaymentResult,
    StripeProvider,
    XenditProvider,
)
from services.saas.license import LicenseManager, PlanLimits
from services.saas.rbac import RBACService, Role
from services.saas.subscription import SubscriptionService, SubscriptionInfo

__all__ = [
    "AuthService",
    "TokenPair",
    "MFAState",
    "RBACService",
    "Role",
    "SubscriptionService",
    "SubscriptionInfo",
    "LicenseManager",
    "PlanLimits",
    "BillingService",
    "BillingProvider",
    "Invoice",
    "PaymentResult",
    "ManualProvider",
    "StripeProvider",
    "MidtransProvider",
    "XenditProvider",
    "AffiliateService",
    "AffiliateRecord",
    "AffiliateStats",
    "Commission",
]
