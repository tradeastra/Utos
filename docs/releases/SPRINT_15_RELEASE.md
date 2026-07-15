# Sprint 15 Release — Frontend Dashboard (v0.15.0)

**Date:** 2026-07-15  
**Sprint:** 15  
**Version:** v0.15.0  
**Status:** Released  

---

## Summary

Complete frontend dashboard for the UTOS trading platform. Built with Next.js 14 (App Router), TailwindCSS, and shadcn/ui components. Provides authentication, trading monitoring, grid visualization, portfolio management, risk settings, SaaS subscription/billing, affiliate dashboard, and exchange account management.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Styling:** TailwindCSS with shadcn/ui design system
- **State Management:** Zustand (auth store)
- **Icons:** Lucide React
- **Charts:** Recharts (available for future use)
- **Testing:** Vitest + @vitejs/plugin-react
- **Language:** TypeScript

## Architecture

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout (dark mode, global CSS)
│   ├── page.tsx                # Redirect to /dashboard
│   ├── login/page.tsx          # Login form with auth store
│   ├── register/page.tsx       # Registration form
│   ├── dashboard/
│   │   ├── layout.tsx          # Dashboard layout with sidebar
│   │   ├── page.tsx            # Overview (portfolio, risk, workers)
│   │   ├── trading/            # Trading instances table
│   │   ├── grid/               # Grid level visualization
│   │   ├── orders/             # Orders feed table
│   │   ├── portfolio/          # Positions + PnL summary
│   │   ├── risk/               # Risk limits + gatekeeper stats
│   │   ├── recovery/           # 4-layer recovery pipeline status
│   │   ├── workers/            # Worker health monitoring
│   │   ├── events/             # EventBus live feed
│   │   ├── notifications/      # Notification channels + history
│   │   ├── subscription/       # Plan comparison cards
│   │   ├── billing/            # Invoice history table
│   │   └── affiliate/          # Referral stats + downline
│   └── settings/
│       └── exchanges/          # Exchange account management
├── components/
│   ├── sidebar.tsx             # Navigation sidebar with active states
│   └── ui/
│       ├── card.tsx            # Card, CardHeader, CardTitle, CardContent, CardFooter
│       ├── button.tsx          # Button with variants (default, secondary, destructive, outline, ghost)
│       ├── badge.tsx           # Badge with variants (default, secondary, success, destructive, warning)
│       └── input.tsx           # Form input
├── lib/
│   ├── utils.ts                # cn(), formatCurrency, formatNumber, formatPercent, timeAgo
│   └── utils.test.ts           # 11 vitest tests
├── services/
│   ├── api.ts                  # ApiClient class (auth, trading, SaaS endpoints)
│   └── websocket.ts            # WebSocketService (subscribe, reconnect, event dispatch)
├── stores/
│   └── auth.ts                 # Zustand auth store (user, token, login, logout)
├── types/
│   └── index.ts                # TypeScript interfaces for all domain models
├── styles/
│   └── globals.css             # TailwindCSS base + shadcn/ui CSS variables
├── package.json
├── tsconfig.json
├── next.config.js              # API proxy rewrites
├── tailwind.config.ts          # shadcn/ui theme extensions
├── postcss.config.js
└── vitest.config.ts
```

## Pages Delivered

### Authentication
- **Login** — Email/password form, JWT token storage, redirect to dashboard
- **Register** — Email/password/full name form, redirect to login on success

### Trading Dashboard
- **Overview** — Portfolio value, PnL, exposure, open positions, risk status, worker health
- **Trading Instances** — Table of active trading instances with status badges
- **Grid Visualization** — Grid levels with price, side, status, quantity
- **Orders Feed** — Recent orders with symbol, side, type, status, timestamp
- **Portfolio** — Unrealized/realized PnL summary, open positions table
- **Risk Management** — Exposure limits, position limits, order gatekeeper stats
- **Recovery** — 4-layer recovery pipeline status (connection, state, runtime, persistence)
- **Workers** — Worker health monitoring with error counts
- **Events** — EventBus live feed with event types and timestamps
- **Notifications** — Channel configuration, recent notification history

### SaaS
- **Subscription** — 4 plan tiers (Free, Starter, Pro, Enterprise) with upgrade buttons
- **Billing** — Invoice history with provider, status, amount
- **Affiliate** — Referral stats, referral link, downline list

### Settings
- **Exchange Accounts** — Connected exchanges list, add new exchange form

## Service Layer

### ApiClient (`services/api.ts`)
- Authenticated REST API client with token management
- Methods: login, register, logout, getTradingInstances, getGridState, getOrders, getPortfolio, getSubscription, getInvoices, getAffiliateStats
- Token stored in localStorage, auto-attached to Authorization header

### WebSocketService (`services/websocket.ts`)
- Real-time event subscription
- Auto-reconnect with exponential backoff
- Event dispatch to registered handlers

## State Management

### Auth Store (`stores/auth.ts`)
- Zustand store with user info, access token
- Actions: login (set token + user), logout (clear state)

## Tests

- **Vitest:** 11 tests passing
  - `cn()` — class merging, tailwind deduplication
  - `formatCurrency()` — USD formatting
  - `formatNumber()` — decimal formatting
  - `formatPercent()` — positive/negative percentage
  - `timeAgo()` — seconds, minutes, hours ago

## Build Status

- `npm run build` — ✅ Compiled successfully
- `npx vitest run` — ✅ 11/11 tests passed

## Dependencies

All backend sprints (01-14) provide the REST API and WebSocket endpoints that this frontend consumes.

## What's Next

Sprint 16: Production Hardening & Deployment — Docker, Kubernetes, CI/CD, monitoring, security hardening.
