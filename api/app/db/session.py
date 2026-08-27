from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

_engine_options: dict[str, Any] = {
    "echo": settings.APP_ENV == "development",
    "pool_pre_ping": True,
}
if settings.DATABASE_NULL_POOL:
    _engine_options["poolclass"] = NullPool
else:
    _engine_options.update({"pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.DATABASE_URL, **_engine_options)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_session_ctx() -> AsyncSession:
    """Async context manager for use in background tasks / services."""
    async with AsyncSessionLocal() as session:
        yield session
