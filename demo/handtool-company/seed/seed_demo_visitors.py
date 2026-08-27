#!/usr/bin/env python3
"""
ForgeBase Demo — NorthForge Tools 訪客行為 Seed
===============================================
注入手工具產業相符的訪客軌跡、RFQ 與（可選）download-gate 留資。

執行前提：
  1. API 服務運行於 http://localhost:8000
  2. 先執行 import_demo_content.py

執行：
  FORGEBASE_ADMIN_PASSWORD='<至少 16 字元的密碼>' \
    python demo/handtool-company/seed/seed_demo_visitors.py
"""
from __future__ import annotations

import json
import os
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API_BASE = os.getenv("FORGEBASE_API_BASE", "http://localhost:8000/api/v1")
LOGIN_EMAIL = os.getenv("FORGEBASE_ADMIN_EMAIL", "admin@forgebase.com")
LOGIN_PASSWORD = os.getenv("FORGEBASE_ADMIN_PASSWORD", "")
# Public content list endpoints filter by X-Tenant-ID (JWT alone is not enough)
TENANT_ID = os.getenv("FORGEBASE_TENANT_ID", "d3dad494-2b93-4993-a55b-6ca847450b9b")

# 真實產品／分類／應用 slug（對齊 seed/*.json）
CAT_TORQUE = "torque-and-socket-tools"
CAT_ELEC = "insulated-electrical-tools"
CAT_AUTO = "automotive-service-tools"
P_TW250 = "1-4-in-drive-micrometer-torque-wrench"
P_TW380 = "3-8-in-drive-click-torque-wrench"
P_TW500 = "1-2-in-drive-industrial-torque-wrench"
P_TWA120 = "digital-torque-adapter"
P_RH372 = "72-tooth-reversible-ratchet-handle"
P_VDE6 = "6-piece-vde-insulated-screwdriver-set"
APP_AUTO = "automotive-aftermarket-service"
APP_MRO = "industrial-maintenance-and-mro"
APP_ELEC = "electrical-installation-and-utility-work"


def product_url(category: str, slug: str) -> str:
    return f"/products/{category}/{slug}/"


PERSONAS = [
    {
        "id": "p1",
        "label": "🔥 Thomas Bauer — Hot 採購（德國）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Bauer Werkzeuge GmbH",
        "country": "DE",
        "email": "thomas.bauer@bauer-werkzeuge.de",
        "full_name": "Thomas Bauer",
        "job_title": "Procurement Manager",
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 10, "source": "google"},
            {"event": "category_view", "url": f"/products/{CAT_TORQUE}/", "page_type": "category", "days_ago": 10},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 10},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW380), "page_type": "product", "days_ago": 10},
            {"event": "page_view", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 5, "source": "direct"},
            {"event": "faq_expand", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 5},
            {"event": "faq_expand", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 5},
            {"event": "faq_expand", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 5},
            {"event": "application_view", "url": f"/applications/{APP_MRO}/", "page_type": "application", "days_ago": 5},
            {"event": "cta_click", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 5},
            {"event": "return_visit", "url": f"/products/{CAT_TORQUE}/", "page_type": "category", "days_ago": 2, "source": "email"},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 2},
            {"event": "spec_download", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 2},
        ],
        "rfq": {
            "full_name": "Thomas Bauer",
            "email": "thomas.bauer@bauer-werkzeuge.de",
            "company_name": "Bauer Werkzeuge GmbH",
            "phone": "+49-89-1234567",
            "country": "DE",
            "job_title": "Procurement Manager",
            "quantity": "800 units / year, mixed SKUs",
            "specifications": "NFT-TW500 industrial torque wrench, ±4% accuracy, DIN ISO 6789. Need private-label packaging option and EU warehouse lead time.",
            "timeline": "3-6 months",
            "incoterms": "FOB",
            "message": "Evaluating Taiwan OEM partners for our MRO distributor line. Please quote NFT-TW500 and NFT-TW380 with MOQ and cert docs.",
            "how_did_you_find_us": "google",
            "consent": True,
            "source_page": product_url(CAT_TORQUE, P_TW500),
        },
    },
    {
        "id": "p2",
        "label": "✅ Sarah Mitchell — Sales-Ready 工程師（美國）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Pacific Tool Supply Inc.",
        "country": "US",
        "email": "s.mitchell@pacifictoolsupply.com",
        "full_name": "Sarah Mitchell",
        "job_title": "Senior Product Manager",
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 21, "source": "linkedin"},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TWA120), "page_type": "product", "days_ago": 21},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW380), "page_type": "product", "days_ago": 21},
            {"event": "application_view", "url": f"/applications/{APP_AUTO}/", "page_type": "application", "days_ago": 20},
            {"event": "comparison_view", "url": "/comparisons/", "page_type": "comparison", "days_ago": 18},
            {"event": "faq_expand", "url": product_url(CAT_TORQUE, P_TWA120), "page_type": "product", "days_ago": 18},
            {"event": "spec_download", "url": product_url(CAT_TORQUE, P_TWA120), "page_type": "product", "days_ago": 15},
            {"event": "return_visit", "url": f"/products/{CAT_TORQUE}/", "page_type": "category", "days_ago": 7, "source": "google"},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TWA120), "page_type": "product", "days_ago": 7},
            {"event": "cta_click", "url": product_url(CAT_TORQUE, P_TWA120), "page_type": "product", "days_ago": 7},
            {"event": "rfq_start", "url": "/rfq/", "page_type": "rfq", "days_ago": 7},
        ],
        "rfq": {
            "full_name": "Sarah Mitchell",
            "email": "s.mitchell@pacifictoolsupply.com",
            "company_name": "Pacific Tool Supply Inc.",
            "country": "US",
            "job_title": "Senior Product Manager",
            "quantity": "1,500 pcs initial, monthly replenishment",
            "specifications": "Digital angle torque wrench NFT-TWA120 with calibration cert. Need UL/CE docs and branded foam inserts.",
            "timeline": "immediate",
            "incoterms": "CIF",
            "annual_volume": "5000+",
            "message": "Active program for US automotive aftermarket. Formal quotation with lead time required this week.",
            "how_did_you_find_us": "linkedin",
            "consent": True,
            "source_page": product_url(CAT_TORQUE, P_TWA120),
        },
    },
    {
        "id": "p3",
        "label": "🟡 Kenji Tanaka — Warm 工程師（日本）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Tanaka Service Tools",
        "country": "JP",
        "email": None,
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 8, "source": "google"},
            {"event": "category_view", "url": f"/products/{CAT_AUTO}/", "page_type": "category", "days_ago": 8},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_RH372), "page_type": "product", "days_ago": 8},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW250), "page_type": "product", "days_ago": 8},
            {"event": "application_view", "url": f"/applications/{APP_AUTO}/", "page_type": "application", "days_ago": 6},
            {"event": "faq_expand", "url": product_url(CAT_TORQUE, P_RH372), "page_type": "product", "days_ago": 6},
            {"event": "return_visit", "url": product_url(CAT_TORQUE, P_RH372), "page_type": "product", "days_ago": 3, "source": "direct"},
        ],
    },
    {
        "id": "p4",
        "label": "❄️ Liu Wei — Cold 初訪（中國）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Unknown",
        "country": "CN",
        "email": None,
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 2, "source": "google"},
            {"event": "category_view", "url": "/products/", "page_type": "category_list", "days_ago": 2},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW250), "page_type": "product", "days_ago": 2},
        ],
    },
    {
        "id": "p5",
        "label": "🟡 Marco Rossi — Warm 採購（義大利）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Rossi Utensili S.r.l.",
        "country": "IT",
        "email": "m.rossi@rossiutensili.it",
        "full_name": "Marco Rossi",
        "job_title": "Purchasing Director",
        "behaviors": [
            {"event": "page_view", "url": "/certifications/", "page_type": "certifications", "days_ago": 14, "source": "referral"},
            {"event": "page_view", "url": f"/applications/{APP_MRO}/", "page_type": "application", "days_ago": 14},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW380), "page_type": "product", "days_ago": 14},
            {"event": "spec_download", "url": product_url(CAT_TORQUE, P_TW380), "page_type": "product", "days_ago": 13},
            {"event": "return_visit", "url": f"/products/{CAT_TORQUE}/", "page_type": "category", "days_ago": 4, "source": "google"},
            {"event": "product_view", "url": product_url(CAT_TORQUE, P_TW500), "page_type": "product", "days_ago": 4},
            {"event": "comparison_view", "url": "/comparisons/", "page_type": "comparison", "days_ago": 4},
        ],
        "download_gate": {
            "full_name": "Marco Rossi",
            "email": "m.rossi@rossiutensili.it",
            "company_name": "Rossi Utensili S.r.l.",
        },
    },
    {
        "id": "p6",
        "label": "🔥 Anna Kowalski — Hot 研究員（波蘭）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Kowalski Industrial Tools",
        "country": "PL",
        "email": "anna.k@kowalski-tools.pl",
        "full_name": "Anna Kowalski",
        "job_title": "R&D Engineer",
        "behaviors": [
            {"event": "page_view", "url": f"/applications/{APP_ELEC}/", "page_type": "application", "days_ago": 12, "source": "google"},
            {"event": "category_view", "url": f"/products/{CAT_ELEC}/", "page_type": "category", "days_ago": 12},
            {"event": "product_view", "url": product_url(CAT_ELEC, P_VDE6), "page_type": "product", "days_ago": 12},
            {"event": "faq_expand", "url": product_url(CAT_ELEC, P_VDE6), "page_type": "product", "days_ago": 12},
            {"event": "faq_expand", "url": product_url(CAT_ELEC, P_VDE6), "page_type": "product", "days_ago": 12},
            {"event": "application_view", "url": f"/applications/{APP_ELEC}/", "page_type": "application", "days_ago": 11},
            {"event": "spec_download", "url": product_url(CAT_ELEC, P_VDE6), "page_type": "product", "days_ago": 11},
            {"event": "return_visit", "url": product_url(CAT_ELEC, P_VDE6), "page_type": "product", "days_ago": 3, "source": "google"},
            {"event": "cta_click", "url": product_url(CAT_ELEC, P_VDE6), "page_type": "product", "days_ago": 3},
        ],
        "download_gate": {
            "full_name": "Anna Kowalski",
            "email": "anna.k@kowalski-tools.pl",
            "company_name": "Kowalski Industrial Tools",
        },
    },
    {
        "id": "p7",
        "label": "❄️ David Park — Cold 匿名（韓國）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Unknown",
        "country": "KR",
        "email": None,
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 1, "source": "google"},
            {"event": "page_view", "url": "/products/", "page_type": "category_list", "days_ago": 1},
        ],
    },
]


def _headers(token=None, content_type=False):
    headers = {"X-Tenant-ID": TENANT_ID}
    if content_type:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_post(path, payload, token=None):
    data = json.dumps(payload).encode("utf-8")
    headers = _headers(token=token, content_type=True)
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  ⚠  HTTP {e.code} at {path}: {body[:200]}")
        return None


def api_get(path, token):
    headers = _headers(token=token)
    req = urllib.request.Request(f"{API_BASE}{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None


def extract_items(resp):
    if not resp:
        return []
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        data = resp.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]
        if isinstance(resp.get("items"), list):
            return resp["items"]
    return []


def main():
    if not LOGIN_PASSWORD:
        raise RuntimeError("Set FORGEBASE_ADMIN_PASSWORD before seeding demo visitors")

    print("=" * 60)
    print("NorthForge Tools — Demo Visitor Seed")
    print("=" * 60)

    print("\n[1/4] 登入 API...")
    result = api_post("/auth/login", {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD})
    if not result or "access_token" not in result:
        print("❌ 登入失敗。請設定 FORGEBASE_ADMIN_PASSWORD 或確認 admin 密碼。")
        return
    token = result["access_token"]
    print("  ✅ 登入成功")

    print("\n[2/4] 取得現有產品 ID...")
    # Prefer known torque SKUs for RFQ linkage
    products_resp = api_get(
        "/content/products?page_size=50&status=published&locale=en", token
    )
    products = extract_items(products_resp)
    by_model = {p.get("model_number"): p.get("id") for p in products if p.get("id")}
    preferred = [by_model[m] for m in ("NFT-TW500", "NFT-TW380", "NFT-TWA120") if by_model.get(m)]
    product_ids = preferred or [p["id"] for p in products[:3] if p.get("id")]
    if product_ids:
        print(f"  ✅ 取得 {len(product_ids)} 個產品 ID")
    else:
        print("  ⚠  找不到已發布產品，RFQ 將不含 product_ids（請先執行 import_demo_content.py，並確認 X-Tenant-ID）")

    print(f"\n[3/4] 注入 {len(PERSONAS)} 位模擬訪客的行為事件...")
    for i, persona in enumerate(PERSONAS, 1):
        print(f"\n  [{i}/{len(PERSONAS)}] {persona['label']}")
        vid = persona["visitor_id"]
        session_id = str(uuid.uuid4())
        current_session_day = None

        for behavior in persona["behaviors"]:
            if behavior["days_ago"] != current_session_day:
                session_id = str(uuid.uuid4())
                current_session_day = behavior["days_ago"]

            event_payload = {
                "event_name": behavior["event"],
                "visitor_id": vid,
                "session_id": session_id,
                "page_url": f"http://localhost:3000{behavior['url']}",
                "page_type": behavior.get("page_type"),
                "referrer": (
                    "https://www.google.com/search?q=industrial+torque+wrench+oem"
                    if behavior.get("source") == "google"
                    else None
                ),
                "traffic_source": behavior.get("source", "direct"),
                "device_type": "desktop",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "locale": "en",
                "properties": {"demo": True, "persona_id": persona["id"]},
            }
            result = api_post("/tracking/events", event_payload)
            status = "✓" if result is not None else "✗"
            print(f"    {status} {behavior['event']} @ {behavior['url']}")
            time.sleep(0.05)

        dl = persona.get("download_gate")
        if dl:
            asset_resp = api_get("/content/assets?page_size=1", token)
            assets = extract_items(asset_resp)
            asset_id = assets[0]["id"] if assets else None
            if asset_id:
                dl_payload = {**dl, "visitor_id": vid, "asset_id": asset_id}
                api_post("/forms/download-gate", dl_payload)
                print(f"    ✓ Download Gate 留資 ({dl['email']})")
            else:
                print("    ⚠  找不到 Asset，跳過 Download Gate")

    print("\n[4/4] 注入模擬 RFQ...")
    rfq_personas = [p for p in PERSONAS if p.get("rfq")]
    for i, persona in enumerate(rfq_personas, 1):
        rfq = {**persona["rfq"], "visitor_id": persona["visitor_id"]}
        if product_ids:
            rfq["product_ids"] = product_ids[:2]
        r = api_post("/forms/rfq", rfq)
        if r:
            print(f"  ✅ [{i}] RFQ 建立成功 — {rfq['full_name']} ({rfq['company_name']})")
        else:
            print(f"  ✗  [{i}] RFQ 建立失敗 — {rfq['full_name']}")
        time.sleep(0.25)

    print("\n" + "=" * 60)
    print("✅ Seed 完成")
    print("=" * 60)
    print("後台應可見：訪客意圖階段、RFQ、（若有 asset）download-gate 聯絡人")
    print("前台：http://localhost:3000  後台：http://localhost:3002/backend（若 3001 被占用）")


if __name__ == "__main__":
    main()
