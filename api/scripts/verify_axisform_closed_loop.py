"""Verify and close one obvious AxisForm E2E RFQ without contacting anyone."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlmodel import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.models  # noqa: F401
from app.core.datetime import utcnow_naive
from app.db.session import AsyncSessionLocal
from app.models.contact import Contact
from app.models.operational_job import OperationalJob
from app.models.rfq_event import RFQEvent
from app.models.rfq_request import RFQRequest
from app.models.site_profile import SiteProfile
from app.models.tenant import Tenant


async def verify(email: str) -> None:
    if not email.startswith("forgebase-axisform-e2e+") or not email.endswith("@example.com"):
        raise ValueError("Only the obvious ForgeBase AxisForm E2E address may be closed by this verifier")
    async with AsyncSessionLocal() as session:
        tenant = (await session.exec(select(Tenant).where(Tenant.slug == "axisform-precision"))).first()
        if not tenant:
            raise RuntimeError("AxisForm tenant not found")
        profile = (await session.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant.id))).first()
        ops_config = json.loads(profile.ops_config_json or "{}") if profile else {}
        if ops_config.get("auto_reply_enabled") is not False:
            raise RuntimeError("AxisForm auto reply must remain explicitly disabled")
        contact = (await session.exec(select(Contact).where(Contact.tenant_id == tenant.id, Contact.email == email))).first()
        if not contact:
            raise RuntimeError("Synthetic contact not found in AxisForm tenant")
        rfq = (await session.exec(select(RFQRequest).where(RFQRequest.tenant_id == tenant.id, RFQRequest.contact_id == contact.id))).first()
        if not rfq:
            raise RuntimeError("Synthetic RFQ not found in AxisForm tenant")
        wrong_tenant_count = (await session.exec(select(func.count()).select_from(Contact).where(Contact.email == email, Contact.tenant_id != tenant.id))).one()
        jobs = (await session.exec(select(OperationalJob).where(OperationalJob.tenant_id == tenant.id, OperationalJob.payload_json.contains(str(rfq.id))))).all()
        if wrong_tenant_count or not jobs:
            raise RuntimeError("Tenant boundary or operational outbox verification failed")

        rfq.status = "won"
        rfq.won_reason = "AUTOMATED E2E OUTCOME — NOT A REAL LEAD OR ORDER"
        rfq.closed_at = utcnow_naive()
        rfq.updated_at = utcnow_naive()
        session.add(rfq)
        session.add(RFQEvent(rfq_id=rfq.id, tenant_id=tenant.id, event_type="status_changed", summary="Automated E2E verification closed synthetic RFQ as won", detail=json.dumps({"old_status":"new","new_status":"won","test_only":True})))
        await session.commit()
        job_statuses: dict[str, int] = {}
        job_errors: dict[str, str] = {}
        for job in jobs:
            key = f"{job.job_type}:{job.status}"
            job_statuses[key] = job_statuses.get(key, 0) + 1
            if job.last_error:
                job_errors[job.job_type] = job.last_error[:240]
        print(json.dumps({"tenant":"axisform-precision","rfq_number":rfq.rfq_number,"quality_score":rfq.quality_score,"outbox_jobs":len(jobs),"job_statuses":job_statuses,"job_errors":job_errors,"wrong_tenant_records":wrong_tenant_count,"outcome":"won-test-only","auto_reply_enabled":False,"no_contact_performed":True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    asyncio.run(verify(parser.parse_args().email))
