# Sprint 14 Release — SaaS Platform

**Version:** v0.14.0
**Date:** 2026-07-15
**Tag:** `v0.14.0`

---

## Summary

Sprint 14 delivers the complete **SaaS Platform** — transforming UTOS from a trading engine into a multi-tenant SaaS product. Six service modules provide authentication, role-based access control, subscription management, license enforcement, billing abstraction, and affiliate/MLM system. Architecture Freeze is fully respected — no engine imports.

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

**SaaS flow:**
```
Register → Login → RBAC check → Subscribe → License enforce → Billing → Affiliate
```

---

## Modules

### Module 1: AuthService (`services.saas.auth`)
- Register, login, refresh token
- Password reset (request + reset)
- Change password
- MFA stub (enable, verify, disable)
- Wraps existing PasswordManager and TokenManager
- Metrics tracking

### Module 2: RBACService (`services.saas.rbac`)
- 4 default roles: user, trader, admin, super_admin
- 13 default permissions (trade:create, trade:read, trade:delete, grid:manage, risk:manage, etc.)
- Custom role definition
- Assign/revoke roles per user
- has_permission() with metrics

### Module 3: SubscriptionService (`services.saas.subscription`)
- 4 tiers: Free ($0), Starter ($29), Pro ($99), Enterprise ($499)
- Create, upgrade, downgrade, cancel, renew
- Plan hierarchy enforcement (can't upgrade to same/lower tier)
- Active status check with expiry
- Plan pricing

### Module 4: LicenseManager (`services.saas.license`)
- Plan limits: max_instances, max_exchange_accounts, max_symbols, max_workers
- Feature flags per tier (basic_grid, profit_lock, notifications, automation, advanced_risk, priority_support, custom_strategies, dedicated_support, white_label)
- Tier resolver callback (injectable for testability)
- enforce_* methods that raise AuthorizationError

### Module 5: BillingService (`services.saas.billing`)
- 4 providers: Manual, Stripe, Midtrans, Xendit
- Abstract BillingProvider interface
- Invoice creation, payment processing, cancellation
- Provider registration (extensible)
- Invoice listing per user

### Module 6: AffiliateService (`services.saas.affiliate`)
- Affiliate registration with commission rate
- Referral code generation and link creation
- Referral tracking (code → referred user)
- Commission calculation (percentage-based)
- Commission recording with earnings tracking
- Downline listing
- Affiliate stats (referrals, earnings, rate)

---

## Test Coverage

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_saas_auth.py` | 12 | Register, login, refresh, password reset, MFA |
| `test_saas_rbac.py` | 13 | Roles, permissions, assign/revoke, multi-role |
| `test_saas_subscription.py` | 14 | Create, upgrade, downgrade, cancel, renew, plans |
| `test_saas_license.py` | 17 | Plan limits, feature flags, enforce, all tiers |
| `test_saas_billing.py` | 14 | Providers, invoices, payments, cancel |
| `test_saas_affiliate.py` | 16 | Register, referrals, commissions, stats, downline |
| `test_saas_integration.py` | 9 | Full SaaS flow, license enforcement, RBAC |
| **Total Sprint 14** | **103** | |

**Full test suite: 937 tests passing** (834 existing + 103 new)

---

## Architecture Freeze Compliance

- ✅ No engine imports in any SaaS module
- ✅ No changes to engine public interfaces
- ✅ SaaS services use repositories (mockable) for database access
- ✅ All services testable without database
- ✅ ADR-011 (Core Compatibility Rule) added

---

## Plan Limits Summary

| Tier | Price | Instances | Exchange Accounts | Symbols | Workers | Feature Flags |
|------|-------|-----------|-------------------|---------|---------|---------------|
| Free | $0 | 1 | 1 | 2 | 1 | basic_grid |
| Starter | $29 | 3 | 2 | 10 | 3 | basic_grid, profit_lock, notifications |
| Pro | $99 | 10 | 5 | 50 | 10 | + automation, advanced_risk, priority_support |
| Enterprise | $499 | 100 | 20 | 500 | 100 | + custom_strategies, dedicated_support, white_label |

---

## RBAC Roles Summary

| Role | Key Permissions |
|------|----------------|
| user | trade:read, account:read |
| trader | + trade:create, trade:delete, grid:manage |
| admin | + risk:manage, account:manage, user:read, billing:read |
| super_admin | + user:manage, billing:manage, system:manage, affiliate:manage |

---

## Files Created

- `docs/sprint/SPRINT_14.md` — Sprint 14 spec
- `backend/services/saas/__init__.py` — package exports
- `backend/services/saas/auth.py` — AuthService
- `backend/services/saas/rbac.py` — RBACService
- `backend/services/saas/subscription.py` — SubscriptionService
- `backend/services/saas/license.py` — LicenseManager
- `backend/services/saas/billing.py` — BillingService + 4 providers
- `backend/services/saas/affiliate.py` — AffiliateService
- `backend/tests/test_unit/test_saas_auth.py` — 12 tests
- `backend/tests/test_unit/test_saas_rbac.py` — 13 tests
- `backend/tests/test_unit/test_saas_subscription.py` — 14 tests
- `backend/tests/test_unit/test_saas_license.py` — 17 tests
- `backend/tests/test_unit/test_saas_billing.py` — 14 tests
- `backend/tests/test_unit/test_saas_affiliate.py` — 16 tests
- `backend/tests/test_unit/test_saas_integration.py` — 9 tests

## Files Modified

- `docs/ARCHITECTURE_DECISIONS.md` — ADR-011: Core Compatibility Rule
- `docs/ROADMAP.md` — Sprint 14 completed, Architecture Freeze, changelog v5.4.0 + v6.0.0

---

## Project Status

| Sprint | Status |
|--------|--------|
| ✅ Sprint 1–4 | Foundation |
| ✅ Sprint 5–10 | Trading Core |
| ✅ Sprint 11 | Recovery & Resilience |
| ✅ Sprint 12 | Worker Scheduler & Event Bus |
| ✅ Sprint 13 | Notification & Automation |
| ✅ Architecture Freeze | Approved |
| ✅ Sprint 14 | SaaS Platform |
| 🚀 Sprint 15 | Frontend Dashboard |
| 📋 Sprint 16 | Production Hardening |
