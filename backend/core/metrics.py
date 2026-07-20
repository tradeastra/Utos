"""
Prometheus metrics for UTOS Trading Engine.

All metrics use the `utos_` prefix following Prometheus naming conventions.
Metrics are organized by domain: trading, recovery, market, scheduler,
notification, and API.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# ── Info ──────────────────────────────────────
utos_info = Info(
    "utos",
    "UTOS Trading Engine application info",
)

# ── Trading Metrics ───────────────────────────
utos_trading_instances_active = Gauge(
    "utos_trading_instances_active",
    "Number of active trading instances",
    ["status"],
)

utos_orders_total = Counter(
    "utos_orders_total",
    "Total orders placed",
    ["side", "status"],
)

utos_orders_failed_total = Counter(
    "utos_orders_failed_total",
    "Total failed orders",
    ["reason"],
)

utos_order_duration_ms = Histogram(
    "utos_order_duration_ms",
    "Order processing duration in milliseconds",
    ["side"],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)

# ── Recovery Metrics ──────────────────────────
utos_recovery_total = Counter(
    "utos_recovery_total",
    "Total recovery operations",
    ["layer", "result"],
)

utos_recovery_duration_ms = Histogram(
    "utos_recovery_duration_ms",
    "Recovery operation duration in milliseconds",
    ["layer"],
    buckets=[100, 500, 1000, 2500, 5000, 10000, 30000, 60000],
)

# ── Market Metrics ────────────────────────────
utos_ws_connections = Gauge(
    "utos_ws_connections",
    "Active WebSocket connections",
)

utos_ws_reconnect_total = Counter(
    "utos_ws_reconnect_total",
    "Total WebSocket reconnections",
)

utos_market_latency_ms = Histogram(
    "utos_market_latency_ms",
    "Market data latency in milliseconds",
    ["symbol"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

# ── Scheduler Metrics ─────────────────────────
utos_workers_active = Gauge(
    "utos_workers_active",
    "Number of active workers",
)

utos_retry_queue_size = Gauge(
    "utos_retry_queue_size",
    "Retry queue size",
)

utos_dlq_size = Gauge(
    "utos_dlq_size",
    "Dead letter queue size",
)

# ── Notification Metrics ──────────────────────
utos_notification_total = Counter(
    "utos_notification_total",
    "Total notifications sent",
    ["channel", "result"],
)

utos_notification_queue_length = Gauge(
    "utos_notification_queue_length",
    "Notification queue length",
)

# ── API Metrics ───────────────────────────────
utos_http_requests_total = Counter(
    "utos_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

utos_http_request_duration_ms = Histogram(
    "utos_http_request_duration_ms",
    "HTTP request duration in milliseconds",
    ["method", "endpoint"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

# ── Infrastructure Metrics ────────────────────
utos_db_connections_active = Gauge(
    "utos_db_connections_active",
    "Active database connections",
)

utos_redis_connections_active = Gauge(
    "utos_redis_connections_active",
    "Active Redis connections",
)

# ── Business Metrics ──────────────────────────
utos_profit_total = Gauge(
    "utos_profit_total",
    "Total realized profit in USD",
)

utos_realized_profit = Gauge(
    "utos_realized_profit",
    "Realized profit in USD",
)

utos_unrealized_profit = Gauge(
    "utos_unrealized_profit",
    "Unrealized profit in USD",
)

utos_grid_cycles_total = Counter(
    "utos_grid_cycles_total",
    "Total grid cycles completed",
)

utos_profit_lock_triggered_total = Counter(
    "utos_profit_lock_triggered_total",
    "Total profit lock triggers",
)

utos_trading_process_started_total = Counter(
    "utos_trading_process_started_total",
    "Total trading processes started",
)

utos_trading_process_stopped_total = Counter(
    "utos_trading_process_stopped_total",
    "Total trading processes stopped",
)

# ── Database Reliability Metrics ──────────────
utos_db_backup_age_hours = Gauge(
    "utos_db_backup_age_hours",
    "Age of latest database backup in hours",
)

utos_db_backup_total = Counter(
    "utos_db_backup_total",
    "Total database backups created",
    ["status"],
)

utos_db_backup_size_bytes = Gauge(
    "utos_db_backup_size_bytes",
    "Size of latest database backup in bytes",
)

utos_db_replication_lag_seconds = Gauge(
    "utos_db_replication_lag_seconds",
    "Database replication lag in seconds",
)

utos_db_slow_query_count = Gauge(
    "utos_db_slow_query_count",
    "Number of slow queries detected",
)

utos_db_migration_version = Gauge(
    "utos_db_migration_version",
    "Current Alembic migration version (numeric hash)",
)

utos_db_pool_size = Gauge(
    "utos_db_pool_size",
    "Current database connection pool size",
)

utos_db_pool_checked_out = Gauge(
    "utos_db_pool_checked_out",
    "Checked out database connections",
)


def init_metrics() -> None:
    """Initialize metrics with default values."""
    utos_info.info(
        {
            "version": "1.0.0",
            "sprint": "16B",
            "env": "production",
        }
    )
    utos_trading_instances_active.labels(status="running").set(0)
    utos_trading_instances_active.labels(status="paused").set(0)
    utos_trading_instances_active.labels(status="stopped").set(0)
    utos_ws_connections.set(0)
    utos_workers_active.set(0)
    utos_retry_queue_size.set(0)
    utos_dlq_size.set(0)
    utos_notification_queue_length.set(0)
    utos_db_connections_active.set(0)
    utos_redis_connections_active.set(0)
    utos_db_backup_age_hours.set(-1)
    utos_db_backup_size_bytes.set(0)
    utos_db_replication_lag_seconds.set(0)
    utos_db_slow_query_count.set(0)
    utos_db_migration_version.set(0)
    utos_db_pool_size.set(0)
    utos_db_pool_checked_out.set(0)


def get_metrics() -> bytes:
    """Return Prometheus-formatted metrics."""
    return generate_latest()


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST
