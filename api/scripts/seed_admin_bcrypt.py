"""One-time admin seed using bcrypt directly (bypasses passlib compat issue)."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import bcrypt
from dotenv import load_dotenv

load_dotenv()

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.config import settings  # noqa: E402


async def seed() -> None:
    import asyncpg

    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
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

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT id, tenant_id, is_superuser FROM users WHERE email=$1 FOR UPDATE",
            email,
        )
        if existing and is_superuser and existing["tenant_id"] is not None:
            raise RuntimeError(
                "Refusing to grant platform superuser access to a tenant-owned account"
            )
        if existing and existing["is_superuser"] and not is_superuser:
            raise RuntimeError(
                "Refusing to demote a platform superuser through the bootstrap script"
            )

        if existing:
            await conn.execute(
                "UPDATE users SET hashed_password=$1, is_active=true, role='admin', full_name='System Admin', "
                "is_superuser=$2, updated_at=$3 WHERE email=$4",
                hashed, is_superuser, now, email,
            )
            action = "updated"
        else:
            await conn.execute(
                "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, is_superuser, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, 'admin', true, $5, $6, $7)",
                uuid.uuid4(), email, hashed, "System Admin", is_superuser, now, now,
            )
            action = "created"

        verified = await conn.fetchrow(
            "SELECT tenant_id, is_active, is_superuser FROM users WHERE email=$1",
            email,
        )
        if not verified or not verified["is_active"]:
            raise RuntimeError("Admin bootstrap verification failed")
        if bool(verified["is_superuser"]) != is_superuser:
            raise RuntimeError("Admin bootstrap role verification failed")
        if is_superuser and verified["tenant_id"] is not None:
            raise RuntimeError("Platform superuser must not belong to a tenant")

    print(f"✓ Admin user {action}: {email}")
    if is_superuser:
        print("✓ Verified platform boundary: tenant_id=NULL, is_superuser=true")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
