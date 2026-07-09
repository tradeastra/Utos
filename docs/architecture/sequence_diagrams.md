# SEQUENCE DIAGRAMS

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the sequence diagrams for all critical flows in the UTOS Trading Engine trading system. Each diagram shows the exact order of operations, the participants involved, and the events emitted.

### 1.1 Participants

| Alias | Participant |
|-------|-------------|
| `User` | End user (via frontend) |
| `API` | FastAPI REST API |
| `TE` | Trading Engine |
| `GE` | Grid Engine |
| `EE` | Execution Engine |
| `EA` | Exchange Adapter |
| `EX` | Exchange (Binance, Bybit, etc.) |
| `PE` | Portfolio Engine |
| `RE` | Risk Engine |
| `PLE` | Profit Lock Engine |
| `PLOE` | Portfolio Lock Engine |
| `MH` | Market Hub |
| `EB` | Event Bus |
| `NS` | Notification Service |
| `DB` | Database |
| `RC` | Recovery Engine |
| `AUTH` | Auth Service |

---

## 2. BUY FLOW

### 2.1 Grid Buy Order

```
User    API     TE      GE      EE      EA      EX      EB      PE      NS
 │       │       │       │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │       │       │
 │ Start │       │       │       │       │       │       │       │       │
 │Process│       │       │       │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │       │       │
 │       │ start │       │       │       │       │       │       │       │
 │       │       │──────▶│       │       │       │       │       │       │
 │       │       │ init  │       │       │       │       │       │       │
 │       │       │ grid  │       │       │       │       │       │       │
 │       │       │       │──────▶│       │       │       │       │       │
 │       │       │       │ place │       │       │       │       │       │
 │       │       │       │ buy   │       │       │       │       │       │
 │       │       │       │ orders│       │       │       │       │       │
 │       │       │       │       │──────▶│       │       │       │       │
 │       │       │       │       │ place │       │       │       │       │
 │       │       │       │       │ order │       │       │       │       │
 │       │       │       │       │       │──────▶│       │       │       │
 │       │       │       │       │       │  API  │       │       │       │
 │       │       │       │       │       │◀──────│       │       │       │
 │       │       │       │       │       │ order │       │       │       │
 │       │       │       │       │       │ ID    │       │       │       │
 │       │       │       │       │◀──────│       │       │       │       │
 │       │       │       │       │ result│       │       │       │       │
 │       │       │       │◀──────│       │       │       │       │       │
 │       │       │       │ orders│       │       │       │       │       │
 │       │       │       │ placed│       │       │       │       │       │
 │       │       │       │       │       │       │       │       │       │
 │       │       │       │       │       │       │       │       │       │
 │       │       │       │       │       │       │       │       │       │
 │       │       │       │       │       │  ─────│──────▶│       │       │
 │       │       │       │       │       │       │ ORDER │       │       │
 │       │       │       │       │       │       │PLACED │       │       │
 │       │       │       │       │       │       │       │       │       │
 │       │       │       │       │       │       │ ──────│──────▶│       │
 │       │       │       │       │       │       │       │ ORDER │       │
 │       │       │       │       │       │       │       │PLACED │       │
 │       │       │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │       │       │ notify│
 │       │◀──────│       │       │       │       │       │       │       │
 │  OK   │       │       │       │       │       │       │       │       │
 │◀──────│       │       │       │       │       │       │       │       │
```

### 2.2 Buy Order Filled

```
EX      EA      EE      EB      GE      PE      TE      NS
 │       │       │       │       │       │       │       │
 │ ws    │       │       │       │       │       │       │
 │ fill  │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │
 │       │ order │       │       │       │       │       │
 │       │ filled│       │       │       │       │       │
 │       │       │──┐    │       │       │       │       │
 │       │       │  │ DB │       │       │       │       │
 │       │       │◀─┘    │       │       │       │       │
 │       │       │──────▶│       │       │       │       │
 │       │       │ ORDER │       │       │       │       │
 │       │       │ FILLED│       │       │       │       │
 │       │       │       │──┐    │       │       │       │
 │       │       │       │  │ DB │       │       │       │
 │       │       │       │◀─┘    │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │ BUY   │       │       │       │
 │       │       │       │ FILLED│       │       │       │
 │       │       │       │       │──┐    │       │       │
 │       │       │       │       │  │ DB │       │       │
 │       │       │       │       │◀─┘    │       │       │
 │       │       │       │       │──────▶│       │       │
 │       │       │       │       │ place │       │       │
 │       │       │       │       │ sell  │       │       │
 │       │       │       │       │ order │       │       │
 │       │       │       │       │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │ PORT  │       │       │       │
 │       │       │       │ UPDATE│       │       │       │
 │       │       │       │       │       │──────▶│       │
 │       │       │       │       │       │ open  │       │
 │       │       │       │       │       │ posi- │       │
 │       │       │       │       │       │ tion  │       │
 │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │ notify│
```

---

## 3. SELL FLOW

### 3.1 Grid Sell Order (After Buy Filled)

```
GE      EE      EA      EX      EB      PE      NS
 │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │
 │ place │       │       │       │       │       │
 │ sell  │       │       │       │       │       │
 │       │──────▶│       │       │       │       │
 │       │ place │       │       │       │       │
 │       │ order │       │       │       │       │
 │       │       │──────▶│       │       │       │
 │       │       │  API  │       │       │       │
 │       │       │◀──────│       │       │       │
 │       │       │ order │       │       │       │
 │       │       │ ID    │       │       │       │
 │       │◀──────│       │       │       │       │
 │       │ result│       │       │       │       │
 │◀──────│       │       │       │       │       │
 │       │       │       │       │       │       │
 │       │       │       │       │ ──────│──────▶│
 │       │       │       │       │ ORDER │       │
 │       │       │       │       │PLACED │       │
```

### 3.2 Sell Order Filled

```
EX      EA      EE      EB      GE      PE      TE      NS
 │       │       │       │       │       │       │       │
 │ ws    │       │       │       │       │       │       │
 │ fill  │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │
 │       │ sell  │       │       │       │       │       │
 │       │ filled│       │       │       │       │       │
 │       │       │──┐    │       │       │       │       │
 │       │       │  │ DB │       │       │       │       │
 │       │       │◀─┘    │       │       │       │       │
 │       │       │──────▶│       │       │       │       │
 │       │       │ SELL  │       │       │       │       │
 │       │       │ FILLED│       │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │ on    │       │       │       │
 │       │       │       │ sell  │       │       │       │
 │       │       │       │ filled│       │       │       │
 │       │       │       │       │──┐    │       │       │
 │       │       │       │       │  │ DB │       │       │
 │       │       │       │       │◀─┘    │       │       │
 │       │       │       │       │──────▶│       │       │
 │       │       │       │       │ place │       │       │
 │       │       │       │       │ next  │       │       │
 │       │       │       │       │ buy   │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │ PORT  │       │       │       │
 │       │       │       │ UPDATE│       │       │       │
 │       │       │       │       │       │──────▶│       │
 │       │       │       │       │       │ close │       │
 │       │       │       │       │       │ posi- │       │
 │       │       │       │       │       │ tion  │       │
 │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │ notify│
```

---

## 4. TAKE PROFIT (TP) FLOW

```
GE      EE      EA      EX      EB      PE      NS
 │       │       │       │       │       │       │
 │ TP    │       │       │       │       │       │
 │ trig- │       │       │       │       │       │
 │ gered │       │       │       │       │       │
 │──────▶│       │       │       │       │       │
 │ place │       │       │       │       │       │
 │ TP    │       │       │       │       │       │
 │ sell  │       │       │       │       │       │
 │       │──────▶│       │       │       │       │
 │       │ place │       │       │       │       │
 │       │ TP    │       │       │       │       │
 │       │ order │       │       │       │       │
 │       │       │──────▶│       │       │       │
 │       │       │  API  │       │       │       │
 │       │       │◀──────│       │       │       │
 │       │◀──────│       │       │       │       │
 │◀──────│       │       │       │       │       │
 │       │       │       │       │       │       │
 │       │       │       │ ──────│──────▶│       │
 │       │       │       │ TP    │       │       │
 │       │       │       │PLACED │       │       │
 │       │       │       │       │       │──────▶│
 │       │       │       │       │       │ notify│
```

### TP Filled

```
EX      EA      EE      EB      GE      PE      TE      NS
 │       │       │       │       │       │       │       │
 │ ws    │       │       │       │       │       │       │
 │ fill  │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │
 │       │ TP    │       │       │       │       │       │
 │       │ filled│       │       │       │       │       │
 │       │       │──┐    │       │       │       │       │
 │       │       │  │ DB │       │       │       │       │
 │       │       │◀─┘    │       │       │       │       │
 │       │       │──────▶│       │       │       │       │
 │       │       │ TP    │       │       │       │       │
 │       │       │ FILLED│       │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │ TP    │       │       │       │
 │       │       │       │ done  │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │ PORT  │       │       │       │
 │       │       │       │ UPDATE│       │       │       │
 │       │       │       │       │       │──────▶│       │
 │       │       │       │       │       │ calc  │       │
 │       │       │       │       │       │ profit│       │
 │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │ notify│
```

---

## 5. PROFIT LOCK FLOW

```
MH      PLE     TE      EE      EA      EX      EB      PE      NS
 │       │       │       │       │       │       │       │       │
 │ price │       │       │       │       │       │       │       │
 │ update│       │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │       │
 │       │ check│       │       │       │       │       │       │
 │       │ trig-│       │       │       │       │       │       │
 │       │ ger  │       │       │       │       │       │       │
 │       │       │       │       │       │       │       │       │
 │       │ YES: │       │       │       │       │       │       │
 │       │ price│       │       │       │       │       │       │
 │       │ >    │       │       │       │       │       │       │
 │       │ trig │       │       │       │       │       │       │
 │       │       │       │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │       │
 │       │ PROF │       │       │       │       │       │       │
 │       │ LOCK │       │       │       │       │       │       │
 │       │ TRIG │       │       │       │       │       │       │
 │       │       │──────▶│       │       │       │       │       │
 │       │       │ place │       │       │       │       │       │
 │       │       │ lock  │       │       │       │       │       │
 │       │       │ sell  │       │       │       │       │       │
 │       │       │       │──────▶│       │       │       │       │
 │       │       │       │ place │       │       │       │       │
 │       │       │       │ order │       │       │       │       │
 │       │       │       │       │──────▶│       │       │       │
 │       │       │       │       │  API  │       │       │       │
 │       │       │       │       │◀──────│       │       │       │
 │       │       │       │◀──────│       │       │       │       │
 │       │       │◀──────│       │       │       │       │       │
 │       │       │       │       │       │       │       │       │
 │       │       │       │       │       │ ──────│──────▶│       │
 │       │       │       │       │       │ PROF  │       │       │
 │       │       │       │       │       │ LOCK  │       │       │
 │       │       │       │       │       │ TRIG  │       │       │
 │       │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │       │ notify│
```

### Profit Lock Trailing Update

```
MH      PLE     EB      EE
 │       │       │       │
 │ price │       │       │
 │ up    │       │       │
 │──────▶│       │       │
 │       │ update│       │
 │       │ trail │       │
 │       │──────▶│       │
 │       │ PROF  │       │
 │       │ LOCK  │       │
 │       │ UPD   │       │
 │       │       │──────▶│
 │       │       │ cancel│
 │       │       │ old   │
 │       │       │ order │
 │       │       │──────▶│
 │       │       │ place │
 │       │       │ new   │
 │       │       │ order │
```

---

## 6. RECOVERY FLOW

```
EB      TE      RC      EA      EX      DB      GE      NS
 │       │       │       │       │       │       │       │
 │ ERROR │       │       │       │       │       │       │
 │ event │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │
 │       │ trans │       │       │       │       │       │
 │       │ ition │       │       │       │       │       │
 │       │ to    │       │       │       │       │       │
 │       │ ERROR │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │
 │       │ reco- │       │       │       │       │       │
 │       │ ver   │       │       │       │       │       │
 │       │       │──┐    │       │       │       │       │
 │       │       │  │ DB │       │       │       │       │
 │       │       │◀─┘    │       │       │       │       │
 │       │       │──────▶│       │       │       │       │
 │       │       │ get   │       │       │       │       │
 │       │       │ open  │       │       │       │       │
 │       │       │ orders│       │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │  API  │       │       │       │
 │       │       │       │◀──────│       │       │       │
 │       │       │◀──────│       │       │       │       │
 │       │       │ recon │       │       │       │       │
 │       │       │ cile  │       │       │       │       │
 │       │       │──┐    │       │       │       │       │
 │       │       │  │ DB │       │       │       │       │
 │       │       │◀─┘    │       │       │       │       │
 │       │       │       │       │       │       │       │
 │       │       │ rebuild grid    │       │       │       │
 │       │       │──────────────────────────────▶│       │
 │       │       │       │       │       │       │ grid  │
 │       │       │       │       │       │       │ state │
 │       │       │◀──────────────────────────────│       │
 │       │       │       │       │       │       │       │
 │       │       │──────▶│       │       │       │       │
 │       │       │ RECOV │       │       │       │       │
 │       │       │ event │       │       │       │       │
 │       │◀──────│       │       │       │       │       │
 │       │ trans │       │       │       │       │       │
 │       │ ition │       │       │       │       │       │
 │       │ to    │       │       │       │       │       │
 │       │ RUN-  │       │       │       │       │       │
 │       │ NING  │       │       │       │       │       │
 │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │ notify│
```

---

## 7. RESTART FLOW (System-Wide)

```
Kernel  DB      EB      MH      EA      TE      GE      Workers
 │       │       │       │       │       │       │       │
 │ start │       │       │       │       │       │       │
 │──┐    │       │       │       │       │       │       │
 │  │ DB │       │       │       │       │       │       │
 │◀─┘    │       │       │       │       │       │       │
 │ load  │       │       │       │       │       │       │
 │ active│       │       │       │       │       │       │
 │ proc  │       │       │       │       │       │       │
 │       │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │
 │ start │       │       │       │       │       │       │
 │ event │       │       │       │       │       │       │
 │ bus   │       │       │       │       │       │       │
 │       │ ready │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │
 │       │       │ start │       │       │       │       │
 │       │       │──────▶│       │       │       │       │
 │       │       │       │ con-  │       │       │       │
 │       │       │       │ nect  │       │       │       │
 │       │       │       │──────▶│       │       │       │
 │       │       │       │       │ con-  │       │       │
 │       │       │       │       │ nect  │       │       │
 │       │       │       │◀──────│       │       │       │
 │       │       │       │ ready │       │       │       │
 │       │       │       │       │       │       │       │
 │ load active processes from DB    │       │       │       │
 │──────▶│       │       │       │       │       │       │
 │       │       │       │       │       │       │       │
 │ for each active process:         │       │       │       │
 │─────────────────────────────────▶│       │       │       │
 │       │       │       │       │ recover│       │       │
 │       │       │       │       │──────▶│       │       │
 │       │       │       │       │       │ sync  │       │
 │       │       │       │       │       │ grid  │       │
 │       │       │       │       │       │──────▶│       │
 │       │       │       │       │       │       │ ready │
 │       │       │       │       │       │◀──────│       │
 │       │       │       │       │       │ resume│       │
 │       │       │       │       │       │──────▶│       │
 │       │       │       │       │       │       │ active│
 │       │       │       │       │       │       │       │
 │ start workers                   │       │       │       │
 │──────────────────────────────────────────────────────▶│
 │       │       │       │       │       │       │ running│
```

---

## 8. LOGIN FLOW

```
User    API     AUTH    DB      EB      NS
 │       │       │       │       │       │
 │ login │       │       │       │       │
 │──────▶│       │       │       │       │
 │       │ auth  │       │       │       │
 │       │──────▶│       │       │       │
 │       │       │ verify│       │       │
 │       │       │──────▶│       │       │
 │       │       │◀──────│       │       │
 │       │       │ valid │       │       │
 │       │       │──┐    │       │       │
 │       │       │  │ gen│       │       │
 │       │       │  │ JWT│       │       │
 │       │       │◀─┘    │       │       │
 │       │◀──────│       │       │       │
 │       │ token │       │       │       │
 │       │       │       │       │       │
 │       │──────▶│       │       │       │
 │       │       │ log   │       │       │
 │       │       │ login │       │       │
 │       │       │──────▶│       │       │
 │       │       │       │ USER  │       │
 │       │       │       │ LOGIN │       │
 │       │       │       │──────▶│       │
 │       │       │       │       │──────▶│
 │       │       │       │       │ welcome│
 │ token│       │       │       │       │
 │◀──────│       │       │       │       │
```

---

## 9. STOP TRADING INSTANCE FLOW

```
User    API     TE      EB      GE      EE      EA      EX      PE      NS
 │       │       │       │       │       │       │       │       │       │
 │ stop  │       │       │       │       │       │       │       │       │
 │──────▶│       │       │       │       │       │       │       │       │
 │       │──────▶│       │       │       │       │       │       │       │
 │       │       │ trans │       │       │       │       │       │       │
 │       │       │ ition │       │       │       │       │       │       │
 │       │       │ to    │       │       │       │       │       │       │
 │       │       │ STOP- │       │       │       │       │       │       │
 │       │       │ PING  │       │       │       │       │       │       │
 │       │       │──────▶│       │       │       │       │       │       │
 │       │       │ STOP  │       │       │       │       │       │       │
 │       │       │ PING  │       │       │       │       │       │       │
 │       │       │       │──────▶│       │       │       │       │       │
 │       │       │       │ cancel│       │       │       │       │       │
 │       │       │       │ all   │       │       │       │       │       │
 │       │       │       │ grid  │       │       │       │       │       │
 │       │       │       │ orders│       │       │       │       │       │
 │       │       │       │──────▶│       │       │       │       │       │
 │       │       │       │       │ cancel│       │       │       │       │
 │       │       │       │       │ all   │       │       │       │       │
 │       │       │       │       │ orders│       │       │       │       │
 │       │       │       │       │──────▶│       │       │       │       │
 │       │       │       │       │       │ cancel│       │       │       │
 │       │       │       │       │       │──────▶│       │       │       │
 │       │       │       │       │       │  API  │       │       │       │
 │       │       │       │       │       │◀──────│       │       │       │
 │       │       │       │       │◀──────│       │       │       │       │
 │       │       │       │◀──────│       │       │       │       │       │
 │       │       │       │ done  │       │       │       │       │       │
 │       │       │       │       │       │       │       │       │       │
 │       │       │ close positions                   │       │       │       │
 │       │       │──────────────────────────────────────────▶│       │       │
 │       │       │       │       │       │       │       │ close │       │
 │       │       │       │       │       │       │       │ posi- │       │
 │       │       │       │       │       │       │       │ tions │       │
 │       │       │◀──────────────────────────────────────────│       │       │
 │       │       │       │       │       │       │       │       │       │
 │       │       │ trans │       │       │       │       │       │       │
 │       │       │ ition │       │       │       │       │       │       │
 │       │       │ to    │       │       │       │       │       │       │
 │       │       │ STOP- │       │       │       │       │       │       │
 │       │       │ PED   │       │       │       │       │       │       │
 │       │       │──────▶│       │       │       │       │       │       │
 │       │       │ STOP  │       │       │       │       │       │       │
 │       │       │ PED   │       │       │       │       │       │       │
 │       │       │       │       │       │       │       │──────▶│       │
 │       │       │       │       │       │       │       │ final │       │
 │       │       │       │       │       │       │       │ P&L   │       │
 │       │       │       │       │       │       │       │       │──────▶│
 │       │       │       │       │       │       │       │       │ notify│
 │       │◀──────│       │       │       │       │       │       │       │
 │  OK   │       │       │       │       │       │       │       │       │
 │◀──────│       │       │       │       │       │       │       │       │
```

---

## 10. ERROR FLOW (Exchange Timeout)

```
EE      EA      EX      EB      TE      NS
 │       │       │       │       │       │
 │ place │       │       │       │       │
 │ order │       │       │       │       │
 │──────▶│       │       │       │       │
 │       │  API  │       │       │       │
 │       │──────▶│       │       │       │
 │       │       │       │       │       │
 │       │  ...  │       │       │       │
 │       │  ...  │       │       │       │
 │       │ TIMEOUT       │       │       │
 │       │◀──────│       │       │       │
 │       │ error │       │       │       │
 │◀──────│       │       │       │       │
 │ error │       │       │       │       │
 │       │       │       │       │       │
 │ retry 1:                       │       │
 │──────▶│       │       │       │       │
 │       │──────▶│       │       │       │
 │       │ TIMEOUT       │       │       │
 │◀──────│       │       │       │       │
 │       │       │       │       │       │
 │ retry 2:                       │       │
 │──────▶│       │       │       │       │
 │       │──────▶│       │       │       │
 │       │ TIMEOUT       │       │       │
 │◀──────│       │       │       │       │
 │       │       │       │       │       │
 │ retry 3:                       │       │
 │──────▶│       │       │       │       │
 │       │──────▶│       │       │       │
 │       │ TIMEOUT       │       │       │
 │◀──────│       │       │       │       │
 │       │       │       │       │       │
 │ max retries exceeded           │       │
 │──────▶│       │       │       │       │
 │ ERROR │       │       │       │       │
 │ event │       │       │       │       │
 │       │──────▶│       │       │       │
 │       │       │ TRAD  │       │       │
 │       │       │ PROC  │       │       │
 │       │       │ ERROR │       │       │
 │       │       │──────▶│       │       │
 │       │       │       │ pause │       │
 │       │       │       │ proc  │       │
 │       │       │       │──────▶│       │
 │       │       │       │       │ notify│
 │       │       │       │       │ user  │
```

---

## 11. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial sequence diagrams |
| 2026-07-09 | 2.0.0 | Architecture revision: project rename, Trading Instance terminology, PLOE participant |
