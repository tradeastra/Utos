"""Create all tables per DATABASE.md

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Drop old users table (Sprint 1 version) to rebuild with full schema ---
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")

    # --- Enum types ---
    user_role = sa.Enum("user", "admin", name="user_role")
    subscription_tier = sa.Enum(
        "free", "basic", "pro", "enterprise", name="subscription_tier"
    )
    exchange_name = sa.Enum(
        "binance", "bybit", "okx", "kraken", "kucoin", name="exchange_name"
    )
    trading_instance_status = sa.Enum(
        "created",
        "ready",
        "running",
        "paused",
        "stopping",
        "stopped",
        "error",
        "recovering",
        "recovered",
        name="trading_instance_status",
    )
    strategy_type = sa.Enum(
        "smart_grid",
        "adaptive_grid",
        "infinity_grid",
        "dca",
        name="strategy_type",
    )
    grid_strategy_type = sa.Enum(
        "smart_grid",
        "adaptive_grid",
        "infinity_grid",
        "dca",
        name="grid_strategy_type",
    )
    order_side = sa.Enum("buy", "sell", name="order_side")
    order_type = sa.Enum("limit", "market", "stop_limit", name="order_type")
    order_status = sa.Enum(
        "pending",
        "open",
        "partially_filled",
        "filled",
        "cancelled",
        "rejected",
        "expired",
        name="order_status",
    )
    position_side = sa.Enum("long", "short", name="position_side")
    transaction_type = sa.Enum(
        "deposit",
        "withdrawal",
        "fee",
        "subscription",
        "refund",
        name="transaction_type",
    )
    notification_type = sa.Enum(
        "order_filled",
        "order_failed",
        "grid_completed",
        "profit_lock",
        "error",
        "system",
        "subscription",
        name="notification_type",
    )
    subscription_tier_enum = sa.Enum(
        "free",
        "basic",
        "pro",
        "enterprise",
        name="subscription_tier_enum",
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("role", user_role, server_default="user", nullable=False),
        sa.Column(
            "subscription_tier",
            subscription_tier,
            server_default="free",
            nullable=False,
        ),
        sa.Column("referral_code", sa.String(20), nullable=True),
        sa.Column("referred_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("referral_code", name="uq_users_referral_code"),
        sa.ForeignKeyConstraint(["referred_by"], ["users.id"]),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_referral_code", "users", ["referral_code"])
    op.create_index("idx_users_subscription_tier", "users", ["subscription_tier"])

    # --- strategies ---
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", strategy_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_investment", sa.Numeric(20, 8), nullable=False),
        sa.Column("max_investment", sa.Numeric(20, 8), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_strategies_name"),
    )

    # --- grid_profiles ---
    op.create_table(
        "grid_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("strategy_type", grid_strategy_type, nullable=False),
        sa.Column("upper_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("lower_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("grid_count", sa.Integer(), nullable=False),
        sa.Column("grid_spacing", sa.Numeric(20, 8), nullable=True),
        sa.Column("investment_per_grid", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "take_profit_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("take_profit_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "stop_loss_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("stop_loss_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_grid_profiles_user_id", "grid_profiles", ["user_id"])

    # --- exchange_accounts ---
    op.create_table(
        "exchange_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_name", exchange_name, nullable=False),
        sa.Column("account_name", sa.String(100), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("is_testnet", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "connection_status",
            sa.String(20),
            server_default="disconnected",
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_exchange_accounts_user_id", "exchange_accounts", ["user_id"])
    op.create_index(
        "idx_exchange_accounts_exchange_name", "exchange_accounts", ["exchange_name"]
    )

    # --- trading_instances ---
    op.create_table(
        "trading_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grid_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column(
            "status", trading_instance_status, server_default="created", nullable=False
        ),
        sa.Column("start_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("total_investment", sa.Numeric(20, 8), nullable=False),
        sa.Column("base_currency", sa.String(10), nullable=False),
        sa.Column("quote_currency", sa.String(10), nullable=False),
        sa.Column(
            "profit_lock_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("profit_lock_trigger_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("profit_lock_trail_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "portfolio_lock_enabled",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("portfolio_lock_trigger_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("portfolio_lock_trail_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("memory_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("memory_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["exchange_account_id"], ["exchange_accounts.id"]),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"]),
        sa.ForeignKeyConstraint(["grid_profile_id"], ["grid_profiles.id"]),
    )
    op.create_index("idx_trading_instances_user_id", "trading_instances", ["user_id"])
    op.create_index(
        "idx_trading_instances_exchange_account_id",
        "trading_instances",
        ["exchange_account_id"],
    )
    op.create_index(
        "idx_trading_instances_strategy_id", "trading_instances", ["strategy_id"]
    )
    op.create_index("idx_trading_instances_status", "trading_instances", ["status"])
    op.create_index("idx_trading_instances_symbol", "trading_instances", ["symbol"])

    # --- positions ---
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", position_side, nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "unrealized_pnl", sa.Numeric(20, 8), server_default="0", nullable=False
        ),
        sa.Column(
            "realized_pnl", sa.Numeric(20, 8), server_default="0", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["trading_instance_id"], ["trading_instances.id"]),
    )
    op.create_index(
        "idx_positions_trading_instance_id", "positions", ["trading_instance_id"]
    )
    op.create_index("idx_positions_symbol", "positions", ["symbol"])

    # --- orders ---
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_instance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exchange_order_id", sa.String(100), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", order_side, nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=True),
        sa.Column("stop_price", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "filled_quantity", sa.Numeric(20, 8), server_default="0", nullable=False
        ),
        sa.Column("average_fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("status", order_status, server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("grid_level", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.String(30), server_default="grid", nullable=False),
        sa.Column(
            "is_profit_lock", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["exchange_account_id"], ["exchange_accounts.id"]),
        sa.ForeignKeyConstraint(["trading_instance_id"], ["trading_instances.id"]),
    )
    op.create_index("idx_orders_user_id", "orders", ["user_id"])
    op.create_index("idx_orders_exchange_account_id", "orders", ["exchange_account_id"])
    op.create_index("idx_orders_trading_instance_id", "orders", ["trading_instance_id"])
    op.create_index("idx_orders_exchange_order_id", "orders", ["exchange_order_id"])
    op.create_index("idx_orders_symbol", "orders", ["symbol"])
    op.create_index("idx_orders_status", "orders", ["status"])

    # --- transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_transactions_user_id", "transactions", ["user_id"])
    op.create_index("idx_transactions_type", "transactions", ["type"])
    op.create_index("idx_transactions_status", "transactions", ["status"])

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tier", subscription_tier_enum, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("auto_renew", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
    )
    op.create_index("idx_subscriptions_tier", "subscriptions", ["tier"])

    # --- affiliates ---
    op.create_table(
        "affiliates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "total_earnings", sa.Numeric(20, 8), server_default="0", nullable=False
        ),
        sa.Column("total_referrals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", name="uq_affiliates_user_id"),
    )

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_notifications_user_id", "notifications", ["user_id"])
    op.create_index("idx_notifications_type", "notifications", ["type"])
    op.create_index("idx_notifications_is_read", "notifications", ["is_read"])

    # --- balances ---
    op.create_table(
        "balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("available", sa.Numeric(20, 8), nullable=False),
        sa.Column("locked", sa.Numeric(20, 8), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["exchange_account_id"], ["exchange_accounts.id"]),
        sa.UniqueConstraint(
            "exchange_account_id",
            "currency",
            name="uq_balances_exchange_account_currency",
        ),
    )
    op.create_index(
        "idx_balances_exchange_account_id", "balances", ["exchange_account_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_balances_exchange_account_id", table_name="balances")
    op.drop_table("balances")

    op.drop_index("idx_notifications_is_read", table_name="notifications")
    op.drop_index("idx_notifications_type", table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_table("affiliates")

    op.drop_index("idx_subscriptions_tier", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("idx_transactions_status", table_name="transactions")
    op.drop_index("idx_transactions_type", table_name="transactions")
    op.drop_index("idx_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("idx_orders_status", table_name="orders")
    op.drop_index("idx_orders_symbol", table_name="orders")
    op.drop_index("idx_orders_exchange_order_id", table_name="orders")
    op.drop_index("idx_orders_trading_instance_id", table_name="orders")
    op.drop_index("idx_orders_exchange_account_id", table_name="orders")
    op.drop_index("idx_orders_user_id", table_name="orders")
    op.drop_table("orders")

    op.drop_index("idx_positions_symbol", table_name="positions")
    op.drop_index("idx_positions_trading_instance_id", table_name="positions")
    op.drop_table("positions")

    op.drop_index("idx_trading_instances_symbol", table_name="trading_instances")
    op.drop_index("idx_trading_instances_status", table_name="trading_instances")
    op.drop_index("idx_trading_instances_strategy_id", table_name="trading_instances")
    op.drop_index(
        "idx_trading_instances_exchange_account_id", table_name="trading_instances"
    )
    op.drop_index("idx_trading_instances_user_id", table_name="trading_instances")
    op.drop_table("trading_instances")

    op.drop_index("idx_exchange_accounts_exchange_name", table_name="exchange_accounts")
    op.drop_index("idx_exchange_accounts_user_id", table_name="exchange_accounts")
    op.drop_table("exchange_accounts")

    op.drop_index("idx_grid_profiles_user_id", table_name="grid_profiles")
    op.drop_table("grid_profiles")

    op.drop_table("strategies")

    op.drop_index("idx_users_subscription_tier", table_name="users")
    op.drop_index("idx_users_referral_code", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")

    # Drop enum types
    for enum_name in [
        "notification_type",
        "transaction_type",
        "position_side",
        "order_status",
        "order_type",
        "order_side",
        "grid_strategy_type",
        "strategy_type",
        "trading_instance_status",
        "exchange_name",
        "subscription_tier_enum",
        "subscription_tier",
        "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
