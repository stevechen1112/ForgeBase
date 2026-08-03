"""Backfill Intent Score 2.0 facets for existing visitors (migration 0050).

既有訪客在 facets 欄位上線前累積的歷史事件不會自動反映到新欄位；
本腳本依 tracking_events 歷史重新計算每位訪客的 facet 分數與
intent_explanation（「為何 Hot」）。

Usage（需 DATABASE_URL）:
    python scripts/backfill_visitor_facets.py --tenant <tenant_uuid>   # 單一租戶
    python scripts/backfill_visitor_facets.py --all                     # 全部
    python scripts/backfill_visitor_facets.py --tenant <uuid> --dry-run # 試算
"""
import argparse
import asyncio
import sys
from collections import defaultdict

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select

sys.path.insert(0, ".")

from app.core.config import settings
from app.models.rfq_request import RFQRequest
from app.models.tracking_event import TrackingEvent
from app.models.visitor import Visitor
from app.services.intent_facets import (
    build_intent_explanation,
    recompute_facets,
)


async def run(tenant_id: str | None, dry_run: bool) -> None:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        v_q = select(Visitor)
        if tenant_id:
            v_q = v_q.where(Visitor.tenant_id == tenant_id)
        visitors = (await session.exec(v_q)).all()

        ev_q = select(TrackingEvent).order_by(TrackingEvent.timestamp.asc())
        if tenant_id:
            ev_q = ev_q.where(TrackingEvent.tenant_id == tenant_id)
        events = (await session.exec(ev_q)).all()

        by_visitor: dict[str, list[TrackingEvent]] = defaultdict(list)
        for e in events:
            if e.visitor_id:
                by_visitor[str(e.visitor_id)].append(e)

        rfq_q = select(RFQRequest.visitor_id).where(RFQRequest.visitor_id.is_not(None)).distinct()
        if tenant_id:
            rfq_q = rfq_q.where(RFQRequest.tenant_id == tenant_id)
        rfq_visitors = {str(x) for x in (await session.exec(rfq_q)).all() if x}

        updated = 0
        for v in visitors:
            evs = by_visitor.get(str(v.visitor_id), [])
            facets = recompute_facets(evs)
            explanation = build_intent_explanation(
                list(reversed(evs[-50:])),
                has_rfq_record=str(v.visitor_id) in rfq_visitors,
            )
            if dry_run:
                if any(facets.values()) or explanation:
                    print(f"[dry] {v.visitor_id} facets={facets} expl={explanation!r}")
                continue
            v.facet_product_interest = facets["product_interest"]
            v.facet_trust_validation = facets["trust_validation"]
            v.facet_procurement_readiness = facets["procurement_readiness"]
            v.facet_urgency = facets["urgency"]
            v.intent_explanation = explanation or None
            session.add(v)
            updated += 1

        if not dry_run:
            await session.commit()
            print(f"Backfilled {updated} visitors"
                  f"{' (tenant=' + tenant_id + ')' if tenant_id else ''}")
        else:
            print(f"[dry-run] {len(visitors)} visitors scanned")

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill visitor intent facets")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--tenant", help="Tenant UUID to backfill")
    g.add_argument("--all", action="store_true", help="Backfill all tenants")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(run(None if args.all else args.tenant, args.dry_run))


if __name__ == "__main__":
    main()
