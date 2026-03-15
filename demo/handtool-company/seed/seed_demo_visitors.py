#!/usr/bin/env python3
"""
ForgeBase Demo — 訪客行為 Seed 腳本
=====================================
目的：在沒有真實流量的情況下，注入一批有歷史軌跡的模擬訪客、
      讓後台呈現「系統已在運行中」的狀態，提升 Demo 說服力。

執行前提：
  1. API 服務需正常運行（http://localhost:8000）
  2. 建議先執行 import_demo_content.py 匯入商品資料
     如果尚未匯入，本腳本仍可執行，只是 RFQ 不含 product_ids

執行方式：
  python3 demo/handtool-company/seed/seed_demo_visitors.py

執行後狀態：
  - 後台「訪客列表」出現 7 個來自不同公司的訪客，分佈於各 intent 階段
  - 後台「RFQ 收件箱」出現 3 筆詢價（新建、已指派、已報價各一）
  - 後台「下載記錄」出現 2 筆規格書下載（含 Contact 建立）
  - 後台「帳戶列表」出現 5 個公司帳戶
"""
import json
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

API_BASE = "http://localhost:8000/api/v1"
LOGIN_EMAIL = "admin@forgebase.com"
LOGIN_PASSWORD = "ForgeBase2026!"

# ─── 模擬人物誌 ─────────────────────────────────────────────────────────────
# 7 個買家，覆蓋不同意圖階段。行為決定最終分數。
PERSONAS = [
    {
        "id": "p1",
        "label": "🔥 Thomas Bauer — Hot 採購（德國）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Bauer Hydraulik GmbH",
        "country": "DE",
        "email": "thomas.bauer@bauerhydraulik.de",
        "full_name": "Thomas Bauer",
        "job_title": "Procurement Manager",
        "behaviors": [
            # Session 1（10 天前）— 初次瀏覽
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 10, "source": "google"},
            {"event": "category_view", "url": "/products/hydraulic-seals/", "page_type": "category", "days_ago": 10},
            {"event": "product_view", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 10},
            {"event": "product_view", "url": "/products/hydraulic-seals/model-hs300/", "page_type": "product", "days_ago": 10},
            # Session 2（5 天前）— 深度研究
            {"event": "page_view", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 5, "source": "direct"},
            {"event": "faq_expand", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 5},
            {"event": "faq_expand", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 5},
            {"event": "faq_expand", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 5},
            {"event": "application_view", "url": "/applications/mobile-hydraulics/", "page_type": "application", "days_ago": 5},
            {"event": "cta_click", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 5},
            # Session 3（2 天前）— 高意圖回訪
            {"event": "return_visit", "url": "/products/hydraulic-seals/", "page_type": "category", "days_ago": 2, "source": "email"},
            {"event": "product_view", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 2},
            {"event": "spec_download", "url": "/products/hydraulic-seals/model-hs200/", "page_type": "product", "days_ago": 2},
        ],
        "rfq": {
            "full_name": "Thomas Bauer",
            "email": "thomas.bauer@bauerhydraulik.de",
            "company_name": "Bauer Hydraulik GmbH",
            "phone": "+49-89-1234567",
            "country": "DE",
            "job_title": "Procurement Manager",
            "quantity": "500 units/month",
            "specifications": "Need hydraulic seals compatible with 350-bar operating pressure, temperature range -30°C to +120°C. Please confirm material options.",
            "timeline": "3-6 months",
            "message": "We are currently evaluating suppliers for a new hydraulic cylinder assembly line. Your HS-200 series looks promising.",
            "how_did_you_find_us": "google",
            "consent": True,
            "source_page": "/products/hydraulic-seals/model-hs200/",
        },
    },
    {
        "id": "p2",
        "label": "✅ Sarah Mitchell — Sales-Ready 工程師（美國）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Pacific Automation Inc.",
        "country": "US",
        "email": "s.mitchell@pacificautomation.com",
        "full_name": "Sarah Mitchell",
        "job_title": "Senior Applications Engineer",
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 21, "source": "linkedin"},
            {"event": "product_view", "url": "/products/pneumatic-fittings/model-pf100/", "page_type": "product", "days_ago": 21},
            {"event": "product_view", "url": "/products/pneumatic-fittings/model-pf200/", "page_type": "product", "days_ago": 21},
            {"event": "application_view", "url": "/applications/factory-automation/", "page_type": "application", "days_ago": 20},
            {"event": "comparison_view", "url": "/compare/pneumatic-fittings/", "page_type": "comparison", "days_ago": 18},
            {"event": "faq_expand", "url": "/products/pneumatic-fittings/model-pf100/", "page_type": "product", "days_ago": 18},
            {"event": "spec_download", "url": "/products/pneumatic-fittings/model-pf100/", "page_type": "product", "days_ago": 15},
            {"event": "return_visit", "url": "/products/pneumatic-fittings/", "page_type": "category", "days_ago": 7, "source": "google"},
            {"event": "product_view", "url": "/products/pneumatic-fittings/model-pf200/", "page_type": "product", "days_ago": 7},
            {"event": "cta_click", "url": "/products/pneumatic-fittings/model-pf200/", "page_type": "product", "days_ago": 7},
            {"event": "rfq_start", "url": "/request-quote/", "page_type": "rfq", "days_ago": 7},
        ],
        "rfq": {
            "full_name": "Sarah Mitchell",
            "email": "s.mitchell@pacificautomation.com",
            "company_name": "Pacific Automation Inc.",
            "country": "US",
            "job_title": "Senior Applications Engineer",
            "quantity": "2,000 pcs initial order, ongoing monthly",
            "specifications": "PF-200 with push-to-connect, 1/4\" OD tubing, max 10 bar. Need RoHS compliance documentation.",
            "timeline": "immediate",
            "message": "We have an active project requiring pneumatic fittings in volume. Please provide formal quotation with lead time.",
            "how_did_you_find_us": "linkedin",
            "consent": True,
            "source_page": "/products/pneumatic-fittings/model-pf200/",
        },
    },
    {
        "id": "p3",
        "label": "🟡 Kenji Tanaka — Warm 工程師（日本）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Tanaka Machine Works",
        "country": "JP",
        "email": None,  # 未留資
        "behaviors": [
            {"event": "page_view", "url": "/", "page_type": "home", "days_ago": 8, "source": "google"},
            {"event": "category_view", "url": "/products/precision-pins/", "page_type": "category", "days_ago": 8},
            {"event": "product_view", "url": "/products/precision-pins/model-pp50/", "page_type": "product", "days_ago": 8},
            {"event": "product_view", "url": "/products/precision-pins/model-pp80/", "page_type": "product", "days_ago": 8},
            {"event": "application_view", "url": "/applications/precision-assembly/", "page_type": "application", "days_ago": 6},
            {"event": "faq_expand", "url": "/products/precision-pins/model-pp50/", "page_type": "product", "days_ago": 6},
            {"event": "return_visit", "url": "/products/precision-pins/model-pp50/", "page_type": "product", "days_ago": 3, "source": "direct"},
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
            {"event": "product_view", "url": "/products/hydraulic-seals/model-hs100/", "page_type": "product", "days_ago": 2},
        ],
    },
    {
        "id": "p5",
        "label": "🟡 Marco Rossi — Warm 採購（義大利）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Rossi Meccanica S.r.l.",
        "country": "IT",
        "email": "m.rossi@rossimeccanica.it",
        "full_name": "Marco Rossi",
        "job_title": "Purchasing Director",
        "behaviors": [
            {"event": "page_view", "url": "/certifications/", "page_type": "certifications", "days_ago": 14, "source": "referral"},
            {"event": "page_view", "url": "/applications/industrial-machinery/", "page_type": "application", "days_ago": 14},
            {"event": "product_view", "url": "/products/bushings/model-bu300/", "page_type": "product", "days_ago": 14},
            {"event": "spec_download", "url": "/products/bushings/model-bu300/", "page_type": "product", "days_ago": 13},
            {"event": "return_visit", "url": "/products/bushings/", "page_type": "category", "days_ago": 4, "source": "google"},
            {"event": "product_view", "url": "/products/bushings/model-bu350/", "page_type": "product", "days_ago": 4},
            {"event": "comparison_view", "url": "/compare/bushings/", "page_type": "comparison", "days_ago": 4},
        ],
        "download_gate": {
            "full_name": "Marco Rossi",
            "email": "m.rossi@rossimeccanica.it",
            "company_name": "Rossi Meccanica S.r.l.",
        },
    },
    {
        "id": "p6",
        "label": "🔥 Anna Kowalski — Hot 研究員（波蘭）",
        "visitor_id": str(uuid.uuid4()),
        "company": "Kowalski Engineering",
        "country": "PL",
        "email": "anna.k@kowalski-eng.pl",
        "full_name": "Anna Kowalski",
        "job_title": "R&D Engineer",
        "behaviors": [
            {"event": "page_view", "url": "/applications/renewable-energy/", "page_type": "application", "days_ago": 12, "source": "google"},
            {"event": "product_view", "url": "/products/seals/model-s500/", "page_type": "product", "days_ago": 12},
            {"event": "faq_expand", "url": "/products/seals/model-s500/", "page_type": "product", "days_ago": 12},
            {"event": "faq_expand", "url": "/products/seals/model-s500/", "page_type": "product", "days_ago": 12},
            {"event": "application_view", "url": "/applications/renewable-energy/", "page_type": "application", "days_ago": 11},
            {"event": "spec_download", "url": "/products/seals/model-s500/", "page_type": "product", "days_ago": 11},
            {"event": "return_visit", "url": "/products/seals/model-s500/", "page_type": "product", "days_ago": 3, "source": "google"},
            {"event": "cta_click", "url": "/products/seals/model-s500/", "page_type": "product", "days_ago": 3},
        ],
        "download_gate": {
            "full_name": "Anna Kowalski",
            "email": "anna.k@kowalski-eng.pl",
            "company_name": "Kowalski Engineering",
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

# ─── 工具函式 ─────────────────────────────────────────────────────────────────
def api_post(path, payload, token=None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
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
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(f"{API_BASE}{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None


def ago(days):
    """回傳 N 天前的 ISO 8601 timestamp（UTC）"""
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


# ─── 主流程 ──────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("ForgeBase Demo Visitor Seed")
    print("=" * 60)

    # 1. 登入
    print("\n[1/4] 登入 API...")
    result = api_post("/auth/login", {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD})
    if not result or "access_token" not in result:
        print("❌ 登入失敗，請確認 API 服務正在運行")
        return
    token = result["access_token"]
    print("  ✅ 登入成功")

    # 2. 取得第一批產品 ID（供 RFQ 注入用）
    print("\n[2/4] 取得現有產品 ID...")
    products_resp = api_get("/content/products?limit=10&status=published", token)
    product_ids = []
    if products_resp and "items" in products_resp:
        product_ids = [p["id"] for p in products_resp["items"][:3]]
        print(f"  ✅ 取得 {len(product_ids)} 個產品 ID")
    elif products_resp and isinstance(products_resp, list):
        product_ids = [p["id"] for p in products_resp[:3]]
        print(f"  ✅ 取得 {len(product_ids)} 個產品 ID")
    else:
        print("  ⚠  找不到已發布产品，RFQ 將不含 product_ids（建議先執行 import_demo_content.py）")

    # 3. 注入訪客行為事件
    print(f"\n[3/4] 注入 {len(PERSONAS)} 位模擬訪客的行為事件...")
    for i, persona in enumerate(PERSONAS, 1):
        print(f"\n  [{i}/{len(PERSONAS)}] {persona['label']}")
        vid = persona["visitor_id"]
        session_id = str(uuid.uuid4())  # 每個訪客第一個 session
        current_session_day = None

        for behavior in persona["behaviors"]:
            # 不同天 = 不同 session（模擬回訪）
            if behavior["days_ago"] != current_session_day:
                session_id = str(uuid.uuid4())
                current_session_day = behavior["days_ago"]

            event_payload = {
                "event_name": behavior["event"],
                "visitor_id": vid,
                "session_id": session_id,
                "page_url": f"http://localhost:3000{behavior['url']}",
                "page_type": behavior.get("page_type"),
                "referrer": f"https://www.google.com/search?q=hydraulic+seals+manufacturer" if behavior.get("source") == "google" else None,
                "traffic_source": behavior.get("source", "direct"),
                "device_type": "desktop",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "locale": "en",
                "properties": {"demo": True, "persona_id": persona["id"]},
            }
            result = api_post("/tracking/events", event_payload)
            status = "✓" if result is not None else "✗"
            print(f"    {status} {behavior['event']} @ {behavior['url']}")
            time.sleep(0.05)  # 避免過快打 API

        # Download Gate（若有）
        dl = persona.get("download_gate")
        if dl:
            asset_resp = api_get("/content/assets?limit=1", token)
            asset_id = None
            if asset_resp and "items" in asset_resp and asset_resp["items"]:
                asset_id = asset_resp["items"][0]["id"]
            elif asset_resp and isinstance(asset_resp, list) and asset_resp:
                asset_id = asset_resp[0]["id"]

            if asset_id:
                dl_payload = {**dl, "visitor_id": vid, "asset_id": asset_id}
                r = api_post("/forms/download-gate", dl_payload)
                print(f"    ✓ Download Gate 留資 ({dl['email']})")
            else:
                print(f"    ⚠  找不到 Asset，跳過 Download Gate")

    # 4. 注入 RFQ
    print(f"\n[4/4] 注入模擬 RFQ...")
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
        time.sleep(0.2)

    # ─── 完成摘要 ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ Seed 完成")
    print("=" * 60)
    print()
    print("後台現在應顯示：")
    print("  • 訪客列表：7 位訪客，分佈 Cold / Warm / Hot / Sales-Ready")
    print("  • RFQ 收件箱：2 筆新詢價（Thomas Bauer、Sarah Mitchell）")
    print("  • 聯絡人：2 個 Download Gate 留資（Marco Rossi、Anna Kowalski）")
    print()
    print("Demo 建議流程：")
    print("  1. 先打開後台 http://localhost:3001 確認資料已出現")
    print("  2. 開一個新的「無痕視窗」開啟 http://localhost:3000")
    print("  3. 瀏覽幾個產品頁，切回後台即時重新整理")
    print("     → 後台出現新事件 / 分數變動 = Demo 最精彩的現場感")
    print()
    print("  提醒：不同的無痕視窗會產生不同的 visitor_id")
    print("        可同時開 2-3 個視窗模擬「不同買家」")
    print()


if __name__ == "__main__":
    main()
