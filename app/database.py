"""Async SQLAlchemy engine + session factory.

All database interactions go through the `get_db` dependency.
Direct access to `engine` is only needed for Alembic migrations.
"""
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # set DEBUG=true in .env to log all SQL
    pool_pre_ping=True,   # detect stale connections
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models.

    AsyncAttrs allows lazy-loading relationships using `await` syntax.
    """
    pass


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields a transactional database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
