# DATABASE DESIGN

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the database schema for the UTOS Trading Engine. The database is built on PostgreSQL and uses SQLAlchemy ORM for Python.

### 1.1 Design Principles

- **UUID Primary Keys**: All tables use UUID for primary keys to avoid ID collisions
- **Timestamps**: All tables have `created_at` and `updated_at` timestamps
- **Soft Deletes**: Critical tables use `deleted_at` for soft deletes instead of hard deletes
- **Indexes**: Strategic indexes on frequently queried fields
- **Foreign Keys**: Proper foreign key relationships with cascade rules
- **Normalization**: Third normal form (3NF) with denormalization only where performance-critical

### 1.2 Naming Conventions

- **Table names**: `snake_case` (e.g., `users`, `exchange_accounts`, `orders`)
- **Column names**: `snake_case` (e.g., `user_id`, `created_at`, `is_active`)
- **Foreign keys**: `{table}_id` (e.g., `user_id`, `order_id`)
- **Indexes**: `idx_{table}_{column}` (e.g., `idx_orders_user_id`)
- **Unique constraints**: `uq_{table}_{column}` (e.g., `uq_users_email`)

---

## 2. CORE ENTITIES

### 2.1 Users

**Table**: `users`

**Description**: User accounts for the UTOS platform.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique user identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| full_name | VARCHAR(100) | | User full name |
| phone | VARCHAR(20) | | Phone number |
| is_active | BOOLEAN | DEFAULT TRUE | Account active status |
| is_verified | BOOLEAN | DEFAULT FALSE | Email verification status |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'user' | User role (user, admin) |
| subscription_tier | VARCHAR(20) | NOT NULL, DEFAULT 'free' | Subscription tier |
| referral_code | VARCHAR(20) | UNIQUE, INDEX | User's referral code |
| referred_by | UUID | FK → users.id | User who referred this user |
| last_login_at | TIMESTAMP | | Last login timestamp |
| deleted_at | TIMESTAMP | | Soft delete timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_users_email` on `email`
- `idx_users_referral_code` on `referral_code`
- `idx_users_subscription_tier` on `subscription_tier`

**Relationships**:
- One-to-Many with `exchange_accounts`
- One-to-Many with `trading_instances`
- One-to-Many with `orders`
- One-to-Many with `positions`
- One-to-Many with `notifications`
- One-to-Many with `transactions`
- Self-referential for referrals (`referred_by`)

---

### 2.2 Exchange Accounts

**Table**: `exchange_accounts`

**Description**: Connected exchange accounts for users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique exchange account identifier |
| user_id | UUID | FK → users.id, NOT NULL, INDEX | User who owns this account |
| exchange_name | VARCHAR(50) | NOT NULL, INDEX | Exchange name (binance, bybit, etc.) |
| account_name | VARCHAR(100) | NOT NULL | User-defined account name |
| api_key_encrypted | TEXT | NOT NULL | Encrypted API key |
| api_secret_encrypted | TEXT | NOT NULL | Encrypted API secret |
| is_testnet | BOOLEAN | DEFAULT FALSE | Whether this is a testnet account |
| is_active | BOOLEAN | DEFAULT TRUE | Account active status |
| last_synced_at | TIMESTAMP | | Last successful sync timestamp |
| connection_status | VARCHAR(20) | DEFAULT 'disconnected' | Connection status |
| deleted_at | TIMESTAMP | | Soft delete timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_exchange_accounts_user_id` on `user_id`
- `idx_exchange_accounts_exchange_name` on `exchange_name`

**Relationships**:
- Many-to-One with `users`
- One-to-Many with `orders`
- One-to-Many with `balances`

---

### 2.3 Trading Instances

**Table**: `trading_instances`

**Description**: Active trading instances (grid trading sessions). A user can have multiple instances for the same pair and strategy with different capital, grid, and risk settings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique trading instance identifier |
| user_id | UUID | FK → users.id, NOT NULL, INDEX | User who owns this instance |
| exchange_account_id | UUID | FK → exchange_accounts.id, NOT NULL, INDEX | Exchange account used |
| strategy_id | UUID | FK → strategies.id, NOT NULL, INDEX | Strategy being used |
| grid_profile_id | UUID | FK → grid_profiles.id, NOT NULL, INDEX | Grid configuration |
| symbol | VARCHAR(20) | NOT NULL, INDEX | Trading pair symbol |
| status | VARCHAR(20) | NOT NULL, INDEX, DEFAULT 'created' | Instance status |
| start_price | DECIMAL(20, 8) | NOT NULL | Price when instance started |
| current_price | DECIMAL(20, 8) | | Current market price |
| total_investment | DECIMAL(20, 8) | NOT NULL | Total investment amount |
| base_currency | VARCHAR(10) | NOT NULL | Base currency (e.g., BTC) |
| quote_currency | VARCHAR(10) | NOT NULL | Quote currency (e.g., USDT) |
| profit_lock_enabled | BOOLEAN | DEFAULT FALSE | Enable per-position trailing profit lock |
| profit_lock_trigger_percentage | DECIMAL(5, 2) | | Profit lock trigger percentage |
| profit_lock_trail_percentage | DECIMAL(5, 2) | | Profit lock trail percentage |
| portfolio_lock_enabled | BOOLEAN | DEFAULT FALSE | Enable instance-level trailing portfolio lock |
| portfolio_lock_trigger_percentage | DECIMAL(5, 2) | | Portfolio lock trigger percentage |
| portfolio_lock_trail_percentage | DECIMAL(5, 2) | | Portfolio lock trail percentage |
| worker_id | VARCHAR(100) | INDEX | Assigned worker ID for this instance |
| memory_snapshot | JSONB | | Last persisted ProcessMemory snapshot |
| memory_version | INTEGER | DEFAULT 0 | ProcessMemory snapshot version |
| error_message | TEXT | | Error message if status is error |
| started_at | TIMESTAMP | | Instance start timestamp |
| stopped_at | TIMESTAMP | | Instance stop timestamp |
| deleted_at | TIMESTAMP | | Soft delete timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Status Values**: `created`, `ready`, `running`, `paused`, `stopping`, `stopped`, `error`, `recovering`

**Indexes**:
- `idx_trading_instances_user_id` on `user_id`
- `idx_trading_instances_exchange_account_id` on `exchange_account_id`
- `idx_trading_instances_strategy_id` on `strategy_id`
- `idx_trading_instances_status` on `status`
- `idx_trading_instances_symbol` on `symbol`

**Relationships**:
- Many-to-One with `users`
- Many-to-One with `exchange_accounts`
- Many-to-One with `strategies`
- Many-to-One with `grid_profiles`
- One-to-Many with `orders`
- One-to-Many with `positions`

---

### 2.4 Positions

**Table**: `positions`

**Description**: Current trading positions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique position identifier |
| trading_instance_id | UUID | FK → trading_instances.id, NOT NULL, INDEX | Associated trading instance |
| symbol | VARCHAR(20) | NOT NULL, INDEX | Trading pair symbol |
| side | VARCHAR(10) | NOT NULL | Position side (long, short) |
| entry_price | DECIMAL(20, 8) | NOT NULL | Average entry price |
| current_price | DECIMAL(20, 8) | | Current market price |
| quantity | DECIMAL(20, 8) | NOT NULL | Position quantity |
| value | DECIMAL(20, 8) | NOT NULL | Position value |
| unrealized_pnl | DECIMAL(20, 8) | DEFAULT 0 | Unrealized profit/loss |
| realized_pnl | DECIMAL(20, 8) | DEFAULT 0 | Realized profit/loss |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_positions_trading_instance_id` on `trading_instance_id`
- `idx_positions_symbol` on `symbol`

**Relationships**:
- Many-to-One with `trading_instances`

---

### 2.5 Orders

**Table**: `orders`

**Description**: Individual orders placed on exchanges.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique order identifier |
| user_id | UUID | FK → users.id, NOT NULL, INDEX | User who placed the order |
| exchange_account_id | UUID | FK → exchange_accounts.id, NOT NULL, INDEX | Exchange account used |
| trading_instance_id | UUID | FK → trading_instances.id, INDEX | Associated trading instance |
| exchange_order_id | VARCHAR(100) | INDEX | Exchange's order ID |
| symbol | VARCHAR(20) | NOT NULL, INDEX | Trading pair symbol |
| side | VARCHAR(10) | NOT NULL | Order side (buy, sell) |
| order_type | VARCHAR(20) | NOT NULL | Order type (limit, market, stop_limit) |
| quantity | DECIMAL(20, 8) | NOT NULL | Order quantity |
| price | DECIMAL(20, 8) | | Order price (null for market) |
| stop_price | DECIMAL(20, 8) | | Stop price (for stop orders) |
| filled_quantity | DECIMAL(20, 8) | DEFAULT 0 | Filled quantity |
| average_fill_price | DECIMAL(20, 8) | | Average fill price |
| status | VARCHAR(20) | NOT NULL, INDEX, DEFAULT 'pending' | Order status |
| error_message | TEXT | | Error message if failed |
| grid_level | INTEGER | | Grid level number (for grid orders) |
| purpose | VARCHAR(30) | NOT NULL, DEFAULT 'grid' | Order purpose: grid, take_profit, profit_lock, portfolio_lock, stop_loss |
| is_profit_lock | BOOLEAN | DEFAULT FALSE | Whether this is a profit lock order (deprecated, use purpose) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |
| filled_at | TIMESTAMP | | Fill timestamp |

**Status Values**: `pending`, `open`, `partially_filled`, `filled`, `cancelled`, `rejected`, `expired`

**Indexes**:
- `idx_orders_user_id` on `user_id`
- `idx_orders_exchange_account_id` on `exchange_account_id`
- `idx_orders_trading_instance_id` on `trading_instance_id`
- `idx_orders_exchange_order_id` on `exchange_order_id`
- `idx_orders_symbol` on `symbol`
- `idx_orders_status` on `status`

**Relationships**:
- Many-to-One with `users`
- Many-to-One with `exchange_accounts`
- Many-to-One with `trading_instances`

---

### 2.6 Grid Profiles

**Table**: `grid_profiles`

**Description**: Grid trading configuration profiles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique grid profile identifier |
| user_id | UUID | FK → users.id, NOT NULL, INDEX | User who owns this profile |
| name | VARCHAR(100) | NOT NULL | Profile name |
| strategy_type | VARCHAR(50) | NOT NULL | Strategy type (smart_grid, adaptive_grid, etc.) |
| upper_price | DECIMAL(20, 8) | NOT NULL | Upper price boundary |
| lower_price | DECIMAL(20, 8) | NOT NULL | Lower price boundary |
| grid_count | INTEGER | NOT NULL | Number of grid levels |
| grid_spacing | DECIMAL(20, 8) | | Spacing between grid levels |
| investment_per_grid | DECIMAL(20, 8) | NOT NULL | Investment per grid level |
| take_profit_enabled | BOOLEAN | DEFAULT FALSE | Enable per-layer take profit |
| take_profit_percentage | DECIMAL(5, 2) | | Per-layer take profit percentage |
| stop_loss_enabled | BOOLEAN | DEFAULT FALSE | Enable stop loss |
| stop_loss_percentage | DECIMAL(5, 2) | | Stop loss percentage |
| is_default | BOOLEAN | DEFAULT FALSE | Whether this is default profile |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_grid_profiles_user_id` on `user_id`

**Relationships**:
- Many-to-One with `users`
- One-to-Many with `trading_instances`

---

### 2.7 Strategies

**Table**: `strategies`

**Description**: Available trading strategies.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique strategy identifier |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Strategy name |
| type | VARCHAR(50) | NOT NULL | Strategy type |
| description | TEXT | | Strategy description |
| min_investment | DECIMAL(20, 8) | NOT NULL | Minimum investment required |
| max_investment | DECIMAL(20, 8) | | Maximum investment allowed |
| is_active | BOOLEAN | DEFAULT TRUE | Strategy active status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Strategy Types**: `smart_grid`, `adaptive_grid`, `infinity_grid`, `dca`

**Indexes**:
- `uq_strategies_name` on `name`

**Relationships**:
- One-to-Many with `trading_instances`

---

### 2.8 Transactions

**Table**: `transactions`

**Description**: Financial transactions (deposits, withdrawals, fees).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique transaction identifier |
| user_id | UUID | FK → users.id, NOT NULL, INDEX | User associated with transaction |
| type | VARCHAR(20) | NOT NULL, INDEX | Transaction type |
| amount | DECIMAL(20, 8) | NOT NULL | Transaction amount |
| currency | VARCHAR(10) | NOT NULL | Currency code |
| status | VARCHAR(20) | NOT NULL, INDEX, DEFAULT 'pending' | Transaction status |
| reference_id | VARCHAR(100) | | External reference ID |
| description | TEXT | | Transaction description |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |
| completed_at | TIMESTAMP | | Completion timestamp |

**Transaction Types**: `deposit`, `withdrawal`, `fee`, `subscription`, `refund`

**Status Values**: `pending`, `processing`, `completed`, `failed`, `cancelled`

**Indexes**:
- `idx_transactions_user_id` on `user_id`
- `idx_transactions_type` on `type`
- `idx_transactions_status` on `status`

**Relationships**:
- Many-to-One with `users`

---

### 2.9 Subscriptions

**Table**: `subscriptions`

**Description**: User subscription records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique subscription identifier |
| user_id | UUID | FK → users.id, NOT NULL, UNIQUE, INDEX | User with subscription |
| tier | VARCHAR(20) | NOT NULL | Subscription tier |
| start_date | DATE | NOT NULL | Subscription start date |
| end_date | DATE | NOT NULL | Subscription end date |
| is_active | BOOLEAN | DEFAULT TRUE | Subscription active status |
| auto_renew | BOOLEAN | DEFAULT FALSE | Auto-renewal enabled |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Subscription Tiers**: `free`, `basic`, `pro`, `enterprise`

**Indexes**:
- `uq_subscriptions_user_id` on `user_id`
- `idx_subscriptions_tier` on `tier`

**Relationships**:
- One-to-One with `users`

---

### 2.10 Affiliates

**Table**: `affiliates`

**Description**: Affiliate program records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique affiliate identifier |
| user_id | UUID | FK → users.id, NOT NULL, UNIQUE, INDEX | User who is affiliate |
| commission_rate | DECIMAL(5, 2) | NOT NULL | Commission rate percentage |
| total_earnings | DECIMAL(20, 8) | DEFAULT 0 | Total earnings |
| total_referrals | INTEGER | DEFAULT 0 | Total number of referrals |
| is_active | BOOLEAN | DEFAULT TRUE | Affiliate active status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `uq_affiliates_user_id` on `user_id`

**Relationships**:
- One-to-One with `users`

---

### 2.11 Notifications

**Table**: `notifications`

**Description**: User notifications.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique notification identifier |
| user_id | UUID | FK → users.id, NOT NULL, INDEX | User to notify |
| type | VARCHAR(50) | NOT NULL, INDEX | Notification type |
| title | VARCHAR(200) | NOT NULL | Notification title |
| message | TEXT | NOT NULL | Notification message |
| data | JSONB | | Additional notification data |
| is_read | BOOLEAN | DEFAULT FALSE | Read status |
| read_at | TIMESTAMP | | Read timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |

**Notification Types**: `order_filled`, `order_failed`, `grid_completed`, `profit_lock`, `error`, `system`, `subscription`

**Indexes**:
- `idx_notifications_user_id` on `user_id`
- `idx_notifications_type` on `type`
- `idx_notifications_is_read` on `is_read`

**Relationships**:
- Many-to-One with `users`

---

### 2.12 Balances

**Table**: `balances`

**Description**: Exchange account balances.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique balance identifier |
| exchange_account_id | UUID | FK → exchange_accounts.id, NOT NULL, INDEX | Exchange account |
| currency | VARCHAR(10) | NOT NULL | Currency code |
| available | DECIMAL(20, 8) | NOT NULL | Available balance |
| locked | DECIMAL(20, 8) | DEFAULT 0 | Locked balance |
| total | DECIMAL(20, 8) | NOT NULL | Total balance |
| last_updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_balances_exchange_account_id` on `exchange_account_id`
- `uq_balances_exchange_account_currency` on `(exchange_account_id, currency)`

**Relationships**:
- Many-to-One with `exchange_accounts`

---

## 3. ENTITY RELATIONSHIP DIAGRAM (ERD)

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │◄──────────────┐
│ email           │               │
│ password_hash   │               │
│ subscription_tier│              │
│ referral_code   │               │
│ referred_by (FK)│               │
│ ...             │               │
└─────────────────┘               │
         │                        │
         │                        │
         │                        │
         ▼                        │
┌─────────────────┐               │
│exchange_accounts│               │
├─────────────────┤               │
│ id (PK)         │               │
│ user_id (FK)    │               │
│ exchange_name   │               │
│ api_key_encrypted│             │
│ ...             │               │
└─────────────────┘               │
         │                        │
         │                        │
         │                        │
         ▼                        │
┌─────────────────┐               │
│  trading_       │               │
│   instances     │               │
├─────────────────┤               │
│ id (PK)         │               │
│ user_id (FK)    │               │
│ exchange_account│               │
│   _id (FK)      │               │
│ strategy_id (FK)│               │
│ grid_profile_id │               │
│   (FK)          │               │
│ symbol          │               │
│ status          │               │
│ worker_id       │               │
│ memory_snapshot │               │
│ ...             │               │
└─────────────────┘               │
         │                        │
         │                        │
         │                        │
         ├────────────┬───────────┘
         │            │
         ▼            ▼
┌─────────────────┐ ┌─────────────┐
│     orders      │ │  positions  │
├─────────────────┤ ├─────────────┤
│ id (PK)         │ │ id (PK)     │
│ user_id (FK)    │ │ trading_    │
│ exchange_account│ │  instance_id│
│   _id (FK)      │ │   (FK)      │
│ trading_instance │ │ symbol      │
│   _id (FK)      │ │ side        │
│ symbol          │ │ quantity    │
│ side            │ │ ...         │
│ status          │ └─────────────┘
│ purpose         │
│ ...             │
└─────────────────┘

┌─────────────────┐
│  grid_profiles  │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ name            │
│ strategy_type   │
│ upper_price     │
│ lower_price     │
│ grid_count      │
│ ...             │
└─────────────────┘
         ▲
         │
         │
┌─────────────────┐
│   strategies    │
├─────────────────┤
│ id (PK)         │
│ name            │
│ type            │
│ description     │
│ ...             │
└─────────────────┘

┌─────────────────┐
│  subscriptions  │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │◄──────────────┘
│ tier            │
│ start_date      │
│ end_date        │
│ ...             │
└─────────────────┘

┌─────────────────┐
│   affiliates    │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │◄──────────────┘
│ commission_rate │
│ total_earnings  │
│ ...             │
└─────────────────┘

┌─────────────────┐
│  transactions   │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │◄──────────────┘
│ type            │
│ amount          │
│ currency        │
│ status          │
│ ...             │
└─────────────────┘

┌─────────────────┐
│ notifications   │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │◄──────────────┘
│ type            │
│ title           │
│ message         │
│ is_read         │
│ ...             │
└─────────────────┘

┌─────────────────┐
│    balances     │
├─────────────────┤
│ id (PK)         │
│ exchange_account│
│   _id (FK)      │◄──────────────┐
│ currency        │               │
│ available       │               │
│ locked          │               │
│ total           │               │
│ ...             │               │
└─────────────────┘               │
                                  │
┌─────────────────┐               │
│exchange_accounts│───────────────┘
└─────────────────┘
```

---

## 4. DATABASE MIGRATIONS

### 4.1 Migration Strategy

- Use **Alembic** for database migrations
- Generate migration scripts automatically with `alembic revision --autogenerate`
- Review all migrations before applying
- Never modify existing migrations
- Use transactional migrations (all-or-nothing)

### 4.2 Migration Commands

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# View migration history
alembic history

# View current version
alembic current
```

### 4.3 Migration Naming Convention

Use descriptive names in snake_case:
- `create_users_table`
- `add_exchange_accounts_table`
- `add_trading_instances_table`
- `add_orders_index_on_status`

---

## 5. SEED DATA

### 5.1 Seed Strategy

- Seed data for development and testing environments
- Use separate seed files for different environments
- Never seed production with test data
- Use Faker library for generating realistic test data

### 5.2 Seed Data Files

```
backend/database/seed/
├── dev/
│   ├── seed_users.py
│   ├── seed_exchanges.py
│   ├── seed_strategies.py
│   └── seed_all.py
├── test/
│   └── seed_test_data.py
└── prod/
    └── seed_initial_data.py
```

---

## 6. PERFORMANCE OPTIMIZATION

### 6.1 Indexing Strategy

**Primary Indexes**:
- All foreign keys
- Frequently queried fields (status, symbol, user_id)
- Unique constraints (email, referral_code)

**Composite Indexes**:
- `(user_id, status)` for filtering user's orders by status
- `(symbol, status)` for filtering orders by symbol and status
- `(exchange_account_id, currency)` for balance lookups

### 6.2 Query Optimization

**Use Eager Loading**:
```python
# Good - avoid N+1 query
orders = db.query(Order).options(
    joinedload(Order.user),
    joinedload(Order.exchange_account)
).all()

# Bad - N+1 query
orders = db.query(Order).all()
for order in orders:
    print(order.user.email)  # Triggers separate query
```

**Use Pagination**:
```python
# Good - paginated query
orders = db.query(Order).filter(
    Order.user_id == user_id
).limit(50).offset(0).all()

# Bad - loads all records
orders = db.query(Order).filter(
    Order.user_id == user_id
).all()
```

### 6.3 Connection Pooling

- Use SQLAlchemy connection pooling
- Configure pool size based on expected load
- Monitor pool usage in production

---

## 7. BACKUP & RECOVERY

### 7.1 Backup Strategy

- **Daily full backups** at midnight
- **Hourly incremental backups** during trading hours
- **Retention policy**: 30 days for daily backups, 7 days for hourly backups
- **Off-site storage**: Store backups in separate region

### 7.2 Backup Commands

```bash
# Full backup
pg_dump -U postgres -d utos -f backup_$(date +%Y%m%d).sql

# Incremental backup (using WAL archiving)
# Configure PostgreSQL for WAL archiving in postgresql.conf
```

### 7.3 Recovery Procedure

1. Stop application
2. Restore from latest backup
3. Apply WAL logs to bring to current state
4. Verify data integrity
5. Restart application

---

## 8. SECURITY CONSIDERATIONS

### 8.1 Encryption

- **API Keys**: Encrypt using AES-256 before storing
- **Passwords**: Hash using bcrypt with salt
- **Sensitive Data**: Use PostgreSQL encryption extension if needed

### 8.2 Access Control

- Use database roles for access control
- Application user has limited privileges
- Separate read and write users if needed

### 8.3 Audit Logging

- Log all DDL operations
- Log sensitive data access
- Regular audit of access logs

---

## 9. MONITORING

### 9.1 Key Metrics

- Database connection pool usage
- Query execution time
- Slow query log
- Table size growth
- Index usage statistics

### 9.2 Alerts

- High connection pool usage (>80%)
- Slow queries (>1 second)
- Database replication lag
- Disk space usage (>80%)

---

## 10. PROCESS MEMORY PERSISTENCE

### 10.1 Philosophy

Database is the **source of truth for recovery**, but runtime state lives in **ProcessMemory**.

Each Trading Instance has a worker that owns an in-memory snapshot. The database is updated asynchronously:

- On state transitions (`created` → `ready` → `running` → `paused` → `stopped` → `error`)
- On order/position changes (debounced, every 1-5 seconds)
- On worker shutdown (final snapshot)
- On explicit `sync_instance_state()` call

### 10.2 `memory_snapshot` Format

```json
{
  "instance_id": "uuid",
  "version": 42,
  "status": "running",
  "grid_state": { ... },
  "positions": [...],
  "open_orders": [...],
  "balances": [...],
  "profit_lock_state": { ... },
  "portfolio_lock_state": { ... },
  "market_data": { "BTCUSDT": { ... } },
  "last_synced_at": "2026-07-09T10:00:00Z"
}
```

### 10.3 Recovery

On restart, workers reload the latest `memory_snapshot` from the database, then reconcile with the exchange. This minimizes startup time for 100,000+ instances.

---

## 11. SCALABILITY FOR 100,000+ TRADING INSTANCES

### 11.1 Database Strategy

| Technique | Purpose |
|-----------|---------|
| Connection Pooling | PgBouncer with transaction pooling |
| Read Replicas | Portfolio/history queries on replicas |
| Partitioning | Partition `orders` by `created_at` (monthly) and `trading_instance_id` hash |
| Bulk Writes | Batch memory snapshot updates |
| Async Persistence | Workers persist snapshots to DB in background |
| Hot Indexes | Index on `(user_id, status)`, `(worker_id, status)`, `(symbol, status)` |

### 11.2 Write Patterns

- **High frequency**: `memory_snapshot` updates every 1-5 seconds per instance
- **Medium frequency**: Order fills, position updates
- **Low frequency**: User profile changes, grid profile updates

### 11.3 Scaling Targets

| Metric | Target |
|--------|--------|
| Concurrent Trading Instances | 100,000+ |
| Orders per second | 10,000+ |
| Memory snapshots per second | 20,000+ (batched) |
| Database connections | 500-1000 via PgBouncer |
| Read replicas | 2-3 replicas |

---

## 12. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial database design |
| 2026-07-09 | 2.0.0 | Architecture revision: Trading Instance, Process Memory, TP/ProfitLock/PortfolioLock separation, READY state, scalability targets |
