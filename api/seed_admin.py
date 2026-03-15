import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings
from app.core.security import get_password_hash
import asyncpg
import uuid
from datetime import datetime, timezone


async def seed():
    conn = await asyncpg.connect(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    )
    email = "admin@forgebase.com"
    existing = await conn.fetchrow("SELECT id FROM users WHERE email=$1", email)
    hashed = get_password_hash("ForgeBase2026!")
    now = datetime.now(timezone.utc)

    if existing:
        await conn.execute(
            "UPDATE users SET hashed_password=$1, is_active=true, role='admin', full_name='System Admin' WHERE email=$2",
            hashed, email,
        )
        print("Admin user updated")
    else:
        await conn.execute(
            "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, 'admin', true, $5, $6)",
            uuid.uuid4(), email, hashed, "System Admin", now, now,
        )
        print("Admin user created")

    await conn.close()


asyncio.run(seed())
