#!/opt/homebrew/bin/python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_BASE = os.environ.get("FORGEBASE_API_BASE", "http://localhost:8000/api/v1").rstrip("/")
LOGIN_EMAIL = os.environ.get("FORGEBASE_DEMO_IMPORT_EMAIL", "admin@forgebase.com")
LOGIN_PASSWORD = os.environ.get("FORGEBASE_DEMO_IMPORT_PASSWORD", "")
LOCALE = "en"

PUBLISHABLE_ENDPOINTS = {
    "categories",
    "products",
    "applications",
    "faqs",
    "certifications",
    "comparisons",
    "pages",
}


def load_json(name: str):
    return json.loads((ROOT / name).read_text())


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


class Importer:
    def __init__(self):
        self.token = ""
        self.ids = {
            "categories": {},
            "products": {},
            "applications": {},
            "certifications": {},
            "capabilities": {},
            "faqs": {},
            "comparisons": {},
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
        if not LOGIN_PASSWORD:
            raise RuntimeError("Set FORGEBASE_DEMO_IMPORT_PASSWORD before importing demo content")
        _, body = api_request(
            "POST",
            "/auth/login",
            {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
            expected=(200,),
        )
        self.token = body["access_token"]

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
        if endpoint == "certifications" and post_payload.get("status") == "published":
            post_payload["status"] = "active"

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

    def import_pages(self):
        for page in load_json("pages.json"):
            existing = self.get_page_by_slug(page["slug"])
            item = self.create_or_update("pages", page, "slug", page["slug"], existing)
            self.ids["pages"][page["slug"]] = item["id"]
            print(f"page: {page['slug']}")

    def import_categories(self):
        for category in load_json("categories.json"):
            existing = self.get_by_slug("categories", category["slug"])
            item = self.create_or_update("categories", category, "slug", category["slug"], existing)
            self.ids["categories"][category["slug"]] = item["id"]
            print(f"category: {category['slug']}")

    def import_products(self):
        for product in load_json("products.json"):
            payload = dict(product)
            category_slug = payload.pop("category_slug")
            payload["category_id"] = self.ids["categories"][category_slug]
            existing = self.get_product_by_model(product["model_number"])
            item = self.create_or_update("products", payload, "model_number", product["model_number"], existing)
            self.ids["products"][product["model_number"]] = item["id"]
            print(f"product: {product['model_number']}")

    def import_slug_endpoint(self, endpoint: str, filename: str, key: str):
        for item_in in load_json(filename):
            existing = self.get_by_slug(endpoint, item_in["slug"])
            item = self.create_or_update(endpoint, item_in, "slug", item_in["slug"], existing)
            self.ids[key][item_in["slug"]] = item["id"]
            print(f"{endpoint[:-1]}: {item_in['slug']}")

    def import_faqs(self):
        for faq in load_json("faq-items.json"):
            existing = self.get_by_question(faq["question"])
            item = self.create_or_update("faqs", faq, "question", faq["question"], existing)
            self.ids["faqs"][faq["question"]] = item["id"]
            print(f"faq: {faq['question']}")

    def link(self, path: str):
        _, _ = api_request("POST", path, {}, token=self.token, expected=(200, 201))
        self.summary["linked"] += 1

    def import_relationships(self):
        relationships = load_json("relationships.json")

        for row in relationships["product_application_links"]:
            self.link(
                f"/content/products/{self.ids['products'][row['product_model_number']]}/applications/{self.ids['applications'][row['application_slug']]}"
            )

        for row in relationships["product_certification_links"]:
            self.link(
                f"/content/products/{self.ids['products'][row['product_model_number']]}/certifications/{self.ids['certifications'][row['cert_slug']]}"
            )

        for row in relationships["product_faq_links"]:
            self.link(
                f"/content/products/{self.ids['products'][row['product_model_number']]}/faqs/{self.ids['faqs'][row['faq_question']]}"
            )

        for row in relationships["application_faq_links"]:
            self.link(
                f"/content/applications/{self.ids['applications'][row['application_slug']]}/faqs/{self.ids['faqs'][row['faq_question']]}"
            )

        # Product -> Comparison links are planned in relationships.json but no API exists yet.
        skipped = len(relationships.get("product_comparison_links", []))
        self.summary["skipped"] += skipped
        if skipped:
            print(f"skipped product_comparison_links: {skipped} (no current API endpoint)")

    def validate_counts(self):
        checks = {
            "categories": 5,
            "products": 32,
            "applications": 6,
            "certifications": 5,
            "capabilities": 6,
            "faqs": 18,
            "comparisons": 8,
            "pages": 4,
        }
        results = {}
        for endpoint, expected_count in checks.items():
            params = {"page_size": "100", "locale": LOCALE}
            if endpoint in {"categories", "products", "applications", "faqs", "comparisons", "pages", "capabilities"}:
                params["status"] = "published"
            if endpoint == "certifications":
                params["status"] = "published"
            count = len(self.list_items(endpoint, params))
            results[endpoint] = {"expected": expected_count, "actual": count}
        return results

    def run(self):
        self.login()
        self.import_pages()
        self.import_categories()
        self.import_products()
        self.import_slug_endpoint("applications", "applications.json", "applications")
        self.import_slug_endpoint("certifications", "certifications.json", "certifications")
        self.import_slug_endpoint("capabilities", "capabilities.json", "capabilities")
        self.import_faqs()
        self.import_slug_endpoint("comparisons", "comparison-topics.json", "comparisons")
        self.import_relationships()
        results = self.validate_counts()
        state = {
            "ids": self.ids,
            "summary": self.summary,
            "validation": results,
        }
        (ROOT / "import_state.json").write_text(json.dumps(state, indent=2))
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    try:
        Importer().run()
    except Exception as exc:
        print(f"IMPORT_FAILED: {exc}", file=sys.stderr)
        raise
