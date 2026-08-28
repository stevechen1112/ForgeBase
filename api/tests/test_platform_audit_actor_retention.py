import uuid

import pytest
from app.core.security import get_password_hash
from app.models.platform_audit_log import PlatformAuditLog
from app.models.user import User
from sqlalchemy import text

from tests.conftest import _make_engine, requires_db


@requires_db
@pytest.mark.asyncio
async def test_audit_actor_snapshot_survives_ephemeral_operator_removal() -> None:
    engine, factory = _make_engine()
    audit_id = uuid.uuid4()
    user_id = uuid.uuid4()
    email = f"production-data-quality-{uuid.uuid4().hex[:12]}@forgebase.com"
    try:
        async with factory() as session:
            user = User(
                id=user_id,
                tenant_id=None,
                email=email,
                full_name="System Admin",
                hashed_password=get_password_hash("test-password-only"),
                role="admin",
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.flush()
            session.add(
                PlatformAuditLog(
                    id=audit_id,
                    actor_user_id=user_id,
                    actor_email=email,
                    action="rfq.classified",
                    target_type="rfq",
                    target_id=str(uuid.uuid4()),
                    changes_json='{"is_test_data":{"from":false,"to":true}}',
                )
            )
            await session.commit()
            await session.exec(text("DELETE FROM users WHERE id = :id"), params={"id": str(user_id)})
            await session.commit()
            row = (
                await session.exec(
                    text(
                        "SELECT actor_user_id, actor_email FROM platform_audit_logs WHERE id = :id"
                    ),
                    params={"id": str(audit_id)},
                )
            ).mappings().one()
            assert row["actor_user_id"] is None
            assert row["actor_email"] == email
            await session.exec(
                text("DELETE FROM platform_audit_logs WHERE id = :id"),
                params={"id": str(audit_id)},
            )
            await session.commit()
    finally:
        await engine.dispose()
