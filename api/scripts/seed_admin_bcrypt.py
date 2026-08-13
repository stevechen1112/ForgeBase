"""One-time admin seed using bcrypt directly (bypasses passlib compat issue)."""
import asyncio
import os
import uuid
from datetime import datetime, timezone
import bcrypt
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings  # noqa: E402


async def seed() -> None:
    import asyncpg

    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD are required")
    if len(password) < 16:
        raise RuntimeError("ADMIN_PASSWORD must be at least 16 characters")
    is_superuser = os.getenv("ADMIN_IS_SUPERUSER", "false").lower() in {"1", "true", "yes"}
    conn = await asyncpg.connect(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    )
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc)

    existing = await conn.fetchrow("SELECT id FROM users WHERE email=$1", email)
    if existing:
        await conn.execute(
            "UPDATE users SET hashed_password=$1, is_active=true, role='admin', full_name='System Admin', "
            "is_superuser=$2, updated_at=$3 WHERE email=$4",
            hashed, is_superuser, now, email,
        )
        print(f"✓ Admin user updated: {email}")
    else:
        await conn.execute(
            "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, 'admin', true, $5, $6, $7)",
            uuid.uuid4(), email, hashed, "System Admin", is_superuser, now, now,
        )
        print(f"✓ Admin user created: {email}")

    await conn.close()


asyncio.run(seed())
