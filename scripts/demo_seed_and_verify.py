#!/usr/bin/env python3
"""
ForgeBase Demo Seed & System Verify Script
==========================================
用途：
  1. verify  模式 — 只做 API 健康檢查（不寫資料），適合每次部署後快速確認
  2. demo    模式 — 注入 30 天模擬訪客流量 + 驗證，適合 Demo 前備料

執行方式：
  python scripts/demo_seed_and_verify.py --mode verify
  python scripts/demo_seed_and_verify.py --mode demo
  python scripts/demo_seed_and_verify.py --mode demo --base-url https://172.233.64.5 --email admin@example.com --password yourpassword

預設 base-url = https://172.233.64.5
"""

import argparse
import json
import math
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

# ── ANSI 顏色 ─────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}")
def info(msg): print(f"  {CYAN}→{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}\n{BOLD}{msg}{RESET}")

# ── Demo 規模參數（調整這裡改 Demo 資料量） ─────────────────────────────────
DEMO_DAYS         = 30      # 模擬過去幾天
VISITORS_TOTAL    = 120     # 總共幾個不同訪客
SESSIONS_TOTAL    = 210     # 總 session 數（訪客平均 1.75 次回訪）
EVENTS_PER_SESSION = (3, 9) # 每個 session 的 event 數範圍
CONTACT_FORMS     = 4       # 模擬幾筆聯絡表單
RFQ_SUBMISSIONS   = 6       # 模擬幾筆 RFQ 詢價單

# ── 模擬訪客輪廓 ──────────────────────────────────────────────────────────────
# (weight, device, country, traffic_source, activity_profile)
VISITOR_PROFILES = [
    (30, "desktop", "TW", "organic",  "cold"),
    (20, "desktop", "US", "organic",  "warm"),
    (15, "mobile",  "TW", "direct",   "cold"),
    (10, "desktop", "JP", "referral", "warm"),
    ( 8, "desktop", "DE", "organic",  "hot"),
    ( 7, "desktop", "US", "paid",     "hot"),
    ( 5, "mobile",  "CN", "organic",  "cold"),
    ( 5, "tablet",  "TW", "referral", "warm"),
]

# ── 模擬用假名 ────────────────────────────────────────────────────────────────
FAKE_NAMES = [
    ("Ethan Chen", "ethan.chen"),         ("Sophia Lin", "sophia.lin"),
    ("James Wu", "james.wu"),             ("Olivia Chang", "olivia.chang"),
    ("Michael Wang", "michael.wang"),     ("Emma Huang", "emma.huang"),
    ("Daniel Lee", "daniel.lee"),         ("Ava Liu", "ava.liu"),
    ("William Zhang", "william.zhang"),   ("Isabella Chou", "isabella.chou"),
]
FAKE_COMPANIES = [
    "Apex Electronics",  "ShineTech Co.",  "Vertex Components",
    "NovaPower GmbH",    "SBR Industries", "PrimeTech Ltd.",
    "BlueStar Holdings", "OmniCircuit Inc.", "Horizon Mfg",
    "CoreTech Systems",
]
HOW_FOUND = ["google", "linkedin", "trade_show", "referral", "direct", "email", "other"]
COUNTRIES  = ["TW", "US", "JP", "DE", "CN", "SG", "KR", "IN", "GB", "AU"]

# ── 流量來源分布（工作日流量較多） ────────────────────────────────────────────
TRAFFIC_WEIGHTS = {
    "organic": 45, "direct": 20, "referral": 15,
    "paid": 12, "social": 8,
}


# ═════════════════════════════════════════════════════════════════════════════
# HTTP 工具
# ═════════════════════════════════════════════════════════════════════════════

class APIClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.errors: list[str] = []
        self.passed: int = 0
        self.failed: int = 0

    def _auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def login(self, email: str, password: str) -> bool:
        url = f"{self.base}/api/v1/auth/login"
        try:
            r = self.session.post(url, json={"email": email, "password": password}, timeout=10)
            if r.status_code == 200:
                self.token = r.json()["access_token"]
                ok(f"登入成功  ({email})")
                return True
            else:
                fail(f"登入失敗 HTTP {r.status_code}: {r.text[:120]}")
                return False
        except Exception as e:
            fail(f"登入請求失敗: {e}")
            return False

    def check(self, method: str, path: str, *, label: str,
              json_body=None, params=None, auth=True,
              expect_status=200, expect_keys: list[str] | None = None) -> Optional[dict]:
        """執行請求並記錄通過/失敗。回傳 response JSON 或 None。"""
        url = f"{self.base}{path}"
        headers = self._auth_headers() if auth else {}
        try:
            r = self.session.request(
                method, url, headers=headers,
                json=json_body, params=params, timeout=15,
            )
            if r.status_code != expect_status:
                fail(f"{label}  →  HTTP {r.status_code}  (期望 {expect_status})")
                self.errors.append(f"{label}: HTTP {r.status_code}")
                self.failed += 1
                return None

            data = r.json() if r.content else {}

            # 驗證 response 有指定的 key
            if expect_keys:
                missing = [k for k in expect_keys if k not in data]
                if missing:
                    fail(f"{label}  →  回應缺少欄位 {missing}")
                    self.errors.append(f"{label}: missing keys {missing}")
                    self.failed += 1
                    return None

            ok(label)
            self.passed += 1
            return data

        except Exception as e:
            fail(f"{label}  →  {e}")
            self.errors.append(f"{label}: {e}")
            self.failed += 1
            return None

    def post_event(self, event: dict) -> Optional[dict]:
        """POST 單筆 tracking event（無需 auth）"""
        return self.check("POST", "/api/v1/tracking/events",
                          label=f"event:{event['event_name']}",
                          json_body=event, auth=False,
                          expect_status=202,
                          expect_keys=["event_id"])

    def post_events_batch(self, events: list[dict]) -> bool:
        """POST batch events（無需 auth）- body 為直接 array"""
        result = self.check("POST", "/api/v1/tracking/events/batch",
                            label=f"batch({len(events)} events)",
                            json_body=events, auth=False,
                            expect_status=202)
        return result is not None


# ═════════════════════════════════════════════════════════════════════════════
# 資料生成工具
# ═════════════════════════════════════════════════════════════════════════════

def weighted_choice(items_weights: dict) -> str:
    keys = list(items_weights.keys())
    weights = list(items_weights.values())
    return random.choices(keys, weights=weights, k=1)[0]

def random_past_timestamp(days_ago_max: int = DEMO_DAYS) -> datetime:
    """生成過去 N 天內的隨機時間戳，工作日 + 日間時段機率較高"""
    now = datetime.now(timezone.utc)
    # 隨機選一天（越近的日子權重略高）
    day_offset = random.choices(
        range(days_ago_max),
        weights=[math.exp(-i * 0.05) for i in range(days_ago_max)],
        k=1
    )[0]
    target_date = now - timedelta(days=day_offset)

    # 工作日加權（週一～週五流量多）
    weekday = target_date.weekday()
    if weekday >= 5:  # 週末
        hour = random.choices(range(8, 22), weights=[1,1,2,2,3,3,3,3,2,2,2,2,1,1], k=1)[0]
    else:  # 平日
        hour = random.choices(range(8, 22), weights=[2,3,4,5,5,4,3,2,2,3,4,5,4,3], k=1)[0]

    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return target_date.replace(hour=hour, minute=minute, second=second, microsecond=0)

def build_visitor_events(visitor_id: str, session_id: str,
                          product_ids: list[str], app_ids: list[str],
                          profile: tuple, event_count: int,
                          base_time: datetime,
                          base_url: str) -> list[dict]:
    """
    根據訪客輪廓生成一個 session 內的事件序列。
    模擬真實的瀏覽行為：先看首頁 → 瀏覽產品 → 可能下載/詢價。
    """
    _, device, country, traffic, activity_profile = profile
    events = []
    t = base_time

    page_types = []

    for i in range(event_count):
        t = t + timedelta(seconds=random.randint(30, 180))

        if i == 0:
            # 第一個事件必定是 page_view
            event_name = "page_view"
            page_type = "page"
            page_id = None
        elif i == 1 and product_ids:
            event_name = "product_view"
            page_type = "product"
            page_id = random.choice(product_ids)
            page_types.append(page_type)
        elif i == 1 and not product_ids:
            event_name = "page_view"
            page_type = "page"
            page_id = None
        else:
            # 根據測試活動輪廓決定後續行為機率
            if activity_profile == "hot":
                choices = ["product_view","product_view","spec_download","rfq_start","cta_click","comparison_view"]
            elif activity_profile == "warm":
                choices = ["product_view","category_view","application_view","cta_click","faq_expand","comparison_view"]
            else:
                choices = ["page_view","category_view","product_view","faq_expand","application_view"]

            event_name = random.choice(choices)
            if event_name == "product_view":
                page_type = "product"
                page_id = random.choice(product_ids) if product_ids else None
            elif event_name == "category_view":
                page_type = "category"
                page_id = None
            elif event_name == "application_view":
                page_type = "application"
                page_id = random.choice(app_ids) if app_ids else None
            elif event_name == "comparison_view":
                page_type = "comparison"
                page_id = None
            else:
                page_type = "page"
                page_id = None

        ev = {
            "event_name": event_name,
            "visitor_id": visitor_id,
            "session_id": session_id,
            "page_url": f"{base_url}/{page_type or 'page'}/{uuid.uuid4().hex[:8]}",
            "page_type": page_type if event_name != "page_view" else "page",
            "locale": "en",
            "traffic_source": traffic,
            "device_type": device,
        }
        if page_id:
            ev["page_id"] = page_id

        events.append(ev)

    # 深度訪問達到 5 頁則追加 session_depth_reached
    if event_count >= 5:
        t = t + timedelta(seconds=10)
        events.append({
            "event_name": "session_depth_reached",
            "visitor_id": visitor_id,
            "session_id": session_id,
            "page_url": f"{base_url}/",
            "locale": "en",
            "traffic_source": traffic,
            "device_type": device,
        })

    return events


# ═════════════════════════════════════════════════════════════════════════════
# Phase 1：健康檢查 (verify)
# ═════════════════════════════════════════════════════════════════════════════

def run_verify(client: APIClient):
    header("Phase 1 / API 健康檢查（需要管理員 Token）")

    # ── Tracking 讀取 API ────────────────────────────────────────────────────
    checks = [
        ("GET",  "/api/v1/tracking/visitors?limit=5",         "訪客列表"),
        ("GET",  "/api/v1/tracking/contacts?page_size=5",      "聯絡人列表"),
        ("GET",  "/api/v1/tracking/rfqs",                      "RFQ 列表"),
        ("GET",  "/api/v1/tracking/analytics/pages?days=30",   "頁面分析 (30天)"),
        ("GET",  "/api/v1/tracking/analytics/products",        "產品分析"),
        ("GET",  "/api/v1/tracking/analytics/applications",    "應用分析"),
        ("GET",  "/api/v1/tracking/events/summary",            "事件摘要"),
    ]

    for method, path, label in checks:
        result = client.check(method, path, label=label)
        if result is not None:
            # 顯示關鍵數字
            if isinstance(result, dict):
                keys_to_show = ["total", "count", "page_views", "summary"]
                shown = {k: result[k] for k in keys_to_show if k in result}
                if shown:
                    info(f"  回應摘要: {shown}")
            elif isinstance(result, list):
                info(f"  返回 {len(result)} 筆記錄")

    # ── 公開 API（不需 auth） ─────────────────────────────────────────────────
    header("公開端點檢查（無需 Token）")
    public_checks = [
        ("GET",  "/api/v1/content/products?page_size=3",       "產品列表（公開）"),
        ("GET",  "/health",                                     "健康檢查"),
    ]
    for method, path, label in public_checks:
        client.check(method, path, label=label, auth=False)

    # ── Event 寫入測試（公開） ────────────────────────────────────────────────
    header("追蹤事件寫入測試")

    test_vid = str(uuid.uuid4())
    test_sid = str(uuid.uuid4())

    test_event = {
        "event_name": "page_view",
        "visitor_id": test_vid,
        "session_id": test_sid,
        "page_url":   f"{client.base}/products",
        "page_type":  "page",
        "locale":     "en",
        "traffic_source": "direct",
        "device_type": "desktop",
    }
    result = client.check("POST", "/api/v1/tracking/events",
                          label="追蹤事件寫入（POST /tracking/events）",
                          json_body=test_event, auth=False,
                          expect_status=202)
    if result:
        info(f"  event_id = {result.get('event_id')}")

    # 驗證剛才寫入的訪客能查到
    r = client.check("GET", f"/api/v1/tracking/visitors",
                     label="驗證 page_view 後訪客已建立",
                     params={"limit": 200})
    if r:
        vids = [v["visitor_id"] for v in (r if isinstance(r, list) else [])]
        if test_vid in vids:
            ok(f"  確認：訪客 {test_vid[:8]}… 已存在於資料庫")
        else:
            warn(f"  注意：測試訪客尚未出現在列表中（可能需要稍等）")


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2：Demo 資料注入
# ═════════════════════════════════════════════════════════════════════════════

def run_demo(client: APIClient):
    header("Phase 2 / 抓取實際產品＆應用 ID")

    # 取真實產品 ID（用在 tracking events 的 page_id）
    product_ids: list[str] = []
    r = client.check("GET", "/api/v1/content/products?page_size=50&status=published",
                     label="取已發布產品列表", auth=False)
    if r and isinstance(r.get("data"), list):
        product_ids = [p["id"] for p in r["data"] if "id" in p]
        ok(f"取得 {len(product_ids)} 個產品 ID")
    else:
        warn("無法取得產品 ID，事件將不帶 page_id")

    # 取真實應用 ID
    app_ids: list[str] = []
    r2 = client.check("GET", "/api/v1/content/applications?page_size=20",
                      label="取應用列表", auth=True)
    # 嘗試不同的應用 endpoint
    if not r2:
        r2 = client.check("GET", "/api/v1/content/applications?page_size=20",
                          label="取應用列表（備用路由）", auth=False)
    if r2 and isinstance(r2.get("data"), list):
        app_ids = [a["id"] for a in r2["data"] if "id" in a]
        ok(f"取得 {len(app_ids)} 個應用 ID")

    # ── 生成訪客 ──────────────────────────────────────────────────────────────
    header("Phase 3 / 生成模擬訪客與 Session 事件")

    # 生成訪客 ID 池
    profile_weights = [p[0] for p in VISITOR_PROFILES]
    visitor_pool: list[tuple[str, tuple]] = []
    for _ in range(VISITORS_TOTAL):
        profile = random.choices(VISITOR_PROFILES, weights=profile_weights, k=1)[0]
        visitor_pool.append((str(uuid.uuid4()), profile))

    info(f"準備模擬 {VISITORS_TOTAL} 個訪客，{SESSIONS_TOTAL} 個 session")
    print()

    # Run-unique suffix for emails — prevents collisions across multiple demo runs
    run_tag = str(int(time.time()))[-6:]

    # Track which visitors actually got events sent (for FK safety in forms)
    active_visitor_ids: set[str] = set()

    total_events_sent = 0
    batch_buffer: list[dict] = []
    BATCH_SIZE = 20

    def flush_batch():
        nonlocal total_events_sent
        if batch_buffer:
            client.post_events_batch(list(batch_buffer))
            total_events_sent += len(batch_buffer)
            batch_buffer.clear()

    # 分配 session 給訪客
    for session_idx in range(SESSIONS_TOTAL):
        # 選一個訪客（熱訪客有更高機率重複造訪）
        hot_visitors   = [(vid, p) for vid, p in visitor_pool if p[4] == "hot"]
        warm_visitors  = [(vid, p) for vid, p in visitor_pool if p[4] == "warm"]
        cold_visitors  = [(vid, p) for vid, p in visitor_pool if p[4] == "cold"]

        bucket_weights = [
            (hot_visitors,  40),
            (warm_visitors, 35),
            (cold_visitors, 25),
        ]
        chosen_bucket = random.choices(
            [bv for bv, _ in bucket_weights],
            weights=[w for _, w in bucket_weights],
            k=1
        )[0]
        if not chosen_bucket:
            chosen_bucket = visitor_pool

        visitor_id, profile = random.choice(chosen_bucket)
        active_visitor_ids.add(visitor_id)
        session_id = str(uuid.uuid4())
        base_time  = random_past_timestamp()

        event_count = random.randint(*EVENTS_PER_SESSION)
        events = build_visitor_events(
            visitor_id, session_id,
            product_ids, app_ids,
            profile, event_count, base_time, client.base
        )

        batch_buffer.extend(events)

        # 每累積 BATCH_SIZE 筆就送出
        while len(batch_buffer) >= BATCH_SIZE:
            to_send = batch_buffer[:BATCH_SIZE]
            client.post_events_batch(to_send)
            total_events_sent += len(to_send)
            del batch_buffer[:BATCH_SIZE]

        # 進度顯示
        if (session_idx + 1) % 30 == 0 or session_idx == SESSIONS_TOTAL - 1:
            pct = int((session_idx + 1) / SESSIONS_TOTAL * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct}%  session {session_idx+1}/{SESSIONS_TOTAL}  events ~{total_events_sent}", end="", flush=True)

    flush_batch()
    print()
    ok(f"共送出約 {total_events_sent} 筆 tracking events")

    # Limit visible visitor pool to those who actually got events sent
    active_visitors = [(vid, p) for vid, p in visitor_pool if vid in active_visitor_ids]
    if not active_visitors:
        active_visitors = visitor_pool  # fallback

    # ── 聯絡表單 ──────────────────────────────────────────────────────────────
    header("Phase 4 / 模擬聯絡表單提交")

    for i in range(CONTACT_FORMS):
        name, email_prefix = random.choice(FAKE_NAMES)
        email = f"{email_prefix}+c{run_tag}{i}@{random.choice(['example.com','testco.io','demo.org'])}"
        company = random.choice(FAKE_COMPANIES)
        country = random.choice(COUNTRIES)

        payload = {
            "full_name":     name,
            "email":         email,
            "company_name":  company,
            "country":       country,
            "job_title":     random.choice(["Purchasing Manager", "CTO", "Engineer", "Director"]),
            "message":       f"We are interested in your products for {random.choice(['automotive','electronics','industrial'])} applications. Please contact us.",
            "how_did_you_find_us": random.choice(HOW_FOUND),
            "visitor_id":    str(random.choice(active_visitors)[0]),
            "source_page":   f"{client.base}/contact",
        }
        r = client.check("POST", "/api/v1/forms/contact",
                         label=f"聯絡表單 #{i+1}  ({name})",
                         json_body=payload, auth=False,
                         expect_status=201)
        if r:
            info(f"  contact_id = {r.get('contact_id', r.get('id', '—'))}")

    # ── RFQ 表單 ──────────────────────────────────────────────────────────────
    header("Phase 5 / 模擬 RFQ 詢價單提交")

    for i in range(RFQ_SUBMISSIONS):
        name, email_prefix = random.choice(FAKE_NAMES)
        email = f"{email_prefix}+r{run_tag}{i}@{random.choice(['example.com','testco.io','demo.org'])}"
        company = random.choice(FAKE_COMPANIES)
        country = random.choice(COUNTRIES)

        selected_products = random.sample(product_ids, min(random.randint(1, 3), len(product_ids))) \
                            if product_ids else []

        quantities = ["100 pcs", "500 pcs", "1000 pcs", "5000+ pcs", "TBD"]
        timelines  = ["immediate", "1-3 months", "3-6 months", "evaluating"]

        payload = {
            "full_name":    name,
            "email":        email,
            "company_name": company,
            "phone":        f"+886-9{random.randint(10000000, 99999999)}",
            "country":      country,
            "job_title":    random.choice(["Procurement", "R&D Engineer", "Product Manager"]),
            "product_ids":  selected_products,
            "quantity":     random.choice(quantities),
            "specifications": f"Need {random.choice(['RoHS compliant','high temperature rated','automotive grade'])} version.",
            "timeline":     random.choice(timelines),
            "message":      f"Please send us a quotation for the above products. We have an urgent project in {random.choice(['Q2','Q3','Q4'])} 2026.",
            "how_did_you_find_us": random.choice(HOW_FOUND),
            "consent":      True,
            "visitor_id":   str(random.choice(active_visitors)[0]),
            "source_page":  f"{client.base}/request-quote",
        }
        r = client.check("POST", "/api/v1/forms/rfq",
                         label=f"RFQ #{i+1}  ({name} / {company})",
                         json_body=payload, auth=False,
                         expect_status=201)
        if r:
            info(f"  rfq_number = {r.get('rfq_number', '—')}")

    # ── 最終驗證 ──────────────────────────────────────────────────────────────
    header("Phase 6 / 注入後驗證：確認儀表板資料已更新")

    verify_checks = [
        ("/api/v1/tracking/visitors?limit=5",        "訪客列表（應有資料）"),
        ("/api/v1/tracking/contacts?page_size=5",     "聯絡人列表（應有資料）"),
        ("/api/v1/tracking/rfqs",                     "RFQ 列表（應有資料）"),
        ("/api/v1/tracking/analytics/pages?days=30",  "頁面分析（應有 page_views）"),
        ("/api/v1/tracking/analytics/products",       "產品分析"),
    ]

    for path, label in verify_checks:
        r = client.check("GET", path, label=label)
        if r is not None:
            # 顯示實際數字
            if isinstance(r, list):
                info(f"  → {len(r)} 筆記錄")
            elif isinstance(r, dict):
                if "total" in r:
                    info(f"  → total = {r['total']}")
                if "pages" in r and isinstance(r["pages"], list):
                    info(f"  → {len(r['pages'])} 個頁面有記錄")
                if "summary" in r:
                    info(f"  → summary = {r['summary']}")


# ═════════════════════════════════════════════════════════════════════════════
# 最終報告
# ═════════════════════════════════════════════════════════════════════════════

def print_report(client: APIClient, mode: str):
    header("測試報告")
    total = client.passed + client.failed
    print(f"  模式：{BOLD}{mode}{RESET}")
    print(f"  通過：{GREEN}{client.passed}{RESET} / {total}")
    if client.failed:
        print(f"  失敗：{RED}{client.failed}{RESET} / {total}")
        print()
        print(f"  {RED}失敗項目：{RESET}")
        for e in client.errors:
            print(f"    • {e}")
    else:
        print(f"\n  {GREEN}{BOLD}全部通過！系統運作正常。{RESET}")

    if mode == "demo":
        print(f"""
  {CYAN}Demo 資料規模：{RESET}
    • 過去 {DEMO_DAYS} 天流量
    • {VISITORS_TOTAL} 個模擬訪客
    • {SESSIONS_TOTAL} 個 session
    • 每 session {EVENTS_PER_SESSION[0]}–{EVENTS_PER_SESSION[1]} 個事件
    • {CONTACT_FORMS} 筆聯絡表單
    • {RFQ_SUBMISSIONS} 筆 RFQ 詢價單

  {YELLOW}可到後台儀表板查看：{RESET}
    {client.base}/backend/dashboard/workspaces/website-product
    {client.base}/backend/dashboard/workspaces/visitor-sources
    {client.base}/backend/dashboard/workspaces/buyer-details
    {client.base}/backend/dashboard/workspaces/inquiries
""")


# ═════════════════════════════════════════════════════════════════════════════
# 入口
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ForgeBase Demo Seed & System Verify")
    parser.add_argument("--mode",     default="verify",
                        choices=["verify", "demo"],
                        help="verify = 只驗證API | demo = 注入資料+驗證")
    parser.add_argument("--base-url", default="https://172.233.64.5",
                        help="API 根網址（預設 https://172.233.64.5）")
    parser.add_argument("--email",    default="admin@forgebase.com",
                        help="管理員帳號")
    parser.add_argument("--password", default=None,
                        help="管理員密碼（若不提供則從終端機輸入）")
    args = parser.parse_args()

    print(f"""
{BOLD}{CYAN}ForgeBase  Demo Seed & System Verify{RESET}
  模式：{BOLD}{args.mode}{RESET}
  目標：{args.base_url}
""")

    # 取得密碼
    password = args.password
    if not password:
        import getpass
        password = getpass.getpass(f"  管理員密碼（{args.email}）：")

    client = APIClient(args.base_url)

    # 登入
    header("登入驗證")
    if not client.login(args.email, password):
        print(f"\n{RED}無法登入，中止執行。請確認帳號密碼。{RESET}")
        sys.exit(1)

    # 執行對應模式
    run_verify(client)

    if args.mode == "demo":
        run_demo(client)

    print_report(client, args.mode)
    sys.exit(0 if client.failed == 0 else 1)


if __name__ == "__main__":
    main()
