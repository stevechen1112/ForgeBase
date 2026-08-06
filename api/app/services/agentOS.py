"""
AgentOS Integration Service — trigger RFQ workflows on AgentOS

This service is responsible for:
1. Triggering RFQ analysis tasks on AgentOS
2. Capturing run_id and storing in RFQ.agent_run_id
3. Handling failures gracefully (fault tolerance)
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

import httpx

from app.core.config import settings
from app.db.session import get_session_ctx
from app.models.rfq_event import RFQEvent
from app.models.rfq_request import RFQRequest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)


async def trigger_agentOS_rfq(rfq_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> Optional[str]:
    """
    Trigger AgentOS to start RFQ analysis workflow.
    
    Args:
        rfq_id: The RFQRequest.id
        tenant_id: The tenant context
        
    Returns:
        The AgentOS run_id if successful, None if failed
        
    Raises:
        httpx.HTTPError: If AgentOS is unreachable (caller should catch and handle)
    """
    
    # Get the RFQ record
    async with get_session_ctx() as db:
        rfq = await db.get(RFQRequest, rfq_id)
        if not rfq:
            logger.warning(f"RFQ {rfq_id} not found for AgentOS trigger")
            return None
    
    # Build the AgentOS task payload (matches TaskCreateRequest schema)
    task_payload = {
        "tenant_id": str(tenant_id) if tenant_id else "system",
        "domain": "forgebase_rfq",
        "objective": f"Analyse and draft reply for RFQ {rfq_id}",
        "idempotency_key": str(rfq_id),  # binding anchor: lets AgentOS detect duplicates and ForgeBase verify back-ref
        "workflow_input": {
            "rfq_id": str(rfq_id),
            "source_id": str(rfq_id),
        },
    }
    
    # Call AgentOS POST /tasks
    agentOS_url = settings.AGENTOSS_URL
    if not agentOS_url:
        logger.warning("AGENTOSS_URL not configured, skipping trigger")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{agentOS_url}/tasks",
                json=task_payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            response_data = response.json()
            run_data = response_data.get("run", {})
            run_id = run_data.get("id")
            
            if run_id:
                # Store run_id in RFQ
                async with get_session_ctx() as db:
                    rfq = await db.get(RFQRequest, rfq_id)
                    if rfq:
                        rfq.agent_run_id = run_id
                        db.add(rfq)
                        await db.commit()
                        
                        # Log success event
                        await _log_rfq_event(
                            db, rfq_id, "agentOS_triggered",
                            f"AgentOS workflow triggered with run_id={run_id}",
                            tenant_id=tenant_id,
                            detail=json.dumps({"run_id": run_id}),
                        )
                
                logger.info(f"RFQ {rfq_id} triggered on AgentOS with run_id={run_id}")
                return run_id
            else:
                logger.error(f"AgentOS response missing run_id: {response_data}")
                return None
                
    except httpx.HTTPError as e:
        logger.error(f"Failed to trigger AgentOS for RFQ {rfq_id}: {e}")
        
        # Log error event
        async with get_session_ctx() as db:
            await _log_rfq_event(
                db, rfq_id, "agentOS_trigger_failed",
                f"AgentOS trigger failed: {str(e)}",
                tenant_id=tenant_id,
                detail=json.dumps({"error": str(e), "error_type": type(e).__name__}),
            )
        
        raise  # Re-raise so caller knows trigger failed


async def _log_rfq_event(
    db: AsyncSession,
    rfq_id: uuid.UUID,
    event_type: str,
    summary: str,
    *,
    actor_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[uuid.UUID] = None,
    detail: Optional[str] = None,
) -> None:
    """Append an immutable event to the rfq_events audit log."""
    db.add(RFQEvent(
        rfq_id=rfq_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type=event_type,
        summary=summary,
        detail=detail,
    ))
    # Note: do NOT commit here; let the caller manage the transaction


async def writeback_agentOS_result(rfq_id: uuid.UUID, run_id: str, tenant_id: Optional[uuid.UUID] = None) -> bool:
    """
    Write AgentOS run evidence back to the ForgeBase RFQ record.

    Calls AgentOS GET /runs/{run_id}/evidence, extracts:
      - forgebase_analyze_rfq evidence → agent_analysis_summary
      - forgebase_send_reply evidence  → agent_draft_body

    This operation is idempotent: calling it multiple times produces the same result.

    Returns:
        True if writeback succeeded, False if run/evidence not yet available.
    """
    agentOS_url = settings.AGENTOSS_URL
    if not agentOS_url:
        logger.warning("AGENTOSS_URL not configured, skipping writeback")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{agentOS_url}/runs/{run_id}/evidence",
                headers={"Accept": "application/json"},
            )
            if response.status_code == 404:
                logger.info(f"AgentOS run {run_id} evidence not yet available")
                return False
            response.raise_for_status()
            evidence_list = response.json()

        analysis_summary: Optional[str] = None
        draft_body: Optional[str] = None

        for ev in evidence_list:
            source_uri = ev.get("source_uri", "")
            payload = ev.get("payload", {})
            output = payload.get("output", {})
            if source_uri == "forgebase_analyze_rfq":
                # output = {"analysis": {"summary": ..., ...}}
                analysis = output.get("analysis", {})
                analysis_summary = str(analysis.get("summary", "")) or analysis_summary
            elif source_uri == "forgebase_send_reply":
                # output = {"delivery_status": "queued", "approved_draft": {"body": ..., "subject": ...}}
                approved_draft = output.get("approved_draft", {})
                draft_body = approved_draft.get("body") or draft_body

        async with get_session_ctx() as db:
            rfq = await db.get(RFQRequest, rfq_id)
            if not rfq:
                logger.warning(f"RFQ {rfq_id} not found for writeback")
                return False

            # Idempotent: only overwrite if new value is non-None
            if analysis_summary is not None:
                rfq.agent_analysis_summary = analysis_summary
            if draft_body is not None:
                rfq.agent_draft_body = draft_body
            db.add(rfq)

            await _log_rfq_event(
                db, rfq_id, "agentOS_writeback",
                f"AgentOS result written back from run_id={run_id}",
                tenant_id=tenant_id,
                detail=json.dumps({
                    "run_id": run_id,
                    "has_analysis": analysis_summary is not None,
                    "has_draft": draft_body is not None,
                }),
            )
            await db.commit()

        logger.info(f"RFQ {rfq_id}: writeback from run {run_id} complete")
        return True

    except httpx.HTTPError as e:
        logger.error(f"Failed to writeback AgentOS result for RFQ {rfq_id}: {e}")
        raise
