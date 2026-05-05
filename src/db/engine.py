from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings


def get_async_engine(database_url: str | None = None):
    """Create async SQLAlchemy engine."""
    url = database_url or get_settings().database_url
    return create_async_engine(url, echo=get_settings().debug)


def get_sync_engine(database_url: str | None = None):
    """Create sync SQLAlchemy engine (for Alembic and simple CLI use)."""
    url = database_url or get_settings().database_url_sync
    return create_engine(url, echo=get_settings().debug)


def get_async_session_factory(engine=None) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    engine = engine or get_async_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


from contextlib import asynccontextmanager
from typing import AsyncGenerator


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Convenience context manager that yields an async session."""
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()
