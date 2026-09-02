"""T7/T8: 時區感知首回 SLA 與首回時間記錄。"""
import uuid
from datetime import datetime

from app.services.sla import add_business_hours, timezone_for_country
from tests.conftest import requires_db


# ── 工作時間計算（以買家當地時間為準，輸入輸出皆 UTC-naive）───────────────

def test_timezone_mapping():
    assert timezone_for_country("DE") == "Europe/Berlin"
    assert timezone_for_country("us") == "America/New_York"
    assert timezone_for_country(None) == "UTC"
    assert timezone_for_country("XX") == "UTC"


def test_sla_during_business_hours():
    # 2026-08-03 07:00 UTC = 週一 09:00 CEST；+4h → 13:00 CEST = 11:00 UTC
    due = add_business_hours(datetime(2026, 8, 3, 7, 0), 4, "Europe/Berlin")
    assert due == datetime(2026, 8, 3, 11, 0)


def test_sla_after_hours_rolls_to_next_morning():
    # 週五 18:00 CEST（16:00 UTC）下班後送單 → 週一 09:00 起算 +4h
    due = add_business_hours(datetime(2026, 7, 31, 16, 0), 4, "Europe/Berlin")
    assert due == datetime(2026, 8, 3, 11, 0)


def test_sla_weekend_rolls_to_monday():
    # 週六中午（買家當地）送單 → 週一 09:00 起算
    due = add_business_hours(datetime(2026, 8, 1, 10, 0), 4, "Europe/Berlin")
    assert due == datetime(2026, 8, 3, 11, 0)


def test_sla_spans_across_days():
    # 週一 16:00 CEST +4h：剩 2h 到 18:00，隔天 09:00 +2h → 週二 11:00 CEST = 09:00 UTC
    due = add_business_hours(datetime(2026, 8, 3, 14, 0), 4, "Europe/Berlin")
    assert due == datetime(2026, 8, 4, 9, 0)


# ── API 整合 ─────────────────────────────────────────────────────────────

@requires_db
async def test_rfq_sla_lifecycle(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    tag = uuid.uuid4().hex[:8]
    headers = {"X-Tenant-ID": str(tenant_a.id)}

    r = await http_client.post("/api/v1/forms/rfq", headers=headers, json={
        "full_name": "SLA Buyer", "email": f"sla-{tag}@acme.com",
        "company_name": "Acme", "country": "DE", "consent": True,
        "product_ids": [], "message": "Need a quote for 5,000 stamped brackets per drawing.",
    })
    assert r.status_code == 201, r.text
    rfq_id = r.json()["rfq_id"]

    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}

    r = await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)
    detail = r.json()
    assert detail["buyer_timezone"] == "Europe/Berlin"
    assert detail["acceptance_due_at"] is not None
    assert detail["acceptance_sla_breached"] is False
    assert detail["accepted_at"] is None
    assert detail["first_verified_response_at"] is None

    # 尚未分派不得直接接手；分派與接手是兩個獨立事件。
    denied = await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
        json={"status": "accepted"},
    )
    assert denied.status_code == 422
    from tests.conftest import _make_engine
    from app.models.user import User
    from sqlmodel import select
    _, factory = _make_engine()
    async with factory() as session:
        owner = (await session.exec(select(User).where(User.tenant_id == tenant_a.id))).first()
    r = await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/assign", headers=auth,
        json={"assigned_to": str(owner.id)},
    )
    assert r.status_code == 200, r.text
    r = await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
        json={"status": "accepted"},
    )
    assert r.status_code == 200, r.text

    r = await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)
    detail = r.json()
    assert detail["accepted_at"] is not None
    assert detail["accepted_at"] >= detail["created_at"]
    assert detail["first_verified_response_at"] is None

    # 接手篩選參數 smoke test
    r = await http_client.get("/api/v1/tracking/rfqs?attention=awaiting_acceptance", headers=auth)
    assert r.status_code == 200, r.text
    assert all(row["status"] == "assigned" for row in r.json())
