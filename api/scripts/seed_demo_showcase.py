"""Idempotently seed a rich, clearly synthetic sales showcase tenant.

The script resolves the tenant through an explicitly named demo user, refuses
to run unless the tenant name contains ``demo``, and never sends email or
creates outbound jobs.  Re-running it updates the same deterministic records
instead of growing the database indefinitely.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlmodel import col, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.models  # noqa: F401 - register SQLModel relationships
from app.core.datetime import utcnow_naive
from app.db.session import AsyncSessionLocal
from app.models.chat import ChatMessage, ChatSession
from app.models.contact import Contact
from app.models.notification_log import NotificationLog
from app.models.page import Page
from app.models.product import Product
from app.models.reply_template import ReplyTemplate
from app.models.rfq_event import RFQEvent
from app.models.rfq_note import RFQNote
from app.models.rfq_request import RFQProductLink, RFQRequest
from app.models.segment import Segment
from app.models.site_profile import SiteProfile
from app.models.tenant import Tenant
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.user import User
from app.models.visitor import Visitor

RUN_ID = "forgebase-showcase-v1"
NAMESPACE = uuid.UUID("ff28c40d-1dc3-4a6c-82f8-ddddbe9b43c1")

BUYERS = [
    ("Axis Technik GmbH", "Hannah Weber", "DE", "Europe/Berlin"),
    ("NOVA Supply Inc.", "Rachel Adams", "US", "America/Chicago"),
    ("Maki Industries", "Kenji Sato", "JP", "Asia/Tokyo"),
    ("NordWerk AB", "Erik Lindberg", "SE", "Europe/Stockholm"),
    ("Apex Motion", "Olivia Chen", "SG", "Asia/Singapore"),
    ("Vertex Automation", "Daniel Miller", "US", "America/New_York"),
    ("Rhein Precision", "Lukas Hoffmann", "DE", "Europe/Berlin"),
    ("Hikari Systems", "Aiko Tanaka", "JP", "Asia/Tokyo"),
    ("Orion Mobility", "Sophie Martin", "FR", "Europe/Paris"),
    ("BluePeak Controls", "James Wilson", "GB", "Europe/London"),
    ("Hanul Robotics", "Min-jun Park", "KR", "Asia/Seoul"),
    ("Pacific Instrument", "Emma Wang", "AU", "Australia/Sydney"),
    ("Titan Components", "William Brown", "CA", "America/Toronto"),
    ("Sakura Engineering", "Yui Nakamura", "JP", "Asia/Tokyo"),
    ("Helvetic Motion", "Noah Meier", "CH", "Europe/Zurich"),
    ("Delta Process", "Mia Schmidt", "NL", "Europe/Amsterdam"),
]

RFQ_STATUSES = (
    ["new"] * 4
    + ["assigned"] * 4
    + ["in_progress"] * 4
    + ["quoted"] * 5
    + ["negotiation"] * 7
    + ["won"] * 4
)
RFQ_DAY_OFFSETS = [0] * 7 + [1] * 5 + [2] * 4 + [3] * 4 + [4] * 3 + [5] * 3 + [6] * 2


def stable_id(tenant_id: uuid.UUID, kind: str, index: int) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{tenant_id}:{RUN_ID}:{kind}:{index}")


async def upsert_id(
    session, model, row_id: uuid.UUID, values: dict[str, Any], *, pk: str = "id"
):
    row = await session.get(model, row_id)
    if row is None:
        row = model(**{pk: row_id}, **values)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    session.add(row)
    await session.flush()
    return row


async def seed(user_email: str) -> dict[str, Any]:
    now = utcnow_naive()
    async with AsyncSessionLocal() as session:
        user = (
            await session.exec(select(User).where(User.email == user_email))
        ).first()
        if user is None or user.tenant_id is None:
            raise RuntimeError("The requested demo user or tenant was not found")
        tenant = await session.get(Tenant, user.tenant_id)
        if tenant is None or "demo" not in tenant.name.casefold():
            raise RuntimeError(
                "Refusing to seed a tenant whose name is not explicitly marked Demo"
            )
        profile = (
            await session.exec(
                select(SiteProfile).where(SiteProfile.tenant_id == tenant.id)
            )
        ).first()
        if profile is None:
            raise RuntimeError("Demo tenant has no site profile")

        products = list(
            (
                await session.exec(
                    select(Product)
                    .where(
                        Product.tenant_id == tenant.id, Product.status == "published"
                    )
                    .order_by(col(Product.display_priority).desc())
                )
            ).all()
        )

        contacts: list[Contact] = []
        for index, (company, full_name, country, _) in enumerate(BUYERS):
            contact_id = stable_id(tenant.id, "contact", index)
            contact = await upsert_id(
                session,
                Contact,
                contact_id,
                {
                    "tenant_id": tenant.id,
                    "email": f"buyer{index + 1:02d}.{RUN_ID}@example.com",
                    "full_name": full_name,
                    "company_name": company,
                    "phone": f"+00 555 010{index:02d}",
                    "country": country,
                    "job_title": "Procurement Manager"
                    if index % 2 == 0
                    else "Sourcing Engineer",
                    "source_page": "/demo/showcase/contact",
                    "how_did_you_find_us": [
                        "google",
                        "trade_show",
                        "referral",
                        "linkedin",
                    ][index % 4],
                    "source_type": "demo_showcase",
                    "notes": "[DEMO] Synthetic buyer used only for the ForgeBase sales showcase.",
                    "created_at": now - timedelta(days=21 - index % 12),
                    "updated_at": now - timedelta(hours=index % 8),
                },
            )
            contacts.append(contact)

        visitors: list[Visitor] = []
        countries = [buyer[2] for buyer in BUYERS]
        for index in range(120):
            visitor_id = stable_id(tenant.id, "visitor", index)
            first_seen = now - timedelta(days=index % 28, hours=index % 11)
            linked_contact = contacts[index] if index < len(contacts) else None
            visitor = await upsert_id(
                session,
                Visitor,
                visitor_id,
                {
                    "tenant_id": tenant.id,
                    "first_seen": first_seen,
                    "last_seen": now - timedelta(minutes=5 + index * 3),
                    "last_activity_at": now - timedelta(minutes=5 + index * 3),
                    "total_visits": 1 + index % 7,
                    "total_page_views": 3 + index % 19,
                    "device_type": ["desktop", "desktop", "mobile", "tablet"][
                        index % 4
                    ],
                    "country": countries[index % len(countries)],
                    "contact_id": linked_contact.id if linked_contact else None,
                    "analytics_consent_status": "granted",
                    "consent_updated_at": first_seen,
                    "is_test_data": False,
                    "test_run_id": RUN_ID,
                    "created_at": first_seen,
                    "updated_at": now - timedelta(minutes=index % 90),
                },
                pk="visitor_id",
            )
            visitors.append(visitor)

            session_id = stable_id(tenant.id, "session", index)
            session_row = await upsert_id(
                session,
                TrackingSession,
                session_id,
                {
                    "visitor_id": visitor_id,
                    "tenant_id": tenant.id,
                    "start_time": first_seen,
                    "end_time": first_seen + timedelta(minutes=12 + index % 35),
                    "page_count": 4 + index % 8,
                    "entry_page": "/en",
                    "exit_page": "/en/rfq" if index % 5 == 0 else "/en/products",
                    "traffic_source": [
                        "organic",
                        "direct",
                        "referral",
                        "paid",
                        "social",
                    ][index % 5],
                    "utm_source": "demo-showcase",
                    "utm_medium": "synthetic",
                    "utm_campaign": "phase2-demo",
                    "device_type": visitor.device_type,
                    "country": visitor.country,
                    "is_test_data": False,
                    "test_run_id": RUN_ID,
                    "created_at": first_seen,
                    "updated_at": now,
                },
                pk="session_id",
            )
            for event_index, event_name in enumerate(
                ["page_view", "product_view", "spec_download", "cta_click"]
            ):
                event_id = stable_id(tenant.id, f"event-{index}", event_index)
                product = (
                    products[(index + event_index) % len(products)]
                    if products
                    else None
                )
                await upsert_id(
                    session,
                    TrackingEvent,
                    event_id,
                    {
                        "tenant_id": tenant.id,
                        "event_name": event_name,
                        "timestamp": first_seen + timedelta(minutes=event_index * 3),
                        "session_id": session_row.session_id,
                        "visitor_id": visitor_id,
                        "page_url": f"/en/products/{product.slug}"
                        if product
                        else "/en/products",
                        "page_type": "product" if event_index else "home",
                        "page_id": product.id if product else None,
                        "locale": "en",
                        "traffic_source": session_row.traffic_source,
                        "device_type": visitor.device_type,
                        "country": visitor.country,
                        "properties": json.dumps({"demo": True, "showcase": RUN_ID}),
                        "is_test_data": False,
                        "test_run_id": RUN_ID,
                    },
                    pk="event_id",
                )

        rfqs: list[RFQRequest] = []
        for index, status in enumerate(RFQ_STATUSES):
            contact = contacts[index % len(contacts)]
            company, _, country, timezone_name = BUYERS[index % len(BUYERS)]
            created_at = now - timedelta(
                days=RFQ_DAY_OFFSETS[index], hours=(index * 3) % 20
            )
            is_new = status == "new"
            quote_sent_at = (
                created_at + timedelta(hours=18 + index % 6)
                if status in {"quoted", "negotiation", "won"}
                else None
            )
            first_response_at = (
                None if index < 2 else created_at + timedelta(hours=2 + index % 7)
            )
            next_follow_up_at = None
            if index == 0:
                next_follow_up_at = now - timedelta(hours=3)
            elif index == 1:
                next_follow_up_at = now - timedelta(minutes=45)
            elif index in {2, 3}:
                next_follow_up_at = now + timedelta(hours=index + 1)
            elif status in {"assigned", "in_progress", "quoted", "negotiation"}:
                next_follow_up_at = now + timedelta(days=1 + index % 6)

            quality_score = (
                [94, 91, 88, 86, 84, 82, 80][index] if index < 7 else 48 + index % 29
            )
            rfq_id = stable_id(tenant.id, "rfq", index)
            deal_amount = (
                Decimal(str([28000, 46500, 72000, 93000][index - 24]))
                if status == "won"
                else None
            )
            rfq = await upsert_id(
                session,
                RFQRequest,
                rfq_id,
                {
                    "tenant_id": tenant.id,
                    "rfq_number": f"DEMO-P2-{index + 1:03d}",
                    "contact_id": contact.id,
                    "visitor_id": visitors[index].visitor_id,
                    "form_data": json.dumps(
                        {
                            "full_name": contact.full_name,
                            "company_name": company,
                            "email": contact.email,
                            "country": country,
                            "quantity": [
                                "500 pcs",
                                "1,000 pcs",
                                "5,000 pcs",
                                "Annual program",
                            ][index % 4],
                            "timeline": ["Immediate", "1–3 months", "3–6 months"][
                                index % 3
                            ],
                            "specifications": "[DEMO] Drawing review, material traceability and inspection report requested.",
                            "message": "Synthetic showcase enquiry. No external reply is expected.",
                        }
                    ),
                    "attribution_json": json.dumps(
                        {"campaign": "phase2-demo", "synthetic": True}
                    ),
                    "status": status,
                    "assigned_to": None if is_new else user.id,
                    "priority": "urgent"
                    if index == 0
                    else "high"
                    if index < 6
                    else "normal",
                    "source_page": [
                        "/en/products/servo-housing",
                        "/en/quality",
                        "/en/rfq",
                    ][index % 3],
                    "first_response_at": first_response_at,
                    "quote_sent_at": quote_sent_at,
                    "next_follow_up_at": next_follow_up_at,
                    "won_reason": "[DEMO] Technical evidence and responsive follow-up"
                    if status == "won"
                    else None,
                    "deal_amount": deal_amount,
                    "deal_currency": "USD",
                    "is_spam": False,
                    "is_test_data": False,
                    "test_run_id": RUN_ID,
                    "buyer_timezone": timezone_name,
                    "sla_due_at": created_at + timedelta(hours=24),
                    "sla_breached": index < 2,
                    "quality_score": quality_score,
                    "quality_reasons_json": json.dumps(
                        [
                            "需求數量與時程完整",
                            "已查看產品與品質資料",
                            "公司與聯絡資料齊全",
                        ],
                        ensure_ascii=False,
                    ),
                    "incoterm": ["FOB", "EXW", "CIF"][index % 3],
                    "annual_volume": ["5,000 pcs", "12,000 pcs", "25,000 pcs"][
                        index % 3
                    ],
                    "is_trial_order": index % 4 == 0,
                    "required_certs_json": json.dumps(
                        ["FAIR", "Material traceability"]
                    ),
                    "target_price": "Demo only",
                    "created_at": created_at,
                    "updated_at": now - timedelta(minutes=index * 2),
                    "closed_at": now - timedelta(days=index % 3)
                    if status == "won"
                    else None,
                },
            )
            rfqs.append(rfq)

            product = products[index % len(products)] if products else None
            if product:
                link = await session.get(RFQProductLink, (rfq.id, product.id))
                if link is None:
                    session.add(RFQProductLink(rfq_id=rfq.id, product_id=product.id))

            event_id = stable_id(tenant.id, "rfq-event", index)
            await upsert_id(
                session,
                RFQEvent,
                event_id,
                {
                    "rfq_id": rfq.id,
                    "tenant_id": tenant.id,
                    "actor_id": user.id,
                    "event_type": "created" if is_new else "status_changed",
                    "summary": f"[DEMO] {company} enquiry is currently {status}",
                    "detail": json.dumps({"status": status, "showcase": RUN_ID}),
                    "created_at": created_at,
                },
            )
            if index < 6:
                note_id = stable_id(tenant.id, "rfq-note", index)
                await upsert_id(
                    session,
                    RFQNote,
                    note_id,
                    {
                        "tenant_id": tenant.id,
                        "rfq_id": rfq.id,
                        "author_id": user.id,
                        "body": "[DEMO] Confirm drawing revision, annual volume and inspection evidence before the next response.",
                        "created_at": created_at + timedelta(hours=1),
                    },
                )

        draft_pages = [
            ("demo-ja-servo-housing", "Servo Drive Housing 日文內容待確認"),
            ("demo-ja-sensor-sleeve", "Sensor Sleeve 日文內容待確認"),
        ]
        for index, (slug, title) in enumerate(draft_pages):
            page_id = stable_id(tenant.id, "draft-page", index)
            await upsert_id(
                session,
                Page,
                page_id,
                {
                    "tenant_id": tenant.id,
                    "page_type": "landing",
                    "slug": slug,
                    "title": title,
                    "subtitle": "[DEMO] 客戶語言草稿，確認後才會公開。",
                    "body": "<p>Demonstration translation draft for review.</p>",
                    "locale": "ja",
                    "status": "draft",
                    "noindex": True,
                    "created_at": now - timedelta(days=2),
                    "updated_at": now - timedelta(hours=index + 2),
                },
            )

        segment_rows = [
            (
                "德國近期重複訪客",
                "近 14 天來自德國且有重複造訪",
                [{"type": "country", "op": "eq", "value": "DE"}],
            ),
            (
                "已下載規格書的買家",
                "曾下載產品規格書，適合人工檢查後跟進",
                [
                    {
                        "type": "event_count",
                        "event_name": "spec_download",
                        "op": "gte",
                        "value": 1,
                        "within_days": 30,
                    }
                ],
            ),
            (
                "本週高互動訪客",
                "近 7 天產品瀏覽達 3 次以上",
                [
                    {
                        "type": "event_count",
                        "event_name": "product_view",
                        "op": "gte",
                        "value": 3,
                        "within_days": 7,
                    }
                ],
            ),
        ]
        for index, (name, description, conditions) in enumerate(segment_rows):
            await upsert_id(
                session,
                Segment,
                stable_id(tenant.id, "segment", index),
                {
                    "tenant_id": tenant.id,
                    "name": name,
                    "description": description,
                    "conditions": json.dumps(conditions, ensure_ascii=False),
                    "combinator": "AND",
                    "created_by": user.id,
                    "created_at": now - timedelta(days=5 - index),
                    "updated_at": now - timedelta(hours=index),
                },
            )

        reply_rows = [
            ("德國年度採購首封回覆", "DE"),
            ("樣品與檢驗文件確認", "US"),
            ("日本 OEM 規格確認", "JP"),
            ("報價後第 7 天跟進", None),
        ]
        for index, (name, country) in enumerate(reply_rows):
            await upsert_id(
                session,
                ReplyTemplate,
                stable_id(tenant.id, "reply-template", index),
                {
                    "tenant_id": tenant.id,
                    "name": name,
                    "product_line": "Precision Components",
                    "country": country,
                    "locale": "en",
                    "body": "Dear Buyer,\n\nThank you for your enquiry. This is a clearly marked demonstration reply template and will not be sent automatically.\n\nBest regards,\nForgeBase Demo Team",
                    "created_at": now - timedelta(days=12 - index),
                    "updated_at": now - timedelta(days=index),
                },
            )

        chat_prompts = [
            "Can you provide a material traceability report?",
            "What should be included with a drawing-led RFQ?",
            "How is the critical tolerance inspected?",
            "Can we start with prototypes before annual production?",
        ]
        for index, prompt in enumerate(chat_prompts):
            chat_id = stable_id(tenant.id, "chat", index)
            product = products[index % len(products)] if products else None
            chat = await upsert_id(
                session,
                ChatSession,
                chat_id,
                {
                    "tenant_id": tenant.id,
                    "visitor_id": visitors[index].visitor_id,
                    "session_id": stable_id(tenant.id, "session", index),
                    "context_page": f"/en/products/{product.slug}"
                    if product
                    else "/en/products",
                    "context_entity_type": "product",
                    "context_entity_id": product.id if product else None,
                    "locale": "en",
                    "started_at": now - timedelta(hours=index * 3 + 1),
                    "ended_at": None
                    if index == 0
                    else now - timedelta(hours=index * 3),
                    "status": "active" if index == 0 else "ended",
                    "message_count": 2,
                    "quality_rating": 5 - index % 2,
                    "admin_notes": "[DEMO] Synthetic product conversation for the showcase.",
                    "qualification_json": json.dumps(
                        {"synthetic": True, "needs_handoff": index == 0}
                    ),
                    "created_at": now - timedelta(hours=index * 3 + 1),
                    "updated_at": now - timedelta(hours=index * 3),
                },
            )
            messages = [
                ("user", prompt),
                (
                    "assistant",
                    "This demo tenant shows the published product and inspection context. A real quotation requires a drawing, revision, material, volume and target timing.",
                ),
            ]
            for message_index, (role, content) in enumerate(messages):
                await upsert_id(
                    session,
                    ChatMessage,
                    stable_id(tenant.id, f"chat-message-{index}", message_index),
                    {
                        "chat_session_id": chat.id,
                        "role": role,
                        "content": content,
                        "sources": json.dumps(
                            [{"type": "demo", "label": "Published AxisForm content"}]
                        )
                        if role == "assistant"
                        else None,
                        "grounding_status": "grounded" if role == "assistant" else None,
                        "created_at": chat.started_at
                        + timedelta(minutes=message_index * 2),
                    },
                )

        notifications = [
            ("new_rfq", "4 筆新詢價等待分派，其中 1 筆為急件。", "delivered"),
            (
                "daily_summary",
                "今日共有 6 項工作需要處理，其中 2 項已逾期。",
                "delivered",
            ),
            ("content_suggestion", "2 份日文產品內容等待人工確認。", "delivered"),
            (
                "chat_handoff",
                "德國訪客正在詢問材料追溯文件，建議由業務接手。",
                "delivered",
            ),
            ("new_rfq", "NOVA Supply 樣品詢價資料完整，尚未分派。", "delivered"),
        ]
        for index, (event_type, preview, status) in enumerate(notifications):
            await upsert_id(
                session,
                NotificationLog,
                stable_id(tenant.id, "notification", index),
                {
                    "tenant_id": tenant.id,
                    "user_id": user.id,
                    "channel": "in_app",
                    "event_type": event_type,
                    "event_ref_id": rfqs[index].id if event_type == "new_rfq" else None,
                    "message_preview": f"[DEMO] {preview}",
                    "status": status,
                    "error_detail": None,
                    "sent_at": now - timedelta(minutes=12 + index * 17),
                },
            )

        await session.commit()
        return {
            "schema_version": 1,
            "status": "seeded",
            "run_id": RUN_ID,
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "brand_name": profile.brand_name,
            "records": {
                "visitors": len(visitors),
                "contacts": len(contacts),
                "rfqs": len(rfqs),
                "won": sum(1 for row in rfqs if row.status == "won"),
                "draft_pages": len(draft_pages),
                "segments": len(segment_rows),
                "reply_templates": len(reply_rows),
                "chats": len(chat_prompts),
                "notifications": len(notifications),
            },
            "safety": {
                "synthetic_contacts_only": True,
                "outbound_jobs_created": 0,
                "email_sent": False,
                "idempotent": True,
            },
        }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the protected ForgeBase demo showcase"
    )
    parser.add_argument("--user-email", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to write without --apply")
    print(json.dumps(await seed(args.user_email), ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
