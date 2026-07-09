# ARCHITECTURE APPROVED

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** ARCHITECTURE APPROVED

---

## 1. APPROVAL STATEMENT

The architecture of the **UTOS Trading Engine** has been reviewed and approved. All documentation files have been revised to reflect the same architectural decisions. **No coding for Sprint 1 may begin until this document is acknowledged by the project owner.**

---

## 2. APPROVED ARCHITECTURAL DECISIONS

| ID | Decision | Status | Rationale |
|----|----------|--------|-----------|
| AD-01 | Project renamed to **UTOS Trading Engine** | Approved | Clear product identity and scope. |
| AD-02 | Terminology: **Trading Instance** replaces Trading Process | Approved | One "instance" = one running trading session per pair/strategy/capital combination. |
| AD-03 | State machine: `CREATED` → `READY` → `RUNNING` → ... | Approved | `READY` is mandatory. `prepare()` must validate API key, balance, grid, sync orders/positions, subscribe market, and allocate worker before `start()`. |
| AD-04 | Event sourcing for every state transition | Approved | Events: `INSTANCE_CREATED`, `INSTANCE_READY`, `INSTANCE_RUNNING`, `INSTANCE_PAUSED`, `INSTANCE_RESUMED`, `INSTANCE_STOPPING`, `INSTANCE_STOPPED`, `INSTANCE_ERROR`, `INSTANCE_RECOVERING`, `INSTANCE_RECOVERED`. |
| AD-05 | `TradingContext` and `KernelContext` | Approved | Reduce parameter complexity. `KernelContext` carries system-wide services; `TradingContext` carries instance-specific collaborators. |
| AD-06 | `ProcessMemory` for runtime state | Approved | Database is source of truth for recovery; runtime state lives in per-instance memory snapshots persisted asynchronously. |
| AD-07 | `IExchangeAdapter` lifecycle split | Approved | `initialize()`, `authenticate()`, `connect_market()`, `connect_account()`, `disconnect()`. Market and account streams are separate. |
| AD-08 | Separation of profit mechanisms | Approved | `TP` = static per-layer take profit; `ProfitLock` = per-position trailing lock; `PortfolioLock` = instance-level trailing lock (premium). |
| AD-09 | Scalability target: 100,000+ Trading Instances | Approved | Symbol-level market channels, worker per instance, PgBouncer, read replicas, partitioning, HPA. |
| AD-10 | Strict gated workflow | Approved | Documentation → Architecture Review → Architecture Approved → Sprint 1 → Code Review → Sprint 2. |

---

## 3. DOCUMENT CONSISTENCY CHECKLIST

| Document | Version | Status | Key Changes |
|----------|---------|--------|-------------|
| `ARCHITECTURE_REVIEW.md` | 1.1.0 | Reviewed | Findings plus resolution status; issues addressed. |
| `INTERFACE_DEFINITIONS.md` | 2.0.0 | Consistent | TradingContext, KernelContext, ProcessMemory, IExchangeAdapter lifecycle, PortfolioLock, TradingInstance. |
| `DATABASE.md` | 2.0.0 | Consistent | `trading_instances` table, READY state, ProcessMemory columns, TP/ProfitLock/PortfolioLock fields, scalability section. |
| `API_GUIDELINES.md` | 2.0.0 | Consistent | `/trading-instances`, `/prepare` endpoint, instance_id, versioning strategy. |
| `architecture/trading_engine.md` | 2.0.0 | Consistent | READY state, event sourcing, separate market/account exchange states. |
| `architecture/event_bus.md` | 2.0.0 | Consistent | `INSTANCE_*` events, `PORTFOLIO_LOCK_*` events, `trading_instance:{id}` channels. |
| `architecture/sequence_diagrams.md` | 2.0.0 | Consistent | PLOE participant, Trading Instance terminology. |
| `FOLDER_RESPONSIBILITY.md` | 2.0.0 | Consistent | `memory/` folder, `trading_instance.py`, `KernelContext`, `TradingContext`. |
| `ROADMAP.md` | 2.0.0 | Consistent | Layer-based sprints, ProcessMemory, KernelContext, separate connections. |
| `DEPLOYMENT_SPEC.md` | 2.0.0 | Consistent | Scalability section, worker pool, database scaling. |
| `PROJECT_BIBLE.md` | 2.0.0 | Approved template | Foundation document with new component placeholders. |
| `MASTER_PROMPT.md` | 2.0.0 | Approved | AI assistant guidelines with gated workflow and new architecture. |
| `CODING_STANDARD.md` | 2.0.0 | Approved | Coding conventions. |
| `ERROR_HANDLING.md` | 2.0.0 | Approved | Error strategy with project rename. |
| `TESTING_STANDARD.md` | 2.0.0 | Approved | Testing strategy with Trading Instance lifecycle. |

---

## 4. GATED WORKFLOW CONFIRMATION

The following gates are enforced:

1. **Documentation** ✅ Complete
2. **Architecture Review** ✅ Complete (`ARCHITECTURE_REVIEW.md`)
3. **Architecture Approved** ✅ This document
4. **Sprint 1** ⏳ Pending (coding begins only after approval)
5. **Code Review** ⏳ Pending
6. **Sprint 2** ⏳ Pending

---

## 5. APPROVAL SIGNATURE

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Project Owner | | | |
| Lead Architect | | | |
| Technical Lead | | | |

---

## 6. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 2.0.0 | Architecture approval document after comprehensive revision cycle. |
