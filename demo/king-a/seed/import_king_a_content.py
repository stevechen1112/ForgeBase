#!/usr/bin/env python3
"""
King-A (欣榮貿易) — ForgeBase Seed Import Script
=================================================
由 Legacy Site Intake 自動生成的導入腳本。
將 king-a.com.tw 的結構化內容匯入 ForgeBase API。

執行方式：
  cd api && source .venv/bin/activate   # (Linux/Mac)
  cd api && .venv\Scripts\activate      # (Windows)
  python3 ../demo/king-a/seed/import_king_a_content.py

前提：
  1. API 服務需正常運行（http://localhost:8000）
  2. 已建立 admin 帳號（預設 admin@forgebase.com）
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# King-A 獨立實例 ports（與 demo 錯開）
# 若 API_BASE 環境變數存在，優先使用（方便 CI/CD）
import os
API_BASE = os.environ.get("API_BASE", "http://localhost:8001/api/v1")
LOGIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@king-a.com.tw")
LOGIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ForgeBase2026!")
LOCALE = "zh-TW"

PUBLISHABLE_ENDPOINTS = {
    "categories",
    "products",
    "applications",
    "faqs",
    "pages",
}


def load_json(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def api_request(method: str, path: str, payload=None, token: str | None = None, expected: tuple[int, ...] = (200,)):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else None
            if response.status not in expected:
                raise RuntimeError(f"Unexpected status {response.status} for {method} {path}: {parsed}")
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {"error": body}
        if exc.code not in expected:
            raise RuntimeError(f"HTTP {exc.code} for {method} {path}: {parsed}") from exc
        return exc.code, parsed


class KingAImporter:
    def __init__(self):
        self.token = ""
        self.ids = {
            "categories": {},
            "products": {},
            "applications": {},
            "faqs": {},
            "pages": {},
        }
        self.summary = {
            "created": 0,
            "updated": 0,
            "published": 0,
            "linked": 0,
            "skipped": 0,
        }

    def login(self):
        _, body = api_request(
            "POST",
            "/auth/login",
            {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
            expected=(200,),
        )
        self.token = body["access_token"]
        print(f"✓ 登入成功")

    def list_items(self, endpoint: str, params: dict[str, str] | None = None):
        query = params or {}
        if "page_size" not in query:
            query["page_size"] = "100"
        if "locale" not in query and endpoint not in {"pages"}:
            query["locale"] = LOCALE
        path = f"/content/{endpoint}"
        if query:
            path += "?" + urllib.parse.urlencode(query)
        _, body = api_request("GET", path, token=self.token, expected=(200,))
        return body["data"]

    def get_by_slug(self, endpoint: str, slug: str):
        items = self.list_items(endpoint, {"slug": slug, "locale": LOCALE, "page_size": "1"})
        return items[0] if items else None

    def get_page_by_slug(self, slug: str):
        items = self.list_items("pages", {"slug": slug, "locale": LOCALE, "page_size": "1"})
        return items[0] if items else None

    def get_by_question(self, question: str):
        items = self.list_items("faqs", {"locale": LOCALE, "page_size": "100"})
        for item in items:
            if item["question"] == question:
                return item
        return None

    def get_product_by_model(self, model_number: str):
        items = self.list_items("products", {"locale": LOCALE, "page_size": "100"})
        for item in items:
            if item["model_number"] == model_number:
                return item
        return None

    def create_or_update(self, endpoint: str, payload: dict, key_field: str, key_value: str, existing: dict | None):
        post_payload = dict(payload)
        if endpoint in PUBLISHABLE_ENDPOINTS and post_payload.get("status") == "published":
            post_payload["status"] = "draft"

        if existing:
            _, body = api_request(
                "PATCH",
                f"/content/{endpoint}/{existing['id']}",
                post_payload,
                token=self.token,
                expected=(200,),
            )
            self.summary["updated"] += 1
            item = body["data"]
        else:
            _, body = api_request(
                "POST",
                f"/content/{endpoint}",
                post_payload,
                token=self.token,
                expected=(201,),
            )
            self.summary["created"] += 1
            item = body["data"]

        if endpoint in PUBLISHABLE_ENDPOINTS:
            _, _ = api_request(
                "POST",
                f"/content/{endpoint}/{item['id']}/publish",
                {},
                token=self.token,
                expected=(200,),
            )
            self.summary["published"] += 1
        return item

    # ── Import methods ──────────────────────────────────────────

    def import_pages(self):
        print("\n── 匯入頁面 ──")
        for page in load_json("pages.json"):
            existing = self.get_page_by_slug(page["slug"])
            item = self.create_or_update("pages", page, "slug", page["slug"], existing)
            self.ids["pages"][page["slug"]] = item["id"]
            print(f"  page: {page['slug']}")

    def import_categories(self):
        print("\n── 匯入產品分類 ──")
        for category in load_json("categories.json"):
            existing = self.get_by_slug("categories", category["slug"])
            item = self.create_or_update("categories", category, "slug", category["slug"], existing)
            self.ids["categories"][category["slug"]] = item["id"]
            print(f"  category: {category['slug']}")

    def import_products(self):
        print("\n── 匯入產品 ──")
        for product in load_json("products.json"):
            payload = dict(product)
            category_slug = payload.pop("category_slug")
            payload.pop("source_url", None)  # source_url is metadata, not an API field
            payload["category_id"] = self.ids["categories"][category_slug]
            existing = self.get_product_by_model(product["model_number"])
            item = self.create_or_update("products", payload, "model_number", product["model_number"], existing)
            self.ids["products"][product["model_number"]] = item["id"]
            print(f"  product: {product['model_number']} — {product['product_name']}")

    def import_applications(self):
        print("\n── 匯入應用場景 ──")
        for app in load_json("applications.json"):
            existing = self.get_by_slug("applications", app["slug"])
            item = self.create_or_update("applications", app, "slug", app["slug"], existing)
            self.ids["applications"][app["slug"]] = item["id"]
            print(f"  application: {app['slug']}")

    def import_faqs(self):
        print("\n── 匯入 FAQ ──")
        for faq in load_json("faq-items.json"):
            existing = self.get_by_question(faq["question"])
            item = self.create_or_update("faqs", faq, "question", faq["question"], existing)
            self.ids["faqs"][faq["question"]] = item["id"]
            print(f"  faq: {faq['question'][:40]}...")

    def link(self, path: str):
        try:
            _, _ = api_request("POST", path, {}, token=self.token, expected=(200, 201))
            self.summary["linked"] += 1
        except Exception as e:
            print(f"  ⚠ link failed: {path} — {e}")
            self.summary["skipped"] += 1

    def import_relationships(self):
        print("\n── 匯入關聯 ──")
        relationships = load_json("relationships.json")

        for row in relationships.get("product_application_links", []):
            model = row["product_model_number"]
            app_slug = row["application_slug"]
            if model in self.ids["products"] and app_slug in self.ids["applications"]:
                self.link(
                    f"/content/products/{self.ids['products'][model]}/applications/{self.ids['applications'][app_slug]}"
                )
                print(f"  link: {model} → {app_slug}")
            else:
                self.summary["skipped"] += 1

        for row in relationships.get("product_faq_links", []):
            model = row["product_model_number"]
            question = row["faq_question"]
            if model in self.ids["products"] and question in self.ids["faqs"]:
                self.link(
                    f"/content/products/{self.ids['products'][model]}/faqs/{self.ids['faqs'][question]}"
                )
                print(f"  link: {model} → FAQ")
            else:
                self.summary["skipped"] += 1

        for row in relationships.get("application_faq_links", []):
            app_slug = row["application_slug"]
            question = row["faq_question"]
            if app_slug in self.ids["applications"] and question in self.ids["faqs"]:
                self.link(
                    f"/content/applications/{self.ids['applications'][app_slug]}/faqs/{self.ids['faqs'][question]}"
                )
                print(f"  link: {app_slug} → FAQ")
            else:
                self.summary["skipped"] += 1

    def validate_counts(self):
        print("\n── 驗證 ──")
        checks = {
            "categories": 6,
            "products": 30,
            "applications": 4,
            "faqs": 10,
            "pages": 4,
        }
        results = {}
        all_ok = True
        for endpoint, expected_count in checks.items():
            params = {"page_size": "100", "locale": LOCALE, "status": "published"}
            count = len(self.list_items(endpoint, params))
            ok = count >= expected_count
            results[endpoint] = {"expected": expected_count, "actual": count, "ok": ok}
            symbol = "✓" if ok else "✗"
            print(f"  {symbol} {endpoint}: {count}/{expected_count}")
            if not ok:
                all_ok = False
        return results

    def run(self):
        print("=" * 60)
        print("King-A (欣榮貿易) ForgeBase 內容匯入")
        print("=" * 60)

        self.login()
        self.import_pages()
        self.import_categories()
        self.import_products()
        self.import_applications()
        self.import_faqs()
        self.import_relationships()
        results = self.validate_counts()

        state = {
            "ids": self.ids,
            "summary": self.summary,
            "validation": results,
        }
        (ROOT / "import_state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))

        print(f"\n{'=' * 60}")
        print(f"匯入完成!")
        print(f"  建立: {self.summary['created']}")
        print(f"  更新: {self.summary['updated']}")
        print(f"  發布: {self.summary['published']}")
        print(f"  關聯: {self.summary['linked']}")
        print(f"  跳過: {self.summary['skipped']}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    try:
        KingAImporter().run()
    except Exception as exc:
        print(f"IMPORT_FAILED: {exc}", file=sys.stderr)
        raise
