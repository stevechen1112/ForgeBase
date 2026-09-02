"""Read-only export required before migration 0102 removes CRM sales fields.

The output is sensitive operational history.  Store it with the deployment
backup, never as a public CI artifact and never commit it to Git.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings


QUERY = text(
    """
    SELECT id, tenant_id, rfq_number, status, first_response_at, quote_sent_at,
           next_follow_up_at, lost_reason, won_reason, deal_amount, deal_currency,
           sla_due_at, sla_breached, closed_at, quality_score,
           quality_reasons_json, created_at, updated_at
    FROM rfq_requests
    ORDER BY tenant_id, created_at, id
    """
)


def _json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


async def export(output: Path) -> dict:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            rows = (await connection.execute(QUERY)).mappings().all()
    finally:
        await engine.dispose()

    records = [
        {key: _json_value(value) for key, value in row.items()}
        for row in rows
    ]
    payload = {
        "schema": "forgebase-retired-rfq-sales-data-v1",
        "record_count": len(records),
        "records": records,
    }
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    try:
        os.chmod(output, 0o600)
    except OSError:
        pass
    return {
        "output": str(output.resolve()),
        "record_count": len(records),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new protected path")
    print(json.dumps(asyncio.run(export(args.output)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
