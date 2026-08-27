"""Create or repair a tenant-scoped admin without exposing its password in argv.

Usage:
    printf '%s\n' "$PASSWORD" | python -m scripts.provision_tenant_user \
        --email admin@example.com --tenant default-tenant --role owner
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlmodel import select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User, UserRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--tenant", required=True, help="Tenant slug")
    parser.add_argument("--full-name", default="Tenant Owner")
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.owner.value,
    )
    return parser.parse_args()


async def provision(args: argparse.Namespace, password: str) -> dict[str, str | bool]:
    async with AsyncSessionLocal() as session:
        tenant = (
            await session.exec(select(Tenant).where(Tenant.slug == args.tenant))
        ).one_or_none()
        if tenant is None:
            raise RuntimeError(f"Tenant not found: {args.tenant}")

        email = args.email.strip().lower()
        user = (
            await session.exec(select(User).where(User.email == email))
        ).one_or_none()
        created = user is None
        if user is None:
            user = User(email=email, hashed_password="")

        user.full_name = args.full_name.strip()
        user.hashed_password = get_password_hash(password)
        user.role = args.role
        user.is_active = True
        user.is_superuser = False
        user.tenant_id = tenant.id
        session.add(user)
        await session.commit()

        return {
            "email": user.email,
            "tenant": tenant.slug,
            "role": user.role,
            "created": created,
        }


async def main() -> None:
    args = parse_args()
    password = sys.stdin.readline().rstrip("\r\n")
    if len(password) < 16:
        raise RuntimeError("Password must contain at least 16 characters")
    result = await provision(args, password)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
