# Sprint 14: SaaS Platform — Auth, RBAC, Subscription, License, Billing, Affiliate

**Version Target:** v0.14.0
**Status:** In Progress
**Dependencies:** Sprint 01–13, Architecture Freeze

---

## Objective

Build the complete SaaS layer: authentication, role-based access control, subscription plans, license enforcement, billing abstraction, and affiliate/MLM system. This sprint transforms UTOS from a trading engine into a multi-tenant SaaS platform.

---

## 6-Module Architecture

```
services/saas/
    ├── __init__.py          — package exports
    ├── auth.py              — AuthService (login, refresh, MFA stub, sessions)
    ├── rbac.py              — RBACService (roles, permissions, access control)
    ├── subscription.py      — SubscriptionService (plans, upgrade/downgrade)
    ├── license.py           — LicenseManager (limits, feature flags)
    ├── billing.py           — BillingService (provider abstraction)
    └── affiliate.py         — AffiliateService (referrals, commissions)
```

**Existing infrastructure (Sprint 1–2):**
- Models: User, Subscription, Affiliate, Transaction
- Repositories: UserRepository, SubscriptionRepository, AffiliateRepository
- Security: PasswordManager, TokenManager (JWT)
- Auth endpoints: register, login, refresh, logout

---

## Module Breakdown

### Module 1: AuthService (`services.saas.auth`)
**Purpose:** Wrap existing security utilities into a cohesive auth service.

```python
class AuthService:
    async def register(email, password, full_name) -> User
    async def login(email, password) -> TokenPair
    async def refresh_token(refresh_token) -> str
    async def verify_email(token) -> bool
    async def request_password_reset(email) -> str
    async def reset_password(token, new_password) -> bool
    async def change_password(user_id, old_password, new_password) -> bool
    async def enable_mfa(user_id) -> str  # returns secret
    async def verify_mfa(user_id, code) -> bool
    async def disable_mfa(user_id) -> bool
```

### Module 2: RBACService (`services.saas.rbac`)
**Purpose:** Role-based access control with fine-grained permissions.

```python
class RBACService:
    def define_role(role_name, permissions: list[str]) -> None
    def assign_role(user_id, role_name) -> None
    def revoke_role(user_id, role_name) -> None
    def has_permission(user_id, permission) -> bool
    def get_user_permissions(user_id) -> list[str]
    def get_role_permissions(role_name) -> list[str]
```

Default roles: user, trader, admin, super_admin
Default permissions: trade:create, trade:read, trade:delete, grid:manage, risk:manage, user:manage, billing:manage

### Module 3: SubscriptionService (`services.saas.subscription`)
**Purpose:** Manage subscription plans and lifecycle.

```python
class SubscriptionService:
    async def create_subscription(user_id, tier, duration_days) -> Subscription
    async def upgrade(user_id, new_tier) -> Subscription
    async def downgrade(user_id, new_tier) -> Subscription
    async def cancel(user_id) -> bool
    async def get_subscription(user_id) -> Subscription | None
    async def check_active(user_id) -> bool
    async def renew(user_id) -> Subscription
```

Plans: Free, Starter, Pro, Enterprise

### Module 4: LicenseManager (`services.saas.license`)
**Purpose:** Enforce plan limits and feature flags.

```python
class LicenseManager:
    def set_plan_limits(tier, limits: PlanLimits) -> None
    def get_plan_limits(tier) -> PlanLimits
    def check_instance_limit(user_id, current_count) -> bool
    def check_exchange_account_limit(user_id, current_count) -> bool
    def check_symbol_limit(user_id, current_count) -> bool
    def check_worker_limit(user_id, current_count) -> bool
    def has_feature(user_id, feature_flag) -> bool
```

PlanLimits: max_instances, max_exchange_accounts, max_symbols, max_workers, feature_flags

### Module 5: BillingService (`services.saas.billing`)
**Purpose:** Payment provider abstraction.

```python
class BillingService:
    def register_provider(name, provider: BillingProvider) -> None
    async def create_invoice(user_id, amount, currency, plan) -> Invoice
    async def process_payment(invoice_id, provider_name) -> PaymentResult
    async def get_invoice(invoice_id) -> Invoice | None
    async def list_invoices(user_id) -> list[Invoice]
```

BillingProvider (abstract): Manual, Stripe, Midtrans, Xendit

### Module 6: AffiliateService (`services.saas.affiliate`)
**Purpose:** Referral system with commission tracking.

```python
class AffiliateService:
    async def register_affiliate(user_id, commission_rate) -> Affiliate
    async def generate_referral_link(user_id) -> str
    async def track_referral(referral_code, referred_user_id) -> bool
    async def calculate_commission(affiliate_id, amount) -> Decimal
    async def record_commission(affiliate_id, amount, source) -> Commission
    async def get_affiliate_stats(user_id) -> AffiliateStats
    async def get_downline(user_id) -> list[Affiliate]
```

---

## Data Types

```python
@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800

@dataclass
class PlanLimits:
    tier: str
    max_instances: int
    max_exchange_accounts: int
    max_symbols: int
    max_workers: int
    feature_flags: list[str]

@dataclass
class Invoice:
    id: str
    user_id: str
    amount: Decimal
    currency: str
    plan: str
    status: str  # pending | paid | failed | cancelled
    provider: str | None
    created_at: datetime

@dataclass
class PaymentResult:
    invoice_id: str
    status: str  # success | failed
    transaction_id: str | None
    error: str | None

@dataclass
class Commission:
    id: str
    affiliate_id: str
    amount: Decimal
    source: str
    created_at: datetime

@dataclass
class AffiliateStats:
    total_referrals: int
    total_earnings: Decimal
    active_referrals: int
    commission_rate: float

@dataclass
class BillingProvider(ABC):
    @abstractmethod
    async def charge(amount, currency, metadata) -> PaymentResult
```

---

## Key Constraints

- SaaS services do NOT import engine modules (Architecture Freeze)
- SaaS services use repositories for database access
- AuthService wraps existing PasswordManager and TokenManager
- LicenseManager does NOT call engines — it only checks limits
- BillingService does NOT process payments directly — uses providers
- AffiliateService does NOT modify user accounts — only tracks referrals
- All services are testable without a database (mock repositories)

---

## Acceptance Criteria

- [ ] AuthService: register, login, refresh, password reset, MFA stub
- [ ] RBACService: roles, permissions, has_permission
- [ ] SubscriptionService: create, upgrade, downgrade, cancel, renew
- [ ] LicenseManager: plan limits, feature flags, all check_* methods
- [ ] BillingService: 4 providers (Manual, Stripe, Midtrans, Xendit), invoices
- [ ] AffiliateService: register, referral link, track, commission, stats
- [ ] Unit tests for all 6 modules
- [ ] Integration tests for full SaaS flow
- [ ] No regressions in existing 834 tests
