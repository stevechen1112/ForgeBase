#!/usr/bin/env python3
"""Scan ForgeBase admin UI for jargon / English copy visible to users."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "http://localhost:3002/backend"
LOGIN = f"{BASE}/login"
API_LOGIN = "http://127.0.0.1:8000/api/v1/auth/login"
EMAIL = os.environ.get("FORGEBASE_ADMIN_EMAIL", "admin@forgebase.com")
PASSWORD = os.environ.get("FORGEBASE_ADMIN_PASSWORD", "")


def fetch_token() -> dict:
    if not PASSWORD:
        raise RuntimeError(
            "Set FORGEBASE_ADMIN_PASSWORD (and optionally FORGEBASE_ADMIN_EMAIL) before running the scan."
        )
    payload = json.dumps({"email": EMAIL, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        API_LOGIN,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Daily workspaces plus retained deep routes (with basePath prefix in href).
# This intentionally exceeds the compact sidebar: deep routes remain reachable
# from their workspace hubs and still need user-facing copy QA.
SIDEBAR_ROUTES = [
    "/dashboard",
    "/dashboard/buyers",
    "/dashboard/content",
    "/dashboard/content/locales",
    "/dashboard/growth",
    "/dashboard/replies",
    "/dashboard/support",
    "/dashboard/tasks",
    "/dashboard/outcomes",
    "/dashboard/rfqs/my",
    "/dashboard/rfqs",
    "/dashboard/rfqs/templates",
    "/dashboard/notifications",
    "/dashboard/intent",
    "/dashboard/visitors",
    "/dashboard/ml-scoring",
    "/dashboard/intent-rules",
    "/dashboard/content-performance",
    "/dashboard/chats",
    "/dashboard/copilot",
    "/dashboard/agent-runs",
    "/dashboard/segments",
    "/dashboard/nurture",
    "/dashboard/nurture/outbox",
    "/dashboard/products",
    "/dashboard/categories",
    "/dashboard/pages",
    "/dashboard/assets",
    "/dashboard/applications",
    "/dashboard/faqs",
    "/dashboard/certifications",
    "/dashboard/capabilities",
    "/dashboard/ctas",
    "/dashboard/redirects",
    "/dashboard/settings/notifications",
    "/dashboard/users",
    "/dashboard/settings/site-profile",
    "/dashboard/integrations",
]

STATIC_SUB_ROUTES = [
    "/dashboard/products/new",
    "/dashboard/categories/new",
    "/dashboard/pages/new",
    "/dashboard/applications/new",
    "/dashboard/faqs/new",
    "/dashboard/certifications/new",
    "/dashboard/capabilities/new",
    "/dashboard/ctas/new",
    "/dashboard/comparisons/new",
    "/dashboard/segments/new",
    "/dashboard/nurture/new",
]

# Words/phrases that should not appear in user-facing UI (case-insensitive word boundary where possible)
JARGON_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("save_failed", re.compile(r"Save failed", re.I)),
    ("slug_label", re.compile(r"\bSlug\b")),
    ("seo_title", re.compile(r"SEO Title", re.I)),
    ("seo_description", re.compile(r"SEO Description", re.I)),
    ("og_image", re.compile(r"OG Image", re.I)),
    ("noindex", re.compile(r"\bNoindex\b", re.I)),
    ("json_ld", re.compile(r"JSON-LD", re.I)),
    ("uuid", re.compile(r"\bUUID\b", re.I)),
    ("entity_label", re.compile(r"\bEntity\b")),
    ("awareness", re.compile(r"\bAwareness\b")),
    ("consideration", re.compile(r"\bConsideration\b")),
    ("decision_stage", re.compile(r"\bDecision\b")),
    ("challenge_paren", re.compile(r"Challenge\)", re.I)),
    ("solution_paren", re.compile(r"Solution\)", re.I)),
    ("landing_option", re.compile(r">Landing<|value=\"landing\">Landing")),
    ("custom_option", re.compile(r">Custom<")),
    ("home_option", re.compile(r">Home<")),
    ("策略地圖", re.compile(r"策略地圖")),
    ("新增摘要", re.compile(r"新增摘要")),
    ("所有摘要", re.compile(r"所有摘要")),
    ("實體 ID", re.compile(r"實體 ID")),
    ("實體類型", re.compile(r"實體類型")),
    ("handoff", re.compile(r"handoff", re.I)),
    ("agentos", re.compile(r"AgentOS", re.I)),
    ("canonical_url", re.compile(r"Canonical URL", re.I)),
    ("structured_data_en", re.compile(r"Structured Data", re.I)),
    ("新增 FAQ", re.compile(r"新增 FAQ")),
    ("編輯摘要", re.compile(r"編輯摘要")),
    ("intent_stage", re.compile(r"Intent Stage|intent stage", re.I)),
    ("cta_key_en", re.compile(r"CTA Key", re.I)),
    ("legacy_starter", re.compile(r"\bStarter\b", re.I)),
    ("legacy_professional", re.compile(r"\bProfessional\b", re.I)),
    ("legacy_billing", re.compile(r"\bBilling\b", re.I)),
    ("legacy_phase", re.compile(r"\bPhase\s*[12]\b", re.I)),
]

ALLOWLIST_SUBSTRINGS = [
    "RFQ",
    "English",
    "Deutsch",
    "日本語",
    "한국어",
    "简体中文",
    "繁體中文",
    "NorthForge",
    "ForgeBase",
    "JSON 格式",  # site-profile intentional
    "JSON 陣列",
    "JSON 定義",
]


@dataclass
class PageResult:
    path: str
    status: str
    title: str
    issues: list[str]
    sample: str


def login(_context, page, token_payload: dict) -> None:
    auth_json = json.dumps(token_payload, ensure_ascii=False)
    page.goto(admin_url("/dashboard"), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    if "/login" not in page.url:
        return
    page.goto(LOGIN, wait_until="domcontentloaded", timeout=60000)
    page.evaluate(
        f"""() => sessionStorage.setItem("fb_auth", {json.dumps(auth_json)})"""
    )
    page.goto(admin_url("/dashboard"), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    if "/login" in page.url:
        page.fill("#login-email", EMAIL)
        page.fill("#login-password", PASSWORD)
        page.get_by_role("button", name="登入管理後台").click()
        page.wait_for_url(re.compile(r"/backend/dashboard"), timeout=60000)


def admin_url(path: str) -> str:
    return f"{BASE.rstrip('/')}{path}"


def visible_text(page) -> str:
    return page.locator("body").inner_text(timeout=15000)


def find_issues(text: str) -> list[str]:
    hits: list[str] = []
    for name, pat in JARGON_PATTERNS:
        if pat.search(text):
            hits.append(name)
    return hits


def collect_dynamic_links(page, list_path: str, patterns: list[str]) -> list[str]:
    page.goto(admin_url(list_path), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1200)
    hrefs: set[str] = set()
    for pat in patterns:
        for el in page.locator(f'a[href*="{pat}"]').all():
            href = el.get_attribute("href") or ""
            if href.startswith("/backend"):
                hrefs.add(href.replace("/backend", "", 1))
            elif href.startswith("/dashboard"):
                hrefs.add(href)
    return sorted(hrefs)[:8]


def scan_path(page, path: str) -> PageResult:
    url = admin_url(path)
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(900)
        if "/login" in page.url and path != "/login":
            return PageResult(path, "redirect_login", page.title(), ["auth_lost"], "")
        status = str(resp.status if resp else "?")
        text = visible_text(page)
        issues = find_issues(text)
        sample = text[:400].replace("\n", " | ")
        return PageResult(path, status, page.title(), issues, sample)
    except PWTimeout:
        return PageResult(path, "timeout", "", ["timeout"], "")
    except Exception as e:  # noqa: BLE001
        return PageResult(path, "error", "", [f"error:{e}"], "")


def main() -> int:
    out_path = Path(__file__).resolve().parent / "admin_ui_scan_report.json"
    routes = list(dict.fromkeys(SIDEBAR_ROUTES + STATIC_SUB_ROUTES))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        token_payload = fetch_token()
        auth_json = json.dumps(token_payload, ensure_ascii=False)
        context = browser.new_context(locale="zh-TW")
        context.add_init_script(
            f"""() => {{
              sessionStorage.setItem("fb_auth", {json.dumps(auth_json)});
            }}"""
        )
        page = context.new_page()
        login(context, page, token_payload)

        dynamic: list[str] = []
        dynamic += collect_dynamic_links(page, "/dashboard/products", ["/edit", "/preview"])
        dynamic += collect_dynamic_links(page, "/dashboard/categories", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/pages", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/applications", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/faqs", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/certifications", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/capabilities", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/ctas", ["/edit"])
        dynamic += collect_dynamic_links(page, "/dashboard/rfqs", ["/dashboard/rfqs/"])
        dynamic += collect_dynamic_links(page, "/dashboard/chats", ["/dashboard/chats/"])
        dynamic += collect_dynamic_links(page, "/dashboard/segments", ["/dashboard/segments/"])
        dynamic += collect_dynamic_links(page, "/dashboard/nurture", ["/dashboard/nurture/"])
        dynamic += collect_dynamic_links(page, "/dashboard/intent", ["/dashboard/visitors/"])

        routes = list(dict.fromkeys(routes + dynamic))

        results: list[PageResult] = []
        for path in routes:
            results.append(scan_path(page, path))
            sys.stdout.write(".")
            sys.stdout.flush()

        browser.close()

    bad = [r for r in results if r.issues or r.status not in ("200", "?", "redirect_login")]
    report = {
        "total": len(results),
        "with_issues": len(bad),
        "sidebar_count": len(SIDEBAR_ROUTES),
        "results": [asdict(r) for r in results],
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n==== SCAN SUMMARY ====")
    print(f"pages scanned: {len(results)} (sidebar={len(SIDEBAR_ROUTES)})")
    print(f"pages with issues: {len(bad)}")
    for r in bad:
        print(f"  {r.path} [{r.status}] -> {', '.join(r.issues)}")
    print(f"report: {out_path}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
