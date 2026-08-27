"""Controlled managed-delivery application flow."""

import uuid

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_superuser() -> tuple[uuid.UUID, str]:
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            user = User(
                tenant_id=None,
                email=f"adoption-admin-{uuid.uuid4().hex[:10]}@example.com",
                full_name="Adoption Operator",
                hashed_password=get_password_hash("testpass"),
                role="admin",
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id, create_access_token(str(user.id))
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_managed_delivery_application_is_not_a_tenant_or_sales_lead(http_client, monkeypatch) -> None:
    """A public application remains in the platform review queue until a human acts."""
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "RFQ_BOT_CHALLENGE_REQUIRED", False)
    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", "")
    marker = uuid.uuid4().hex[:10]
    operator_id, token = await _create_superuser()
    try:
        response = await http_client.post(
            "/api/v1/forms/adoption",
            json={
                "company_name": f"Test Forge {marker}",
                "website_url": "https://example.test",
                "contact_name": "Test Contact",
                "work_email": f"managed-{marker}@example.com",
                "industry": "Industrial tools",
                "current_situation": "replace_site",
                "requested_scope": "We need a managed site with a structured product catalogue and RFQ workflow.",
                "consent": True,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "received"
        assert "no account or trial" in response.json()["message"]

        listed = await http_client.get(
            f"/api/v1/admin/adoption-applications?search={marker}",
            headers=_auth(token),
        )
        assert listed.status_code == 200, listed.text
        assert listed.json()["meta"]["total"] == 1
        application = listed.json()["data"][0]
        assert application["status"] == "new"
        assert application["is_test_data"] is False

        updated = await http_client.patch(
            f"/api/v1/admin/adoption-applications/{application['id']}",
            json={"status": "reviewing", "internal_note": "Review scope before any invitation."},
            headers=_auth(token),
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == "reviewing"
        assert updated.json()["reviewed_at"] is not None
    finally:
        engine, factory = _make_engine()
        try:
            async with factory() as session:
                await session.exec(
                    text("DELETE FROM adoption_applications WHERE work_email = :email"),
                    params={"email": f"managed-{marker}@example.com"},
                )
                await session.exec(
                    text("DELETE FROM users WHERE id = :id"),
                    params={"id": str(operator_id)},
                )
                await session.commit()
        finally:
            await engine.dispose()
