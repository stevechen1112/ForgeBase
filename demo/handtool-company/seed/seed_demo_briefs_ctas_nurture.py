#!/usr/bin/env python3
"""
Demo 補充 Seed — Page Briefs、CTAs、Nurture Sequences
為 Demo 文件中第一部分（1-3、1-4）、3-7、3-8 章節提供所需資料。

執行方式：
  cd /Users/yuchuchen/Desktop/ForgeBase/api
  source .venv/bin/activate
  python3 ../demo/handtool-company/seed/seed_demo_briefs_ctas_nurture.py
"""

import asyncio
import uuid
from datetime import datetime

import asyncpg

# ==============================================================
# 設定
# ==============================================================
DB_URL = "postgresql://forgebase:forgebase_dev@localhost:5432/forgebase"  # pragma: allowlist secret -- local-only demo
ADMIN_EMAIL = "admin@forgebase.com"

NOW = datetime.utcnow()

# related_entity_key = product.model_number 或 application.slug（執行時動態解析）
BRIEFS = [
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "product",
        "target_slug": "1-2-in-drive-industrial-torque-wrench",
        "title_draft": "Professional 1/2 in Drive Torque Wrench for Automotive Service",
        "audience_persona": "Automotive aftermarket service technicians, procurement managers",
        "buyer_stage": "consideration",
        "primary_keyword": "industrial torque wrench 1/2 drive",
        "secondary_keywords": '["torque wrench automotive", "precision torque tool", "click torque wrench"]',
        "tone": "technical",
        "word_count_target": 800,
        "main_cta_key": "rfq_primary",
        "notes": "Focus on accuracy specs (±4%) and DIN ISO 6789 certification. Target European automotive service shops.",
        "related_entity_type": "product",
        "related_entity_key": "NFT-TW500",
        "brief_status": "draft",
        "ai_status": "pending",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "product",
        "target_slug": "digital-torque-adapter",
        "title_draft": "Digital Torque Adapter — Real-Time Torque Measurement for Industry 4.0",
        "audience_persona": "Industrial engineers, quality assurance managers, MRO procurement",
        "buyer_stage": "decision",
        "primary_keyword": "digital torque adapter Bluetooth",
        "secondary_keywords": '["electronic torque measurement", "Industry 4.0 torque tool", "smart torque wrench adapter"]',
        "tone": "technical",
        "word_count_target": 1000,
        "main_cta_key": "rfq_primary",
        "notes": "Emphasise Bluetooth connectivity, data logging, and compatibility with 1/4\", 3/8\", 1/2\" drives.",
        "related_entity_type": "product",
        "related_entity_key": "NFT-TWA120",
        "brief_status": "approved",
        "ai_status": "pending",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "application",
        "target_slug": "automotive-aftermarket-service",
        "title_draft": "Hand Tools for Automotive Aftermarket Service — Complete Workshop Solution",
        "audience_persona": "Workshop owners, service managers, automotive parts distributors",
        "buyer_stage": "awareness",
        "primary_keyword": "automotive service hand tools",
        "secondary_keywords": '["workshop tools for automotive", "professional mechanic tools", "torque tools for car repair"]',
        "tone": "authoritative",
        "word_count_target": 900,
        "main_cta_key": "catalog_download",
        "notes": "Highlight breadth of product range, CE & GS certifications, OEM supply capability.",
        "related_entity_type": "application",
        "related_entity_key": "automotive-aftermarket-service",
        "brief_status": "approved",
        "ai_status": "pending",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "product",
        "target_slug": "72-tooth-reversible-ratchet-handle",
        "title_draft": "72-Tooth Reversible Ratchet Handle — 5° Arc Swing for Tight Spaces",
        "audience_persona": "Professional mechanics, industrial maintenance technicians",
        "buyer_stage": "consideration",
        "primary_keyword": "72 tooth ratchet handle professional",
        "secondary_keywords": '["reversible ratchet", "fine tooth ratchet", "ratchet handle tight space"]',
        "tone": "technical",
        "word_count_target": 750,
        "main_cta_key": "rfq_primary",
        "notes": "Key differentiator: 5° arc swing in confined spaces.",
        "related_entity_type": "product",
        "related_entity_key": "NFT-RH372",
        "brief_status": "in_progress",
        "ai_status": "processing",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "product",
        "target_slug": "94-piece-metric-socket-tool-set",
        "title_draft": "94-Piece Metric Socket Tool Set — Complete Workshop Solution for Export",
        "audience_persona": "Wholesale buyers, tool distributors, B2B procurement",
        "buyer_stage": "decision",
        "primary_keyword": "94 piece socket set metric export",
        "secondary_keywords": '["metric socket tool set wholesale", "complete socket set manufacturer", "professional socket set OEM"]',
        "tone": "authoritative",
        "word_count_target": 850,
        "main_cta_key": "rfq_primary",
        "notes": "Emphasise MOQ flexibility, custom packaging, CE certification.",
        "related_entity_type": "product",
        "related_entity_key": "NFT-SS094",
        "brief_status": "completed",
        "ai_status": "done",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "application",
        "target_slug": "industrial-maintenance-and-mro",
        "title_draft": "Hand Tools for Industrial Maintenance & MRO — Reliability Under Pressure",
        "audience_persona": "Plant maintenance managers, MRO procurement specialists",
        "buyer_stage": "awareness",
        "primary_keyword": "industrial maintenance hand tools MRO",
        "secondary_keywords": '["MRO tools supplier", "maintenance repair operations tools", "industrial hand tools bulk"]',
        "tone": "authoritative",
        "word_count_target": 900,
        "main_cta_key": "rfq_primary",
        "notes": "Focus on durability metrics, ISO certifications, availability of replacement parts.",
        "related_entity_type": "application",
        "related_entity_key": "industrial-maintenance-and-mro",
        "brief_status": "published",
        "ai_status": "done",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "faq",
        "target_slug": "torque-wrench-calibration-faq",
        "title_draft": "Torque Wrench Calibration — Common Questions from Procurement Teams",
        "audience_persona": "Quality managers, procurement, technical buyers",
        "buyer_stage": "consideration",
        "primary_keyword": "torque wrench calibration FAQ",
        "secondary_keywords": '["how to calibrate torque wrench", "torque wrench accuracy", "ISO 6789 calibration"]',
        "tone": "friendly",
        "word_count_target": 600,
        "main_cta_key": "spec_download",
        "notes": "需補充：各型號的建議校準週期、送廠校準的費用參考。",
        "related_entity_type": None,
        "related_entity_key": None,
        "brief_status": "revision",
        "ai_status": "done",
        "locale": "en",
    },
    {
        "id": str(uuid.uuid4()),
        "target_page_type": "product",
        "target_slug": "digital-torque-adapter-de",
        "title_draft": "Digitaler Drehmomentadapter — Präzisionsmessung für die Industrie",
        "audience_persona": "Industrieeinkäufer, Fertigungsingenieure (Deutschland, Österreich, Schweiz)",
        "buyer_stage": "consideration",
        "primary_keyword": "digitaler Drehmomentadapter kaufen",
        "secondary_keywords": '["Drehmomentmessung digital", "Drehmomentadapter Bluetooth", "elektronisches Drehmomentwerkzeug"]',
        "tone": "technical",
        "word_count_target": 800,
        "main_cta_key": "rfq_primary",
        "notes": "DACH market focus. Emphasise DIN conformity, CE marking.",
        "related_entity_type": "product",
        "related_entity_key": "NFT-TWA120",
        "brief_status": "draft",
        "ai_status": "pending",
        "locale": "de",
    },
]


# ==============================================================
# CTAs（4 筆，對應 Cold / Warm / Hot / Sales-Ready）
# ==============================================================
CTAS = [
    {
        "id": str(uuid.uuid4()),
        "cta_key": "spec_download",
        "cta_type": "inline",
        "headline": "Download the Full Specification Sheet",
        "subheadline": "Get detailed technical specs, dimensional drawings, and test data.",
        "button_label": "Download Spec Sheet",
        "button_action": "open_rfq",
        "button_url": None,
        "bg_color": "#F0F9FF",
        "image_url": None,
        "locale": "en",
        "status": "active",
        "sort_order": 10,
    },
    {
        "id": str(uuid.uuid4()),
        "cta_key": "comparison_view",
        "cta_type": "banner",
        "headline": "See How We Compare",
        "subheadline": "Side-by-side comparison: NorthForge vs standard market options.",
        "button_label": "View Full Comparison",
        "button_action": "link",
        "button_url": "/comparisons/",
        "bg_color": "#EFF6FF",
        "image_url": None,
        "locale": "en",
        "status": "active",
        "sort_order": 20,
    },
    {
        "id": str(uuid.uuid4()),
        "cta_key": "rfq_primary",
        "cta_type": "banner",
        "headline": "Ready to Source? Request a Quote Now",
        "subheadline": "Get pricing, MOQ details, and lead time within 24 hours.",
        "button_label": "Request a Quote",
        "button_action": "open_rfq",
        "button_url": None,
        "bg_color": "#1A56DB",
        "image_url": None,
        "locale": "en",
        "status": "active",
        "sort_order": 30,
    },
    {
        "id": str(uuid.uuid4()),
        "cta_key": "engineer_consult",
        "cta_type": "popup",
        "headline": "Talk to Our Application Engineers",
        "subheadline": "Schedule a 30-minute technical consultation — no commitment required.",
        "button_label": "Book a Consultation",
        "button_action": "link",
        "button_url": "/contact/",
        "bg_color": "#064E3B",
        "image_url": None,
        "locale": "en",
        "status": "active",
        "sort_order": 40,
    },
]


# ==============================================================
# Nurture Sequences + Steps（2 個序列）
# ==============================================================
SEQ1_ID = str(uuid.uuid4())
SEQ2_ID = str(uuid.uuid4())

NURTURE_SEQUENCES = [
    {
        "id": SEQ1_ID,
        "name": "Warm Visitor — Product Interest Follow-Up",
        "description": "3-step sequence for Warm-stage visitors who browsed products but haven't submitted an RFQ after 14 days.",
        "trigger_type": "manual",
        "trigger_value": None,
        "is_active": True,
        "allow_re_enrollment": False,
    },
    {
        "id": SEQ2_ID,
        "name": "Spec Sheet Download — Post-Download Nurture",
        "description": "4-step sequence triggered immediately after a contact downloads a spec sheet. Goal: move from Interest to RFQ submission.",
        "trigger_type": "download_gate",
        "trigger_value": None,
        "is_active": True,
        "allow_re_enrollment": True,
    },
]

NURTURE_STEPS = [
    # Sequence 1 — Warm Visitor Follow-Up
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ1_ID,
        "step_order": 0,
        "delay_days": 0,
        "subject": "Your inquiry about NorthForge hand tools",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>We noticed you've been exploring our torque and ratchet tools. Can I send you our latest export catalog and pricing sheet?</p><p>— NorthForge Sales Team</p>",
        "text_body": "Hi {{contact.first_name}},\n\nWe noticed you've been exploring our torque and ratchet tools. Can I send you our latest export catalog and pricing sheet?\n\n— NorthForge Sales Team",
        "from_name": "NorthForge Sales",
        "from_email": "sales@northforge-tools.com",
    },
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ1_ID,
        "step_order": 1,
        "delay_days": 5,
        "subject": "NorthForge: Case study — how a German MRO distributor reduced tool costs by 18%",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>I wanted to share a quick case study — a German MRO distributor recently switched to NorthForge torque tools and reduced their per-unit tool spend by 18% while maintaining ISO 6789 compliance.</p><p>Would a similar analysis be useful for your sourcing team?</p>",
        "text_body": "Hi {{contact.first_name}},\n\nI wanted to share a quick case study — a German MRO distributor recently switched to NorthForge torque tools and reduced their per-unit tool spend by 18% while maintaining ISO 6789 compliance.\n\nWould a similar analysis be useful for your sourcing team?",
        "from_name": "NorthForge Sales",
        "from_email": "sales@northforge-tools.com",
    },
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ1_ID,
        "step_order": 2,
        "delay_days": 10,
        "subject": "Last step — request a sample batch for evaluation",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>We'd like to offer you a sample evaluation batch — 5 units of any model, shipped to your facility at our cost.</p><p>If you'd like to proceed, simply reply to this email with your shipping address and preferred model numbers.</p>",
        "text_body": "Hi {{contact.first_name}},\n\nWe'd like to offer you a sample evaluation batch — 5 units of any model, shipped to your facility at our cost.\n\nIf you'd like to proceed, simply reply to this email with your shipping address and preferred model numbers.",
        "from_name": "NorthForge Sales",
        "from_email": "sales@northforge-tools.com",
    },
    # Sequence 2 — Post Download Nurture
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ2_ID,
        "step_order": 0,
        "delay_days": 0,
        "subject": "Your NorthForge spec sheet is ready — plus a few extras",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>Thank you for downloading our specification sheet. Attached are two additional resources: our full ISO certification documents and a comparative test report.</p>",
        "text_body": "Hi {{contact.first_name}},\n\nThank you for downloading our specification sheet. Attached are two additional resources: our full ISO certification documents and a comparative test report.",
        "from_name": "NorthForge Technical Team",
        "from_email": "tech@northforge-tools.com",
    },
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ2_ID,
        "step_order": 1,
        "delay_days": 3,
        "subject": "Quick question about your application",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>I noticed you downloaded specs for our {{product.name}}. I had a quick question — are you sourcing for automotive, industrial MRO, or another application?</p><p>Your answer will help me send you the most relevant pricing and lead time info.</p>",
        "text_body": "Hi {{contact.first_name}},\n\nI noticed you downloaded specs for our product. I had a quick question — are you sourcing for automotive, industrial MRO, or another application?\n\nYour answer will help me send you the most relevant pricing and lead time info.",
        "from_name": "NorthForge Sales",
        "from_email": "sales@northforge-tools.com",
    },
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ2_ID,
        "step_order": 2,
        "delay_days": 8,
        "subject": "NorthForge pricing for your volume range",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>Based on typical order volumes from buyers in your sector, I've prepared a rough pricing estimate. Would you like me to send it over?</p>",
        "text_body": "Hi {{contact.first_name}},\n\nBased on typical order volumes from buyers in your sector, I've prepared a rough pricing estimate. Would you like me to send it over?",
        "from_name": "NorthForge Sales",
        "from_email": "sales@northforge-tools.com",
    },
    {
        "id": str(uuid.uuid4()),
        "sequence_id": SEQ2_ID,
        "step_order": 3,
        "delay_days": 15,
        "subject": "One last thing before I close this thread",
        "html_body": "<p>Hi {{contact.first_name}},</p><p>I'll close out this follow-up sequence, but wanted to leave the door open — if your sourcing timeline shifts or you have questions about our product range, just reply here and I'll get back to you within 4 hours.</p>",
        "text_body": "Hi {{contact.first_name}},\n\nI'll close out this follow-up sequence, but wanted to leave the door open — if your sourcing timeline shifts or you have questions about our product range, just reply here and I'll get back to you within 4 hours.",
        "from_name": "NorthForge Sales",
        "from_email": "sales@northforge-tools.com",
    },
]


# ==============================================================
# 匯入邏輯
# ==============================================================
async def resolve_related_id(conn, entity_type, key):
    if not entity_type or not key:
        return None
    if entity_type == "product":
        return await conn.fetchval(
            "SELECT id FROM products WHERE model_number = $1 LIMIT 1", key
        )
    if entity_type == "application":
        return await conn.fetchval(
            "SELECT id FROM applications WHERE slug = $1 LIMIT 1", key
        )
    return None


async def seed():
    conn = await asyncpg.connect(DB_URL)
    print("Connected to DB")

    admin_user_id = await conn.fetchval(
        "SELECT id FROM users WHERE email = $1 LIMIT 1", ADMIN_EMAIL
    )
    if not admin_user_id:
        raise RuntimeError(
            f"找不到 admin 使用者 {ADMIN_EMAIL}。請先確認 API seed_admin / 登入帳號存在。"
        )
    print(f"Admin user: {admin_user_id}")

    # --- Page Briefs ---
    existing_briefs = await conn.fetchval("SELECT COUNT(*) FROM page_briefs")
    if existing_briefs > 0:
        print(f"⚠️  page_briefs 已有 {existing_briefs} 筆，跳過（如需重建請先手動清空）")
    else:
        inserted = 0
        for b in BRIEFS:
            related_id = await resolve_related_id(
                conn, b.get("related_entity_type"), b.get("related_entity_key")
            )
            if b.get("related_entity_key") and not related_id:
                print(
                    f"  ⚠  找不到 related entity {b.get('related_entity_type')}:{b.get('related_entity_key')}，略過 brief {b['target_slug']}"
                )
                continue
            await conn.execute(
                """
                INSERT INTO page_briefs (
                    id, target_page_type, target_slug, title_draft, audience_persona,
                    buyer_stage, primary_keyword, secondary_keywords, tone,
                    word_count_target, main_cta_key, notes,
                    related_entity_type, related_entity_id,
                    brief_status, ai_status, locale, created_by, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12,
                    $13, $14,
                    $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT DO NOTHING
                """,
                uuid.UUID(b["id"]),
                b["target_page_type"], b["target_slug"], b["title_draft"], b["audience_persona"],
                b["buyer_stage"], b["primary_keyword"], b["secondary_keywords"], b["tone"],
                b["word_count_target"], b["main_cta_key"], b["notes"],
                b["related_entity_type"],
                related_id,
                b["brief_status"], b["ai_status"], b["locale"],
                admin_user_id, NOW, NOW,
            )
            inserted += 1
        print(f"✅ page_briefs: 插入 {inserted} 筆")
        rows = await conn.fetch("SELECT brief_status, COUNT(*) as cnt FROM page_briefs GROUP BY brief_status ORDER BY brief_status")
        for r in rows:
            print(f"   {r['brief_status']}: {r['cnt']} 筆")

    # --- CTAs ---
    existing_ctas = await conn.fetchval("SELECT COUNT(*) FROM ctas")
    if existing_ctas > 0:
        print(f"⚠️  ctas 已有 {existing_ctas} 筆，跳過")
    else:
        for c in CTAS:
            await conn.execute(
                """
                INSERT INTO ctas (
                    id, cta_key, cta_type, headline, subheadline,
                    button_label, button_action, button_url,
                    bg_color, image_url, locale, status, sort_order,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8,
                    $9, $10, $11, $12, $13,
                    $14, $15
                )
                ON CONFLICT DO NOTHING
                """,
                uuid.UUID(c["id"]),
                c["cta_key"], c["cta_type"], c["headline"], c["subheadline"],
                c["button_label"], c["button_action"], c["button_url"],
                c["bg_color"], c["image_url"], c["locale"], c["status"], c["sort_order"],
                NOW, NOW,
            )
        print(f"✅ ctas: 插入 {len(CTAS)} 筆")

    # --- Nurture Sequences ---
    # 若表不存在則跳過（部分環境可能未啟用 nurture）
    has_nurture = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'nurture_sequences')"
    )
    if not has_nurture:
        print("⚠️  nurture_sequences 表不存在，跳過 nurture seed")
    else:
        existing_seq = await conn.fetchval("SELECT COUNT(*) FROM nurture_sequences")
        if existing_seq > 0:
            print(f"⚠️  nurture_sequences 已有 {existing_seq} 筆，跳過")
        else:
            for s in NURTURE_SEQUENCES:
                await conn.execute(
                    """
                    INSERT INTO nurture_sequences (
                        id, name, description, trigger_type, trigger_value,
                        is_active, allow_re_enrollment, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT DO NOTHING
                    """,
                    uuid.UUID(s["id"]),
                    s["name"], s["description"], s["trigger_type"], s["trigger_value"],
                    s["is_active"], s["allow_re_enrollment"], NOW, NOW,
                )
            print(f"✅ nurture_sequences: 插入 {len(NURTURE_SEQUENCES)} 筆")

            for step in NURTURE_STEPS:
                await conn.execute(
                    """
                    INSERT INTO nurture_steps (
                        id, sequence_id, step_order, delay_days,
                        subject, html_body, text_body,
                        from_name, from_email, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT DO NOTHING
                    """,
                    uuid.UUID(step["id"]),
                    uuid.UUID(step["sequence_id"]),
                    step["step_order"], step["delay_days"],
                    step["subject"], step["html_body"], step["text_body"],
                    step["from_name"], step["from_email"], NOW, NOW,
                )
            print(f"✅ nurture_steps: 插入 {len(NURTURE_STEPS)} 筆")

    await conn.close()
    print("\n🎉 Demo 資料補充完成！")
    print("現在可以展示：")
    print("  Page Brief 列表（含多種 brief_status）")
    print("  Dynamic CTA（spec_download / comparison_view / rfq_primary / engineer_consult）")
    print("  Nurture 序列（若表存在）")


if __name__ == "__main__":
    asyncio.run(seed())
