import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# 讓 alembic 找到 app 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# 載入所有 models 以讓 autogenerate 能偵測（必須在 target_metadata 之前）
import app.models  # noqa: F401 — side-effect import registers all tables
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# 用環境變數覆蓋 alembic.ini 的 URL（同步版本給 alembic offline 用）
db_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
config.set_main_option("sqlalchemy.url", db_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Historical migrations use PostgreSQL TEXT/timestamptz while SQLModel
        # reports equivalent AutoString/DateTime abstractions. Treating those
        # representational differences as schema changes hides real table,
        # column, index and constraint drift in hundreds of false positives.
        # Type changes remain explicit, reviewed migrations rather than an
        # autogenerate gate.
        compare_type=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with async_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await async_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
