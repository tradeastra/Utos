# Sprint 02: Database

**Duration:** Week 2
**Layer:** Data persistence
**Status:** In Progress
**Branch:** `develop`

---

## Scope

Sprint 2 fokus **hanya pada layer Database**. Tidak menyentuh JWT, login, Docker, CI/CD, frontend, atau trading engine logic.

### In Scope
- Semua model SQLAlchemy selesai (12 tabel per DATABASE.md)
- Relasi antar model selesai
- `session.py` selesai
- Alembic migration lengkap (semua tabel)
- Repository base (`IRepository`) selesai
- Repository tests selesai

### Out of Scope
- Seed data scripts
- Service layer / business logic
- API endpoints
- Auth/JWT changes
- Docker / CI/CD
- Frontend

---

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| S2-01 | All 12 SQLAlchemy models created matching DATABASE.md spec | PENDING |
| S2-02 | All model relationships (FKs + back_populates) defined | PENDING |
| S2-03 | `session.py` provides async session factory + test session helper | PENDING |
| S2-04 | Alembic migration covers all 12 tables | PENDING |
| S2-05 | `IRepository` abstract base class defined | PENDING |
| S2-06 | All repository classes implemented (12 repos for 12 tables) | PENDING |
| S2-07 | Repository unit tests written and passing | PENDING |
| S2-08 | `alembic/env.py` imports all models for autogenerate | PENDING |
| S2-09 | `models/__init__.py` exports all models | PENDING |

---

## 12 Tables (per DATABASE.md)

1. `users`
2. `exchange_accounts`
3. `trading_instances`
4. `positions`
5. `orders`
6. `grid_profiles`
7. `strategies`
8. `transactions`
9. `subscriptions`
10. `affiliates`
11. `notifications`
12. `balances`

---

## Implementation Plan

### Phase 1: Models
- Rewrite `user.py` to match DATABASE.md (add `phone`, `referral_code`, `referred_by`, `last_login_at`, `deleted_at`)
- Rewrite `exchange_account.py` to match spec (fix column names, add missing columns)
- Rewrite `trading_instance.py` to match spec (add FKs to `strategies` + `grid_profiles`, fix Order/Position/Transaction)
- Create `grid_profile.py`
- Create `strategy.py`
- Create `subscription.py`
- Create `affiliate.py`
- Create `notification.py`
- Create `balance.py` (rename from `ExchangeBalance`)
- Update `models/__init__.py` to export all

### Phase 2: Session
- Write `database/session.py` with async session helpers + test session factory

### Phase 3: Migration
- Update `alembic/env.py` to import all models
- Write comprehensive migration `0002_all_tables.py`

### Phase 4: Repositories
- Create `repositories/base.py` with `IRepository` abstract base
- Implement all 12 repository classes

### Phase 5: Tests
- Write repository unit tests using in-memory SQLite or test PostgreSQL
- Tests cover CRUD operations for each repository

---

## Workflow

```
Planning → Implement → Compile → Run Tests → Audit → Fix → Commit → Tag → Next Sprint
```

Commit only after audit passes. Work on `develop` branch. Merge to `main` + tag when complete.
