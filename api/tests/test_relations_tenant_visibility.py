"""Tenant visibility rules for content relationship endpoints."""

import uuid
from types import SimpleNamespace

from app.api.v1.endpoints.relations import _tenant_visible


def test_tenant_can_only_see_own_content() -> None:
    tenant_id = uuid.uuid4()

    assert _tenant_visible(SimpleNamespace(tenant_id=tenant_id), tenant_id)
    assert not _tenant_visible(SimpleNamespace(tenant_id=None), tenant_id)


def test_tenant_cannot_see_another_tenants_content() -> None:
    assert not _tenant_visible(
        SimpleNamespace(tenant_id=uuid.uuid4()),
        uuid.uuid4(),
    )


def test_tenantless_context_only_sees_legacy_content() -> None:
    assert _tenant_visible(SimpleNamespace(tenant_id=None), None)
    assert not _tenant_visible(SimpleNamespace(tenant_id=uuid.uuid4()), None)
