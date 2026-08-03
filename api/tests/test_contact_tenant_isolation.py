"""T2: Contact email uniqueness is scoped to (tenant_id, email).

Verifies:
1. The same email can create one Contact per tenant.
2. Dedup still merges within the same tenant.
3. Admin contact lists stay tenant-isolated.
"""
import uuid

from tests.conftest import requires_db


@requires_db
async def test_same_email_allowed_across_tenants(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, tenant_b = two_tenants
    email = f"buyer-{uuid.uuid4().hex[:8]}@example.com"
    payload = {"full_name": "Cross Tenant Buyer", "email": email}

    # Tenant A submits — new contact
    r = await http_client.post(
        "/api/v1/forms/contact", json=payload, headers={"X-Tenant-ID": str(tenant_a.id)}
    )
    assert r.status_code == 201, r.text
    body_a = r.json()
    assert body_a["new"] is True

    # Tenant B submits the SAME email — must be a separate, new contact
    r = await http_client.post(
        "/api/v1/forms/contact", json=payload, headers={"X-Tenant-ID": str(tenant_b.id)}
    )
    assert r.status_code == 201, r.text
    body_b = r.json()
    assert body_b["new"] is True
    assert body_b["contact_id"] != body_a["contact_id"]

    # Tenant A submits again — dedup merges within tenant A
    r = await http_client.post(
        "/api/v1/forms/contact", json=payload, headers={"X-Tenant-ID": str(tenant_a.id)}
    )
    assert r.status_code == 201, r.text
    body_a2 = r.json()
    assert body_a2["new"] is False
    assert body_a2["contact_id"] == body_a["contact_id"]

    # Admin list isolation: each tenant sees exactly their own record
    token_a = await admin_token_for_tenant(tenant_a.id)
    token_b = await admin_token_for_tenant(tenant_b.id)

    r = await http_client.get(
        "/api/v1/tracking/contacts", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert r.status_code == 200, r.text
    emails_a = [c["email"] for c in r.json() if c["email"] == email]
    assert len(emails_a) == 1

    r = await http_client.get(
        "/api/v1/tracking/contacts", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert r.status_code == 200, r.text
    emails_b = [c["email"] for c in r.json() if c["email"] == email]
    assert len(emails_b) == 1


@requires_db
async def test_rfq_same_email_across_tenants(http_client, two_tenants):
    """RFQ contact upsert must also dedup per-tenant, not globally."""
    tenant_a, tenant_b = two_tenants
    email = f"rfq-buyer-{uuid.uuid4().hex[:8]}@example.com"

    def _payload():
        return {
            "full_name": "RFQ Buyer",
            "email": email,
            "company_name": "Acme Corp",
            "country": "DE",
            "message": "Need 10k units of part X",
            "product_ids": [],
            "consent": True,
        }

    for tenant in (tenant_a, tenant_b):
        r = await http_client.post(
            "/api/v1/forms/rfq", json=_payload(), headers={"X-Tenant-ID": str(tenant.id)}
        )
        assert r.status_code == 201, r.text
