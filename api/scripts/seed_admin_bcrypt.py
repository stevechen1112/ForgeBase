"""One-time admin seed using bcrypt directly (bypasses passlib compat issue)."""
import asyncio
import uuid
import bcrypt
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings  # noqa: E402


async def seed() -> None:
    import asyncpg

    conn = await asyncpg.connect(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    )
    email = "admin@forgebase.com"
    password = "ForgeBase2026!"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc)

    existing = await conn.fetchrow("SELECT id FROM users WHERE email=$1", email)
    if existing:
        await conn.execute(
            "UPDATE users SET hashed_password=$1, is_active=true, role='admin', full_name='System Admin' WHERE email=$2",
            hashed, email,
        )
        print(f"✓ Admin user updated: {email}")
    else:
        await conn.execute(
            "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, 'admin', true, $5, $6)",
            uuid.uuid4(), email, hashed, "System Admin", now, now,
        )
        print(f"✓ Admin user created: {email}")

    await conn.close()


asyncio.run(seed())
