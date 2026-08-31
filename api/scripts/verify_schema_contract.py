"""Fail when the migrated database breaks the North Star buyer pipeline contract."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.core.config import settings  # noqa: E402

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "visitors": {
        "visitor_id",
        "tenant_id",
        "analytics_consent_status",
    },
    "tracking_sessions": {"session_id", "tenant_id", "visitor_id", "start_time"},
    "tracking_events": {
        "event_id",
        "tenant_id",
        "visitor_id",
        "session_id",
        "event_name",
    },
    "network_observations": {
        "id",
        "tenant_id",
        "visitor_id",
        "session_id",
        "ip_hash",
        "consent_state",
    },
    "company_identifications": {
        "id",
        "tenant_id",
        "visitor_id",
        "network_observation_id",
        "domain",
        "confidence_band",
        "status",
    },
    "contact_candidates": {
        "id",
        "tenant_id",
        "company_identification_id",
        "email_hash",
        "status",
        "verification_status",
    },
    "journey_snapshots": {
        "id",
        "tenant_id",
        "visitor_id",
        "company_identification_id",
        "contact_candidate_id",
        "generation_key",
    },
    "outreach_messages": {
        "id",
        "tenant_id",
        "visitor_id",
        "contact_candidate_id",
        "journey_snapshot_id",
        "status",
        "send_idempotency_key",
    },
    "inbound_replies": {
        "id",
        "tenant_id",
        "outreach_message_id",
        "classification",
        "needs_human_review",
        "stops_automation",
    },
    "sales_handoffs": {
        "id",
        "tenant_id",
        "inbound_reply_id",
        "outreach_message_id",
        "owner_id",
        "rfq_id",
        "status",
    },
    "rfq_requests": {"id", "tenant_id", "visitor_id", "status", "quality_score"},
    "operational_jobs": {
        "id",
        "tenant_id",
        "job_type",
        "status",
        "idempotency_key",
        "available_at",
    },
}

REQUIRED_FOREIGN_KEYS = {
    (
        "network_observations",
        "session_id",
        "tracking_sessions",
        "session_id",
        "SET NULL",
    ),
    (
        "company_identifications",
        "network_observation_id",
        "network_observations",
        "id",
        "CASCADE",
    ),
    (
        "contact_candidates",
        "company_identification_id",
        "company_identifications",
        "id",
        "SET NULL",
    ),
    (
        "journey_snapshots",
        "company_identification_id",
        "company_identifications",
        "id",
        "CASCADE",
    ),
    (
        "journey_snapshots",
        "contact_candidate_id",
        "contact_candidates",
        "id",
        "CASCADE",
    ),
    ("outreach_messages", "journey_snapshot_id", "journey_snapshots", "id", "CASCADE"),
    (
        "outreach_messages",
        "contact_candidate_id",
        "contact_candidates",
        "id",
        "CASCADE",
    ),
    ("inbound_replies", "outreach_message_id", "outreach_messages", "id", "SET NULL"),
    ("sales_handoffs", "inbound_reply_id", "inbound_replies", "id", "CASCADE"),
    ("sales_handoffs", "rfq_id", "rfq_requests", "id", "SET NULL"),
}

REQUIRED_UNIQUE_INDEXES = {
    "uq_network_observation_tenant_dedupe",
    "uq_company_identification_provider_candidate",
    "uq_contact_candidate_company_email",
    "uq_journey_snapshot_generation_key",
    "uq_outreach_messages_send_idempotency_key",
    "uq_inbound_reply_provider_event",
    "uq_sales_handoff_inbound_reply",
    "operational_jobs_idempotency_key_key",
}

FORBIDDEN_COLUMNS = {
    "visitors": {"intent_score", "intent_stage", "intent_explanation", "stage_alert_sent"},
    "tracking_events": {"score_delta"},
    "contacts": {"intent_score_at_creation", "hubspot_contact_id"},
    "rfq_requests": {"intent_score_at_submit", "intent_snapshot_json", "hubspot_deal_id", "agent_run_id"},
    "journey_snapshots": {"intent_score", "intent_stage", "intent_facets"},
}


def _expected_heads() -> set[str]:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location", str(API_ROOT / "app" / "db" / "migrations")
    )
    return set(ScriptDirectory.from_config(config).get_heads())


async def verify() -> list[str]:
    failures: list[str] = []
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            versions = set(
                (
                    await connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                ).scalars()
            )
            expected_heads = _expected_heads()
            if versions != expected_heads:
                failures.append(
                    f"migration head mismatch: database={sorted(versions)}, code={sorted(expected_heads)}"
                )

            def inspect_contract(sync_connection) -> None:
                inspector = inspect(sync_connection)
                table_names = set(inspector.get_table_names())
                for table, required in REQUIRED_COLUMNS.items():
                    if table not in table_names:
                        failures.append(f"missing table: {table}")
                        continue
                    actual = {column["name"] for column in inspector.get_columns(table)}
                    if missing := required - actual:
                        failures.append(f"{table}: missing columns {sorted(missing)}")
                    if forbidden := FORBIDDEN_COLUMNS.get(table, set()) & actual:
                        failures.append(f"{table}: retired columns still present {sorted(forbidden)}")
                if "content_strategies" in table_names:
                    failures.append("retired table still present: content_strategies")

                actual_fks: set[tuple[str, str, str, str, str]] = set()
                for table in REQUIRED_COLUMNS:
                    if table not in table_names:
                        continue
                    for fk in inspector.get_foreign_keys(table):
                        options = fk.get("options") or {}
                        referred_columns = fk.get("referred_columns") or []
                        for local, remote in zip(
                            fk.get("constrained_columns") or [],
                            referred_columns,
                            strict=True,
                        ):
                            actual_fks.add(
                                (
                                    table,
                                    local,
                                    fk["referred_table"],
                                    remote,
                                    str(options.get("ondelete", "NO ACTION")).upper(),
                                )
                            )
                for required_fk in sorted(REQUIRED_FOREIGN_KEYS):
                    if required_fk not in actual_fks:
                        failures.append(f"missing foreign-key contract: {required_fk}")

                unique_names: set[str] = set()
                for table in REQUIRED_COLUMNS:
                    if table not in table_names:
                        continue
                    unique_names.update(
                        constraint["name"]
                        for constraint in inspector.get_unique_constraints(table)
                        if constraint.get("name")
                    )
                    unique_names.update(
                        index["name"]
                        for index in inspector.get_indexes(table)
                        if index.get("unique") and index.get("name")
                    )
                if missing := REQUIRED_UNIQUE_INDEXES - unique_names:
                    failures.append(f"missing unique indexes: {sorted(missing)}")

            await connection.run_sync(inspect_contract)
    finally:
        await engine.dispose()
    return failures


async def main() -> int:
    failures = await verify()
    if failures:
        print("North Star database contract FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("North Star database contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
