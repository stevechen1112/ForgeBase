"""Retention cleanup for consented anonymous analytics data."""
from datetime import timedelta

from sqlalchemy import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.services.company_identification.privacy import purge_expired_company_evidence
from app.services.contact_enrichment.runtime import purge_expired_contact_candidates
from app.services.outreach.runtime import purge_expired_outreach_evidence


async def purge_expired_analytics(db: AsyncSession) -> dict[str, int]:
    outreach_evidence = await purge_expired_outreach_evidence(db)
    company_evidence = await purge_expired_company_evidence(db)
    contact_candidates = await purge_expired_contact_candidates(db)
    cutoff = utcnow_naive() - timedelta(days=max(1, settings.ANALYTICS_RETENTION_DAYS))
    events = await db.exec(delete(TrackingEvent).where(TrackingEvent.timestamp < cutoff))
    sessions = await db.exec(delete(TrackingSession).where(TrackingSession.updated_at < cutoff))
    await db.commit()
    return {
        "events": int(events.rowcount or 0),
        "sessions": int(sessions.rowcount or 0),
        **company_evidence,
        **outreach_evidence,
        "expired_contact_candidates": contact_candidates,
    }
