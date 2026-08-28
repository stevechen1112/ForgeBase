"""Remove the exact one-run Platform Admin browser verifier account."""

from __future__ import annotations

import asyncio
import os
import re

from app.core.config import settings


def expected_ephemeral_email(run_id: str, run_attempt: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("Invalid workflow run id")
    if not re.fullmatch(r"[1-9][0-9]*", run_attempt):
        raise ValueError("Invalid workflow run attempt")
    return f"production-browser-{run_id}-{run_attempt}@forgebase.com"


async def remove() -> None:
    import asyncpg

    email = os.environ.get("EPHEMERAL_OPERATOR_EMAIL", "").strip().lower()
    expected = expected_ephemeral_email(
        os.environ.get("EPHEMERAL_OPERATOR_RUN_ID", ""),
        os.environ.get("EPHEMERAL_OPERATOR_RUN_ATTEMPT", ""),
    )
    if email != expected:
        raise RuntimeError("Refusing to remove an unexpected platform operator")

    connection = await asyncpg.connect(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    )
    try:
        async with connection.transaction():
            row = await connection.fetchrow(
                """
                SELECT id, tenant_id, is_superuser, full_name
                FROM users
                WHERE email=$1
                FOR UPDATE
                """,
                email,
            )
            if not row:
                print("Ephemeral platform operator was already absent")
                return
            if (
                row["tenant_id"] is not None
                or row["is_superuser"] is not True
                or row["full_name"] != "System Admin"
            ):
                raise RuntimeError(
                    "Refusing to remove an account outside the verifier boundary"
                )
            await connection.execute("DELETE FROM users WHERE id=$1", row["id"])
            if await connection.fetchval("SELECT 1 FROM users WHERE id=$1", row["id"]):
                raise RuntimeError(
                    "Ephemeral platform operator removal was not durable"
                )
        print("Ephemeral platform operator removed")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(remove())
