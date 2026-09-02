"""RFQ handoff workspace, role boundaries and tenant isolation."""

import uuid

from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload(email: str, company: str = "Acme Industrial") -> dict:
    return {"full_name": "Alex Buyer", "email": email, "company_name": company, "country": "DE", "consent": True, "product_ids": [], "quantity": "5,000 pcs", "specifications": "SUS304 per drawing", "message": "Please review FOB Hamburg."}


@requires_db
async def test_rfq_handoff_end_to_end(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, tenant_b = two_tenants
    tag = uuid.uuid4().hex[:8]
    admin_token = await admin_token_for_tenant(tenant_a.id)
    other_admin_token = await admin_token_for_tenant(tenant_b.id)
    engine, factory = _make_engine()
    async with factory() as session:
        sales = User(email=f"sales-{tag}@test.invalid", hashed_password=get_password_hash("testpass"), full_name="Alice Sales", role="sales", tenant_id=tenant_a.id)
        session.add(sales); await session.commit(); await session.refresh(sales)
    sales_token = create_access_token(str(sales.id))

    public_headers = {"X-Tenant-ID": str(tenant_a.id)}
    buyer_email = f"repeat-{tag}@acme.com"
    first = await http_client.post("/api/v1/forms/rfq", headers=public_headers, json=_payload(buyer_email))
    second = await http_client.post("/api/v1/forms/rfq", headers=public_headers, json=_payload(buyer_email))
    spam_row = await http_client.post("/api/v1/forms/rfq", headers=public_headers, json=_payload(f"spam-{tag}@example.com", "Directory Promotion"))
    assert first.status_code == second.status_code == spam_row.status_code == 201
    first_id, second_id, spam_id = first.json()["rfq_id"], second.json()["rfq_id"], spam_row.json()["rfq_id"]

    assigned = await http_client.put(f"/api/v1/tracking/rfqs/{first_id}/assign", headers=_auth(admin_token), json={"assigned_to": str(sales.id), "priority": "high"})
    assert assigned.status_code == 200
    await http_client.put(f"/api/v1/tracking/rfqs/{spam_id}/assign", headers=_auth(admin_token), json={"assigned_to": str(sales.id)})
    assert (await http_client.put(f"/api/v1/tracking/rfqs/{second_id}/assign", headers=_auth(sales_token), json={"assigned_to": str(sales.id)})).status_code == 403

    detail = (await http_client.get(f"/api/v1/tracking/rfqs/{first_id}", headers=_auth(admin_token))).json()
    assert detail["status"] == "assigned"
    assert detail["accepted_at"] is None
    assert detail["first_verified_response_at"] is None
    assert detail["acknowledgement_sent_at"] is None
    assert detail["acceptance_due_at"] is not None
    assert {"quality_score", "deal_amount", "next_follow_up_at", "first_response_at"}.isdisjoint(detail)

    sales_rows = await http_client.get("/api/v1/tracking/rfqs", headers=_auth(sales_token))
    assert {row["id"] for row in sales_rows.json()} == {first_id, spam_id}
    assert (await http_client.get(f"/api/v1/tracking/rfqs/{second_id}", headers=_auth(sales_token))).status_code == 404
    assert (await http_client.get(f"/api/v1/tracking/rfqs/{first_id}", headers=_auth(other_admin_token))).status_code == 404

    accepted = await http_client.put(f"/api/v1/tracking/rfqs/{first_id}/status", headers=_auth(sales_token), json={"status": "accepted"})
    assert accepted.status_code == 200 and accepted.json()["accepted_at"]
    accepted_detail = (await http_client.get(f"/api/v1/tracking/rfqs/{first_id}", headers=_auth(sales_token))).json()
    assert accepted_detail["first_verified_response_at"] is None
    assert (await http_client.post(f"/api/v1/tracking/rfqs/{first_id}/notes", headers=_auth(sales_token), json={"body": "Drawing revision must be confirmed."})).status_code == 201
    notes = await http_client.get(f"/api/v1/tracking/rfqs/{first_id}/notes", headers=_auth(sales_token))
    assert notes.json()[0]["author_name"] == "Alice Sales"

    archived = await http_client.put(f"/api/v1/tracking/rfqs/{first_id}/status", headers=_auth(sales_token), json={"status": "archived"})
    assert archived.status_code == 200 and archived.json()["archived_at"]
    reopened = await http_client.put(f"/api/v1/tracking/rfqs/{first_id}/status", headers=_auth(admin_token), json={"status": "assigned"})
    assert reopened.status_code == 200 and reopened.json()["archived_at"] is None

    assert (await http_client.put(f"/api/v1/tracking/rfqs/{spam_id}/spam", headers=_auth(sales_token), json={"is_spam": True, "reason": "Directory promotion"})).status_code == 200
    active = await http_client.get("/api/v1/tracking/rfqs", headers=_auth(admin_token))
    assert spam_id not in {row["id"] for row in active.json()}
    isolated = await http_client.get("/api/v1/tracking/rfqs?view=spam", headers=_auth(admin_token))
    assert spam_id in {row["id"] for row in isolated.json()}

    merged = await http_client.post(f"/api/v1/tracking/rfqs/{first_id}/merge", headers=_auth(admin_token), json={"duplicate_rfq_id": second_id})
    assert merged.status_code == 200
    merged_rows = await http_client.get("/api/v1/tracking/rfqs?view=merged", headers=_auth(admin_token))
    assert second_id in {row["id"] for row in merged_rows.json()}
    events = await http_client.get(f"/api/v1/tracking/rfqs/{first_id}/events", headers=_auth(admin_token))
    assert {"assigned", "accepted", "archived", "note_added", "duplicate_merged"} <= {row["event_type"] for row in events.json()}

    export = await http_client.get("/api/v1/tracking/rfqs/export.csv", headers=_auth(admin_token))
    exported = export.content.decode("utf-8-sig")
    assert export.status_code == 200 and "Acme Industrial" in exported
    assert "deal_amount" not in exported and "quality_score" not in exported
    await engine.dispose()
