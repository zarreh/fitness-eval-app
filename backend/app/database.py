"""Async SQLAlchemy engine, session factory, and FastAPI dependency.

Import this module (and ``db_models``) before calling ``create_tables()``
so that all ORM models are registered with ``Base.metadata``.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATA_DIR = Path(__file__).parent.parent / "data"
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/fitness.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""

    pass


async def create_tables() -> None:
    """Create all database tables that do not yet exist.

    Must be called after all ORM models have been imported so that
    ``Base.metadata`` contains every table definition.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a scoped async database session.

    Usage::

        async def my_endpoint(db: AsyncSession = Depends(get_db)) -> ...:
    """
    async with AsyncSessionLocal() as session:
        yield session
