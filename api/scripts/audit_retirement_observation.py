"""Emit and validate a privacy-minimised production retirement snapshot."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlmodel import col, select

from app.api.v1.endpoints.retirement_audit import _candidate_payload
from app.db.session import AsyncSessionLocal, engine
from app.models.retirement import RetirementCandidateObservation

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

OBSERVING_DISABLED = {
    "relation_recommender": 60,
    "notification_telegram": 60,
    "notification_line": 60,
}
REMOVED = {"legacy_ip_resolver"}
PROTECTED_NORTH_STAR = {
    "full_tracking",
    "company_identification",
    "contact_enrichment",
    "journey_personalization",
    "outreach_send",
    "inbound_reply",
    "sales_handoff",
    "rfq_workspace",
}


def validate_snapshot(candidates: list[dict]) -> dict:
    by_key = {candidate["candidate_key"]: candidate for candidate in candidates}
    missing = sorted((set(OBSERVING_DISABLED) | REMOVED) - set(by_key))
    violations: list[str] = []
    if missing:
        violations.append(f"missing_candidates:{','.join(missing)}")

    for key, required_days in OBSERVING_DISABLED.items():
        candidate = by_key.get(key)
        if not candidate:
            continue
        if candidate["code_state"] != "disabled":
            violations.append(f"{key}:entry_not_disabled")
        if candidate["status"] != "observing":
            violations.append(f"{key}:not_observing")
        if candidate["required_observation_days"] != required_days:
            violations.append(f"{key}:unexpected_window")
        if candidate["removal_ready"]:
            violations.append(f"{key}:premature_removal_ready")
        if key.startswith("notification_") and candidate["evidence"].get(
            "enabled_preferences"
        ):
            violations.append(f"{key}:enabled_preferences")

    for key in REMOVED:
        candidate = by_key.get(key)
        if candidate and (
            candidate["code_state"] != "removed" or candidate["status"] != "removed"
        ):
            violations.append(f"{key}:removed_state_mismatch")

    protected_overlap = sorted(PROTECTED_NORTH_STAR & set(by_key))
    if protected_overlap:
        violations.append(f"north_star_marked_for_retirement:{','.join(protected_overlap)}")

    return {
        "status": "failed" if violations else "passed",
        "violations": violations,
        "observing_disabled": sorted(OBSERVING_DISABLED),
        "removed_verified": sorted(REMOVED),
        "new_removals_authorized": [],
        "notification_core_retained": True,
    }


async def main() -> None:
    engine.echo = False
    async with AsyncSessionLocal() as session:
        rows = list(
            (
                await session.exec(
                    select(RetirementCandidateObservation).order_by(
                        col(RetirementCandidateObservation.candidate_key)
                    )
                )
            ).all()
        )
        candidates = [await _candidate_payload(session, row) for row in rows]

    validation = validate_snapshot(candidates)
    digest = hashlib.sha256(
        json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_sha256": digest,
        **validation,
        "candidates": candidates,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if validation["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
