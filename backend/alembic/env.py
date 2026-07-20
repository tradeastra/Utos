"""Alembic environment — async SQLAlchemy with asyncpg."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.config import get_database_url
from database.base import Base
from models import (  # noqa: F401 — ensure all models are registered
    Affiliate,
    Balance,
    ExchangeAccount,
    GridProfile,
    Notification,
    Order,
    Position,
    Strategy,
    Subscription,
    TradingInstance,
    Transaction,
    User,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(get_database_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
