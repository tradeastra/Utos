# Sprint 15: Frontend Dashboard

**Version Target:** v0.15.0
**Status:** In Progress
**Dependencies:** Sprint 01–14 (all backend)

---

## Objective

Build a complete Next.js dashboard with real-time trading monitoring, SaaS management, and settings. The dashboard connects to the UTOS backend API and WebSocket for live updates.

---

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Styling:** TailwindCSS
- **Components:** shadcn/ui
- **Icons:** Lucide
- **State:** Zustand
- **API:** Native fetch + WebSocket
- **Charts:** Recharts
- **Testing:** Vitest + React Testing Library

---

## Page Structure

```
frontend/app/
    ├── layout.tsx              — root layout
    ├── page.tsx                — redirect to /dashboard
    ├── login/page.tsx          — login page
    ├── register/page.tsx       — register page
    ├── dashboard/
    │   ├── layout.tsx          — dashboard shell (sidebar + header)
    │   ├── page.tsx            — overview (metrics summary)
    │   ├── trading/page.tsx    — live trading instances
    │   ├── grid/page.tsx       — live grid visualization
    │   ├── orders/page.tsx     — live orders feed
    │   ├── portfolio/page.tsx  — PnL, exposure, positions
    │   ├── risk/page.tsx       — risk settings + status
    │   ├── recovery/page.tsx   — recovery status + history
    │   ├── workers/page.tsx    — worker status + health
    │   ├── events/page.tsx     — EventBus live feed
    │   ├── notifications/page.tsx — notification settings + history
    │   ├── subscription/page.tsx — plan + upgrade
    │   ├── billing/page.tsx    — invoices + payment
    │   └── affiliate/page.tsx  — referral links + commissions
    └── settings/
        ├── exchanges/page.tsx  — exchange account management
        └── profile/page.tsx    — user profile + security
```

---

## Key Features

### Live Monitoring
- Real-time grid level visualization (waiting/open/filled/cancelled)
- Live order feed with status transitions
- Live PnL chart and exposure breakdown
- Worker health status with heartbeat indicators
- EventBus event stream (filterable)
- Notification delivery status

### SaaS Management
- Subscription plan display with upgrade/downgrade
- Billing history with invoice status
- Affiliate dashboard with referral link, downline, earnings
- License limits display (usage / max)

### Settings
- Exchange account CRUD (API key management)
- Risk parameter configuration
- Notification channel preferences
- Profile + password change + MFA setup

---

## Architecture

```
frontend/
    ├── app/              — Next.js App Router pages
    ├── components/       — shadcn/ui + custom components
    │   └── ui/           — shadcn/ui primitives
    ├── features/         — feature-specific components
    ├── hooks/            — custom React hooks
    ├── lib/              — utilities, API client
    ├── services/         — API + WebSocket services
    ├── stores/           — Zustand stores
    ├── styles/           — global CSS
    └── types/            — TypeScript types
```

---

## Acceptance Criteria

- [ ] Next.js project with TailwindCSS + shadcn/ui
- [ ] Auth pages (login, register)
- [ ] Dashboard layout with sidebar navigation
- [ ] Live trading dashboard with real-time updates
- [ ] Grid visualization
- [ ] Order feed
- [ ] Portfolio overview
- [ ] Risk status
- [ ] Recovery status
- [ ] Worker health
- [ ] EventBus feed
- [ ] Notification settings
- [ ] Subscription + billing + affiliate pages
- [ ] Exchange account settings
- [ ] Component tests
- [ ] Build succeeds
