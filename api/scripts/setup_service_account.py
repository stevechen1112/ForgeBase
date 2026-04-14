"""Create a ContentFlow service account user in ForgeBase."""
import asyncio
import os
import uuid
from datetime import datetime, timezone

import asyncpg
import bcrypt


async def main():
    db_url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    conn = await asyncpg.connect(db_url)

    # 0. Show users table structure
    cols = await conn.fetch(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"
    )
    print("=== USERS TABLE ===")
    for c in cols:
        print(f"  {c['column_name']:25s} {c['data_type']:20s} nullable={c['is_nullable']}")

    # 1. List existing tenants
    tenants = await conn.fetch("SELECT id, name, plan FROM tenants LIMIT 10")
    print("\n=== TENANTS ===")
    for t in tenants:
        print(f"  id={t['id']}  name={t['name']}  plan={t['plan']}")
    if not tenants:
        print("  (no tenants found, creating default)")
        tenant_id = uuid.uuid4()
        await conn.execute(
            "INSERT INTO tenants (id, name, plan, created_at, updated_at) VALUES ($1, $2, $3, $4, $5)",
            tenant_id, "ContentFlow Publisher", "pro", datetime.now(timezone.utc), datetime.now(timezone.utc),
        )
        print(f"  Created tenant: {tenant_id}")
    else:
        tenant_id = tenants[0]["id"]
        print(f"  Using first tenant: {tenant_id}")

    # 2. Check if service account already exists
    sa_email = "contentflow-sa@service.internal"
    existing = await conn.fetchrow(
        "SELECT id, email, role, tenant_id FROM users WHERE email = $1", sa_email
    )
    if existing:
        print(f"\n=== SERVICE ACCOUNT EXISTS ===")
        print(f"  id={existing['id']}  email={existing['email']}  role={existing['role']}")
        user_id = existing["id"]
    else:
        # 3. Create service account user
        user_id = uuid.uuid4()
        hashed_pw = bcrypt.hashpw(uuid.uuid4().hex[:20].encode(), bcrypt.gensalt()).decode()
        now = datetime.now(timezone.utc)
        await conn.execute(
            "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, tenant_id, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            user_id, sa_email, hashed_pw,
            "ContentFlow Service Account", "marketing_manager", True, tenant_id, now, now,
        )
        print(f"\n=== SERVICE ACCOUNT CREATED ===")
        print(f"  id={user_id}")
        print(f"  email={sa_email}")
        print(f"  role=marketing_manager")
        print(f"  tenant_id={tenant_id}")

    # 4. Output the user_id for token mapping
    print(f"\n=== TOKEN CONFIG ===")
    print(f"USER_ID={user_id}")

    await conn.close()


asyncio.run(main())
