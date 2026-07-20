"""SaaS services package: auth, rbac, subscription, license, billing, affiliate."""

from services.saas.affiliate import (
    AffiliateRecord,
    AffiliateService,
    AffiliateStats,
    Commission,
)
from services.saas.auth import AuthService, MFAState, TokenPair
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
from services.saas.subscription import SubscriptionInfo, SubscriptionService

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
