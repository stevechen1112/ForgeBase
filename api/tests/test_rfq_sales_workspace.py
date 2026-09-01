"""RFQ sales workspace, role boundaries and tenant isolation."""

import uuid
from datetime import timedelta

from app.core.datetime import utcnow_naive
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload(email: str, *, company: str = "Acme Industrial") -> dict:
    return {
        "full_name": "Alex Buyer",
        "email": email,
        "company_name": company,
        "country": "DE",
        "consent": True,
        "product_ids": [],
        "quantity": "5,000 pcs",
        "specifications": "Need production quotation and sample lead time.",
        "message": "Please quote FOB Hamburg.",
    }


@requires_db
async def test_rfq_sales_workspace_end_to_end(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, tenant_b = two_tenants
    tag = uuid.uuid4().hex[:8]
    admin_token = await admin_token_for_tenant(tenant_a.id)
    other_admin_token = await admin_token_for_tenant(tenant_b.id)

    engine, factory = _make_engine()
    async with factory() as session:
        sales = User(
            email=f"sales-{tag}@test.invalid",
            hashed_password=get_password_hash("testpass"),
            full_name="Alice Sales",
            role="sales",
            tenant_id=tenant_a.id,
        )
        marketing = User(
            email=f"marketing-{tag}@test.invalid",
            hashed_password=get_password_hash("testpass"),
            full_name="Mark Marketing",
            role="marketing_manager",
            tenant_id=tenant_a.id,
        )
        session.add(sales)
        session.add(marketing)
        await session.commit()
        await session.refresh(sales)
        await session.refresh(marketing)
    sales_token = create_access_token(str(sales.id))
    marketing_token = create_access_token(str(marketing.id))

    public_headers = {"X-Tenant-ID": str(tenant_a.id)}
    buyer_email = f"repeat-{tag}@acme.com"
    first = await http_client.post("/api/v1/forms/rfq", headers=public_headers, json=_payload(buyer_email))
    second = await http_client.post("/api/v1/forms/rfq", headers=public_headers, json=_payload(buyer_email))
    third = await http_client.post(
        "/api/v1/forms/rfq",
        headers=public_headers,
        json=_payload(f"spam-{tag}@example.com", company="Directory Promotion"),
    )
    assert first.status_code == second.status_code == third.status_code == 201
    first_id = first.json()["rfq_id"]
    second_id = second.json()["rfq_id"]
    third_id = third.json()["rfq_id"]

    # Only managers assign cases, and the assignee must belong to this tenant.
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{first_id}/assign",
        headers=_auth(admin_token),
        json={"assigned_to": str(sales.id)},
    )
    assert response.status_code == 200, response.text
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{third_id}/assign",
        headers=_auth(admin_token),
        json={"assigned_to": str(sales.id)},
    )
    assert response.status_code == 200, response.text
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{second_id}/assign",
        headers=_auth(sales_token),
        json={"assigned_to": str(sales.id)},
    )
    assert response.status_code == 403

    # Sales sees and operates only assigned cases; marketing is read-only.
    response = await http_client.get("/api/v1/tracking/rfqs", headers=_auth(sales_token))
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {first_id, third_id}
    assert response.json()[0]["contact"]["company_name"]
    assert response.json()[0]["assigned_to_name"] == "Alice Sales"
    assert (await http_client.get(f"/api/v1/tracking/rfqs/{second_id}", headers=_auth(sales_token))).status_code == 404
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{first_id}/follow-up",
        headers=_auth(marketing_token),
        json={"next_follow_up_at": utcnow_naive().isoformat()},
    )
    assert response.status_code == 403

    follow_up_at = utcnow_naive() + timedelta(hours=4)
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{first_id}/follow-up",
        headers=_auth(sales_token),
        json={"next_follow_up_at": follow_up_at.isoformat()},
    )
    assert response.status_code == 200, response.text
    response = await http_client.post(
        f"/api/v1/tracking/rfqs/{first_id}/notes",
        headers=_auth(sales_token),
        json={"body": "Buyer requested a revised sample schedule."},
    )
    assert response.status_code == 201, response.text
    notes = await http_client.get(f"/api/v1/tracking/rfqs/{first_id}/notes", headers=_auth(sales_token))
    assert notes.status_code == 200
    assert notes.json()[0]["author_name"] == "Alice Sales"
    assert (await http_client.get(f"/api/v1/tracking/rfqs/{first_id}/notes", headers=_auth(other_admin_token))).status_code == 404

    detail = await http_client.get(f"/api/v1/tracking/rfqs/{first_id}", headers=_auth(admin_token))
    assert detail.status_code == 200, detail.text
    assert detail.json()["contact"]["email"] == buyer_email
    assert detail.json()["next_follow_up_at"].endswith("Z")
    assert any(item["id"] == second_id for item in detail.json()["duplicate_candidates"])
    assert "visitor_history" in detail.json()
    assert "crm_sync" not in detail.json()

    # The sales workspace records outcome reason, amount and currency.
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{first_id}/status",
        headers=_auth(sales_token),
        json={"status": "won", "reason": "Approved production order", "deal_amount": "12500.50", "deal_currency": "eur"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["deal_amount"] == "12500.50"
    assert response.json()["deal_currency"] == "EUR"

    # Spam is quarantined, not deleted. Duplicate merging is manager-only and auditable.
    response = await http_client.put(
        f"/api/v1/tracking/rfqs/{third_id}/spam",
        headers=_auth(sales_token),
        json={"is_spam": True, "reason": "Directory sales promotion"},
    )
    assert response.status_code == 200, response.text
    active = await http_client.get("/api/v1/tracking/rfqs", headers=_auth(admin_token))
    assert third_id not in {row["id"] for row in active.json()}
    spam = await http_client.get("/api/v1/tracking/rfqs?view=spam", headers=_auth(admin_token))
    assert third_id in {row["id"] for row in spam.json()}

    response = await http_client.post(
        f"/api/v1/tracking/rfqs/{first_id}/merge",
        headers=_auth(admin_token),
        json={"duplicate_rfq_id": second_id},
    )
    assert response.status_code == 200, response.text
    merged = await http_client.get("/api/v1/tracking/rfqs?view=merged", headers=_auth(admin_token))
    assert second_id in {row["id"] for row in merged.json()}

    export = await http_client.get("/api/v1/tracking/rfqs/export.csv", headers=_auth(admin_token))
    assert export.status_code == 200, export.text
    assert "text/csv" in export.headers["content-type"]
    assert "Acme Industrial" in export.content.decode("utf-8-sig")
    assert (await http_client.get("/api/v1/tracking/rfqs/export.csv", headers=_auth(sales_token))).status_code == 403

    events = await http_client.get(f"/api/v1/tracking/rfqs/{first_id}/events", headers=_auth(admin_token))
    event_types = {event["event_type"] for event in events.json()}
    assert {"assigned", "next_follow_up_set", "note_added", "status_changed", "duplicate_merged"} <= event_types

    await engine.dispose()
