"""Batch-7 closed-loop lineage, tenant isolation, funnel and auto gate tests."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.datetime import utcnow_naive
from app.models.outreach import OutreachDeliveryPolicy
from app.models.rfq_request import RFQRequest
from app.models.tenant import Tenant
from app.services.attribution import derive_attribution
from tests.conftest import _make_engine, requires_db
from tests.test_inbound_reply_handoff import _seed_reply


async def _enable_closed_loop(factory, tenant_id) -> None:
    async with factory() as db:
        tenant = await db.get(Tenant, tenant_id)
        tenant.feature_overrides = {
            **(tenant.feature_overrides or {}),
            "inbound_reply": True,
            "sales_handoff": True,
            "closed_loop_attribution": True,
        }
        db.add(tenant)
        await db.commit()


@requires_db
@pytest.mark.asyncio
async def test_reviewed_reply_conversion_is_direct_and_preserves_outcome_history(
    two_tenants, admin_token_for_tenant, http_client
) -> None:
    tenant_a, tenant_b = two_tenants
    engine, factory = _make_engine()
    try:
        await _enable_closed_loop(factory, tenant_a.id)
        await _enable_closed_loop(factory, tenant_b.id)
        reply = await _seed_reply(factory, tenant_a, suffix=uuid.uuid4().hex[:8])
        token_a = await admin_token_for_tenant(tenant_a.id)
        token_b = await admin_token_for_tenant(tenant_b.id)
        auth_a = {"Authorization": f"Bearer {token_a}"}
        auth_b = {"Authorization": f"Bearer {token_b}"}

        created = await http_client.post(
            f"/api/v1/tracking/replies/{reply.id}/handoff", headers=auth_a, json={}
        )
        assert created.status_code == 200, created.text
        converted = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{created.json()['id']}/convert-to-rfq",
            headers=auth_a,
            json={"note": "Buyer requested a quotation"},
        )
        assert converted.status_code == 200, converted.text
        rfq_id = converted.json()["rfq_id"]

        detail = await http_client.get(
            f"/api/v1/tracking/rfqs/{rfq_id}/attribution", headers=auth_a
        )
        assert detail.status_code == 200, detail.text
        payload = detail.json()
        assert payload["attribution_type"] == "direct"
        assert payload["confidence"] == pytest.approx(0.98)
        assert payload["evidence"]["causal_claim"] == "direct_conversion"
        assert payload["lineage"]["inbound_reply_id"] == str(reply.id)
        assert payload["lineage"]["sales_handoff_id"] == created.json()["id"]

        isolated = await http_client.get(
            f"/api/v1/tracking/rfqs/{rfq_id}/attribution", headers=auth_b
        )
        assert isolated.status_code == 404

        won = await http_client.put(
            f"/api/v1/tracking/rfqs/{rfq_id}/status",
            headers=auth_a,
            json={
                "status": "won",
                "reason": "Buyer accepted the reviewed quotation",
                "deal_amount": "12500.00",
                "deal_currency": "USD",
            },
        )
        assert won.status_code == 200, won.text
        refreshed = await http_client.get(
            f"/api/v1/tracking/rfqs/{rfq_id}/attribution", headers=auth_a
        )
        actions = [event["action"] for event in refreshed.json()["events"]]
        assert actions.count("derived") == 1
        assert "outcome_changed" in actions

        funnel = await http_client.get(
            "/api/v1/tracking/growth-funnel?days=30", headers=auth_a
        )
        assert funnel.status_code == 200, funnel.text
        layers = {row["stage"]: row for row in funnel.json()["layers"]}
        assert layers["tracked_visitors"]["count"] >= 1
        assert layers["rfq"]["count"] >= 1
        assert layers["won"]["count"] >= 1
        assert funnel.json()["attribution"]["direct"]["count"] >= 1
        assert Decimal(funnel.json()["attribution"]["direct"]["won_revenue"]) >= Decimal(12500)
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_existing_rfq_link_is_assisted_and_manual_override_is_append_only(
    two_tenants, admin_token_for_tenant, http_client
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    try:
        await _enable_closed_loop(factory, tenant.id)
        reply = await _seed_reply(factory, tenant, suffix=uuid.uuid4().hex[:8])
        token = await admin_token_for_tenant(tenant.id)
        auth = {"Authorization": f"Bearer {token}"}
        created = await http_client.post(
            f"/api/v1/tracking/replies/{reply.id}/handoff", headers=auth, json={}
        )
        assert created.status_code == 200, created.text

        now = utcnow_naive()
        existing_id = uuid.uuid4()
        async with factory() as db:
            db.add(
                RFQRequest(
                    id=existing_id,
                    tenant_id=tenant.id,
                    rfq_number=f"RFQ-ASSISTED-{uuid.uuid4().hex[:8]}",
                    status="new",
                    created_at=now,
                    updated_at=now,
                )
            )
            await db.commit()
        linked = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{created.json()['id']}/link-rfq",
            headers=auth,
            json={"rfq_id": str(existing_id), "note": "Matched after human review"},
        )
        assert linked.status_code == 200, linked.text
        detail = await http_client.get(
            f"/api/v1/tracking/rfqs/{existing_id}/attribution", headers=auth
        )
        assert detail.json()["attribution_type"] == "assisted"
        assert detail.json()["evidence"]["causal_claim"] == "assisted_only_no_direct_causal_claim"

        override = await http_client.put(
            f"/api/v1/tracking/rfqs/{existing_id}/attribution",
            headers=auth,
            json={
                "attribution_type": "manual",
                "confidence": 0.55,
                "reason": "Sales confirmed an offline event was the primary source.",
            },
        )
        assert override.status_code == 200, override.text
        assert override.json()["manually_overridden"] is True
        assert override.json()["attribution_type"] == "manual"
        history = await http_client.get(
            f"/api/v1/tracking/rfqs/{existing_id}/attribution", headers=auth
        )
        assert [event["action"] for event in history.json()["events"]] == [
            "derived",
            "manual_override",
        ]
        assert history.json()["events"][1]["previous_type"] == "assisted"
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_unknown_is_not_promoted_and_controlled_auto_remains_evaluation_only(
    two_tenants, admin_token_for_tenant, http_client
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    try:
        await _enable_closed_loop(factory, tenant.id)
        now = utcnow_naive()
        rfq_id = uuid.uuid4()
        legacy_rfq_id = uuid.uuid4()
        async with factory() as db:
            rfq = RFQRequest(
                id=rfq_id,
                tenant_id=tenant.id,
                rfq_number=f"RFQ-UNKNOWN-{uuid.uuid4().hex[:8]}",
                status="won",
                deal_amount=999,
                deal_currency="USD",
                created_at=now - timedelta(days=1),
                updated_at=now,
            )
            db.add(rfq)
            db.add(
                RFQRequest(
                    id=legacy_rfq_id,
                    tenant_id=tenant.id,
                    rfq_number=f"RFQ-LEGACY-{uuid.uuid4().hex[:8]}",
                    status="new",
                    created_at=now - timedelta(days=1),
                    updated_at=now,
                )
            )
            await db.flush()
            link = await derive_attribution(db, rfq=rfq)
            db.add(
                OutreachDeliveryPolicy(
                    tenant_id=tenant.id,
                    mode="approval_send",
                    controlled_auto_opt_in=True,
                    controlled_auto_legal_approved=True,
                    controlled_auto_allowed_regions=["US"],
                    controlled_auto_allowed_personas=["procurement"],
                    controlled_auto_allowed_templates=["pump-v1"],
                    controlled_auto_review_sample_pct=100,
                )
            )
            await db.commit()
            assert link.attribution_type == "unknown"

        token = await admin_token_for_tenant(tenant.id)
        auth = {"Authorization": f"Bearer {token}"}
        missing = await http_client.get(
            f"/api/v1/tracking/rfqs/{legacy_rfq_id}/attribution", headers=auth
        )
        assert missing.status_code == 404

        invalid_direct = await http_client.put(
            f"/api/v1/tracking/rfqs/{rfq_id}/attribution",
            headers=auth,
            json={
                "attribution_type": "direct",
                "confidence": 0.9,
                "reason": "No verified causal handoff chain exists for this RFQ.",
            },
        )
        assert invalid_direct.status_code == 409

        funnel = await http_client.get(
            "/api/v1/tracking/growth-funnel?days=30", headers=auth
        )
        assert funnel.status_code == 200, funnel.text
        assert funnel.json()["attribution"]["unknown"]["count"] >= 2

        rebuilt = await http_client.post(
            "/api/v1/tracking/attribution/rebuild?limit=1&offset=0", headers=auth
        )
        assert rebuilt.status_code == 200, rebuilt.text
        assert rebuilt.json()["processed"] == 1
        assert rebuilt.json()["next_offset"] == 1
        assert rebuilt.json()["total"] >= 2

        readiness = await http_client.get(
            "/api/v1/tracking/controlled-auto/readiness?days=30", headers=auth
        )
        assert readiness.status_code == 200, readiness.text
        payload = readiness.json()
        assert payload["evaluation_only"] is True
        assert payload["activation_available"] is False
        assert payload["gate_passed"] is False
        assert "delivery_sample" in payload["blockers"]
        assert payload["metrics"]["bounce"]["denominator"] == 0

        quality = await http_client.get(
            "/api/v1/tracking/growth-funnel/quality?days=30", headers=auth
        )
        assert quality.status_code == 200
        for metric in quality.json()["metrics"].values():
            assert {"numerator", "denominator", "rate_pct"} <= set(metric)
    finally:
        await engine.dispose()
