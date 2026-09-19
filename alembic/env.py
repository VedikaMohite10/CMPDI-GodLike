"""Async-compatible Alembic env.py.

Reads the database URL from app.config (pydantic-settings → .env) rather than
from alembic.ini so there is one canonical source of configuration.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so `app` is importable
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402

# Import all models so Alembic's autogenerate can see them
import app.models  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().DATABASE_URL


# ---------------------------------------------------------------------------
# Offline migrations (generates SQL without a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (runs against a live async DB connection)
# ---------------------------------------------------------------------------
def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
