"""
End-to-End Intake Pipeline for king-a.com.tw
=============================================

This script simulates the full intake pipeline:
  1. Crawl king-a.com.tw → discover URLs → classify pages
  2. Extract entities from product/category/application pages
  3. Generate redirect map + PageBrief drafts
  4. Output ForgeBase-ready seed data for import

Can run standalone (no DB required) — outputs to intake_output/ directory.
"""
import asyncio
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_URL = "https://king-a.com.tw/"
MAX_PAGES = 200
REQUEST_TIMEOUT = 20.0
USER_AGENT = "ForgeBase-Intake/1.0 (+https://forgebase.io)"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "intake_output"

# ── Manufacturing / B2B keyword banks for smart classification ────────────────

PRODUCT_KEYWORDS = {
    "zh": [
        "型號", "規格", "額定", "輸出", "電流", "電壓", "功率", "重量",
        "焊接", "切割", "加工", "手臂", "機器人", "雷射", "CO2", "MAG",
        "TIG", "MIG", "定位", "搬運", "伺服", "馬達", "變頻", "驅動",
        "感測", "控制器", "機台", "設備", "工具", "模組", "機種",
        "最大", "最小", "精度", "速度", "容量", "耐壓", "絕緣",
    ],
    "en": [
        "model", "spec", "rated", "output", "current", "voltage", "power",
        "weight", "welding", "cutting", "robot", "laser", "servo", "motor",
        "controller", "machine", "tool", "module", "capacity", "precision",
    ],
}

CATEGORY_KEYWORDS = {
    "zh": ["系列", "產品線", "產品類", "全系列", "機種一覽", "品項", "分類"],
    "en": ["series", "product line", "lineup", "catalogue", "catalog", "range"],
}

APPLICATION_KEYWORDS = {
    "zh": ["應用", "解決方案", "案例", "實績", "導入", "用途", "場景"],
    "en": ["application", "solution", "case study", "use case", "industry"],
}

FAQ_KEYWORDS = {
    "zh": ["常見問題", "FAQ", "Q&A", "問答"],
    "en": ["faq", "frequently asked", "q&a", "questions"],
}

CONTACT_KEYWORDS = {
    "zh": ["聯絡", "聯繫", "洽詢", "預約", "諮詢", "留言"],
    "en": ["contact", "inquiry", "enquiry", "get in touch"],
}

COMPANY_KEYWORDS = {
    "zh": ["公司", "關於", "沿革", "理念", "團隊", "據點", "營業"],
    "en": ["about", "company", "history", "team", "mission"],
}


# ── Utility functions ─────────────────────────────────────────────────────────

def extract_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:120]


def keyword_score(text: str, keywords: dict[str, list[str]]) -> int:
    """Count how many keywords appear in the text."""
    text_lower = text.lower()
    score = 0
    for lang_kws in keywords.values():
        for kw in lang_kws:
            if kw.lower() in text_lower:
                score += 1
    return score


def classify_page(url: str, title: str, text: str) -> tuple[str, float]:
    """Classify a page using keyword scoring + URL pattern heuristics."""
    path = urlparse(url).path.lower()
    combined = f"{title} {text[:2000]}"

    scores = {
        "product": keyword_score(combined, PRODUCT_KEYWORDS),
        "category": keyword_score(combined, CATEGORY_KEYWORDS),
        "application": keyword_score(combined, APPLICATION_KEYWORDS),
        "faq": keyword_score(combined, FAQ_KEYWORDS),
        "contact": keyword_score(combined, CONTACT_KEYWORDS),
        "company": keyword_score(combined, COMPANY_KEYWORDS),
    }

    # URL-based overrides
    if any(k in path for k in ["/contact", "/inquiry"]):
        return "contact", 0.95
    if any(k in path for k in ["/about", "/company"]):
        return "company", 0.9
    if "faq" in path:
        return "faq", 0.95

    # For /article/ and /page/ URLs (common CMS patterns in Taiwan)
    if "/article/" in path:
        # Articles are usually product detail pages
        if scores["product"] >= 3:
            return "product", min(0.5 + scores["product"] * 0.05, 0.95)
        return "product", 0.6  # default assumption for article pages

    if "/page/" in path:
        # Pages can be categories or product listings
        if scores["category"] >= 2:
            return "category", min(0.5 + scores["category"] * 0.1, 0.95)
        if scores["product"] >= 5:
            return "product", min(0.5 + scores["product"] * 0.05, 0.95)
        if scores["application"] >= 2:
            return "application", min(0.5 + scores["application"] * 0.1, 0.95)
        # Default for /page/ with product keywords
        if scores["product"] >= 2:
            return "category", 0.6
        return "company", 0.5

    # Fallback — pick highest scoring category
    best = max(scores, key=lambda k: scores[k])
    if scores[best] >= 3:
        return best, min(0.5 + scores[best] * 0.05, 0.9)

    return "unknown", 0.3


def extract_specs_from_text(text: str) -> list[dict[str, str]]:
    """Try to extract specification key-value pairs from text."""
    specs = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        # Common patterns: "額定輸出電流：350A" or "重量: 125kg"
        for sep in ["：", ":", "＝", "="]:
            if sep in line:
                parts = line.split(sep, 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if key and val and len(key) < 30 and len(val) < 100:
                    specs.append({"key": key, "value": val})
                break
    return specs


def extract_model_numbers(text: str) -> list[str]:
    """Extract model numbers using regex patterns common in manufacturing."""
    patterns = [
        r'\b[A-Z]{2,6}[-]?\d{2,5}[A-Z]{0,3}\b',           # e.g. YD-350NR1, GZ4
        r'\b[A-Z]\d{3,5}[A-Z]{0,2}\d{0,2}\b',              # e.g. G400VP1
        r'\b[A-Z]{2,4}\d{2}[A-Z]?\b',                       # e.g. RJB22Y
        r'\bTM\d+[A-Z]?\b',                                  # e.g. TM14
        r'\b[A-Z]{2,3}-\d{3,5}[A-Z]*\d*\b',                 # e.g. YD-350NR1
    ]
    models = set()
    for pat in patterns:
        for match in re.finditer(pat, text):
            m = match.group()
            if len(m) >= 3 and not m.startswith("HTTP") and m not in ("FAQ", "URL", "CMS", "PDF", "SEO"):
                models.add(m)
    return sorted(models)


def extract_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract image URLs, filtering out icons and tracking pixels."""
    images = []
    for img in soup.find_all("img", src=True):
        src = urljoin(base_url, img["src"])
        # Skip tiny images (likely icons/spacers)
        width = img.get("width", "999")
        height = img.get("height", "999")
        try:
            if int(width) < 50 or int(height) < 50:
                continue
        except (ValueError, TypeError):
            pass
        if any(skip in src.lower() for skip in ["icon", "logo", "spacer", "pixel", "tracking", ".svg"]):
            continue
        images.append(src)
    return images[:10]  # limit


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def crawl_site(base_url: str) -> list[dict[str, Any]]:
    """Phase 1: Discover and fetch all pages."""
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc
    discovered: list[dict[str, Any]] = []
    to_visit = [base_url]
    visited: set[str] = set()
    pdf_urls: list[dict[str, str]] = []

    logger.info("Starting crawl of %s", base_url)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        while to_visit and len(discovered) < MAX_PAGES:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                resp = await client.get(current_url)
            except Exception as exc:
                logger.warning("Skip %s: %s", current_url, exc)
                continue

            if resp.status_code >= 400:
                continue

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta_tag.get("content", "") if meta_tag else ""
            visible_text = extract_visible_text(BeautifulSoup(html, "html.parser"))

            page_type, confidence = classify_page(current_url, title, visible_text)

            page_data = {
                "url": current_url,
                "title": title,
                "meta_description": meta_desc,
                "page_type": page_type,
                "confidence": confidence,
                "text": visible_text[:8000],
                "html_length": len(html),
                "images": extract_images(soup, current_url),
                "models": extract_model_numbers(visible_text),
                "specs": extract_specs_from_text(visible_text),
            }
            discovered.append(page_data)

            # Extract links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(current_url, href)
                parsed = urlparse(full_url)
                if parsed.netloc == domain and parsed.scheme in ("http", "https"):
                    clean_url = full_url.split("?")[0].split("#")[0]
                    if clean_url.lower().endswith(".pdf"):
                        link_text = link.get_text(strip=True) or "PDF"
                        pdf_urls.append({"url": clean_url, "title": link_text})
                    elif clean_url not in visited:
                        to_visit.append(clean_url)

    logger.info("Crawl complete: %d pages, %d PDFs", len(discovered), len(pdf_urls))
    return discovered


def extract_entities(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Phase 2: Extract entities from classified pages."""
    entities: list[dict[str, Any]] = []

    for page in pages:
        if page["page_type"] in ("contact", "company", "unknown"):
            continue

        entity: dict[str, Any] = {
            "source_url": page["url"],
            "entity_type": page["page_type"],
            "display_name": page["title"].replace("欣榮貿易", "").strip().strip(" -—|·"),
            "confidence": page["confidence"],
            "extracted_data": {},
        }

        data = entity["extracted_data"]

        if page["page_type"] == "product":
            data["product_name"] = entity["display_name"]
            data["model_numbers"] = page["models"]
            data["specifications"] = page["specs"]
            data["images"] = page["images"]
            data["short_description"] = page["text"][:300]

        elif page["page_type"] == "category":
            data["category_name"] = entity["display_name"]
            data["description"] = page["text"][:500]
            # Count sub-pages that might belong to this category
            data["estimated_products"] = len(page["models"])

        elif page["page_type"] == "application":
            data["application_name"] = entity["display_name"]
            data["description"] = page["text"][:500]
            data["related_models"] = page["models"]

        elif page["page_type"] == "faq":
            # Try to extract Q&A pairs
            pairs = []
            lines = page["text"].split("\n")
            q, a = None, []
            for line in lines:
                line = line.strip()
                if line.startswith(("Q:", "Q：", "問：", "問:")):
                    if q:
                        pairs.append({"question": q, "answer": " ".join(a)})
                    q = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                    a = []
                elif line.startswith(("A:", "A：", "答：", "答:")):
                    a.append(line.split(":", 1)[-1].split("：", 1)[-1].strip())
                elif q:
                    a.append(line)
            if q:
                pairs.append({"question": q, "answer": " ".join(a)})
            data["questions"] = pairs

        entities.append(entity)

    logger.info("Extracted %d entities", len(entities))
    return entities


def generate_redirects(pages: list[dict[str, Any]], entities: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Phase 3: Generate redirect map from old URLs to ForgeBase slugs."""
    PREFIX_MAP = {
        "product": "/products/",
        "category": "/categories/",
        "application": "/applications/",
        "faq": "/faq",
    }
    entity_by_url = {e["source_url"]: e for e in entities}
    redirects = []

    for page in pages:
        if page["page_type"] in ("contact", "company", "unknown"):
            continue
        parsed = urlparse(page["url"])
        from_path = parsed.path
        if not from_path or from_path == "/":
            continue

        prefix = PREFIX_MAP.get(page["page_type"], "/")
        entity = entity_by_url.get(page["url"])
        if entity and entity["display_name"]:
            slug = slugify(entity["display_name"])
        else:
            slug = slugify(page["title"])

        to_path = f"{prefix}{slug}" if prefix != "/faq" else "/faq"

        redirects.append({
            "from_path": from_path,
            "to_path": to_path,
            "page_type": page["page_type"],
        })

    logger.info("Generated %d redirects", len(redirects))
    return redirects


def generate_briefs(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Phase 4: Generate PageBrief drafts with SEO + buyer persona."""
    BUYER_STAGE = {
        "product": "consideration",
        "category": "awareness",
        "application": "awareness",
        "faq": "awareness",
    }
    AUDIENCE = {
        "product": "Engineers, procurement managers, and technical buyers evaluating specific models",
        "category": "B2B buyers exploring product categories and comparing options",
        "application": "Decision-makers researching solutions for specific industrial challenges",
        "faq": "Potential buyers with pre-purchase questions about products and services",
    }
    CTA = {
        "product": "request_quote",
        "category": "browse_products",
        "application": "contact_specialist",
        "faq": "contact_us",
    }

    briefs = []
    for entity in entities:
        etype = entity["entity_type"]
        data = entity.get("extracted_data", {})
        display = entity["display_name"]

        primary_kw = (
            data.get("product_name")
            or data.get("category_name")
            or data.get("application_name")
            or display
        )

        secondary_kws = []
        if data.get("model_numbers"):
            secondary_kws.extend(data["model_numbers"][:5])
        if isinstance(data.get("related_models"), list):
            secondary_kws.extend(data["related_models"][:3])

        brief = {
            "entity_display_name": display,
            "target_page_type": etype,
            "suggested_slug": slugify(display),
            "title_draft": display,
            "primary_keyword": primary_kw,
            "secondary_keywords": secondary_kws,
            "audience_persona": AUDIENCE.get(etype, "B2B industrial buyers"),
            "buyer_stage": BUYER_STAGE.get(etype, "awareness"),
            "main_cta_key": CTA.get(etype, "contact_us"),
            "word_count_target": 800 if etype == "product" else 600,
            "confidence": entity["confidence"],
        }
        briefs.append(brief)

    logger.info("Generated %d PageBrief drafts", len(briefs))
    return briefs


def build_analysis_report(
    pages: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    redirects: list[dict[str, str]],
    briefs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build comprehensive analysis report with Pilot recommendation."""
    type_counts = Counter(p["page_type"] for p in pages)
    entity_type_counts = Counter(e["entity_type"] for e in entities)

    all_models = []
    for e in entities:
        if e["entity_type"] == "product":
            all_models.extend(e.get("extracted_data", {}).get("model_numbers", []))

    # Find which entities have the richest content
    richest = sorted(
        [e for e in entities if e["entity_type"] == "product"],
        key=lambda e: (
            len(e.get("extracted_data", {}).get("specifications", [])),
            len(e.get("extracted_data", {}).get("model_numbers", [])),
        ),
        reverse=True,
    )

    pilot_candidates = [
        {
            "display_name": e["display_name"],
            "model_count": len(e.get("extracted_data", {}).get("model_numbers", [])),
            "spec_count": len(e.get("extracted_data", {}).get("specifications", [])),
            "url": e["source_url"],
        }
        for e in richest[:10]
    ]

    # Content gap analysis
    gaps = []
    if entity_type_counts.get("application", 0) < 3:
        gaps.append("應用場景頁面不足，建議新增至少 3 個應用案例頁面")
    if entity_type_counts.get("faq", 0) < 1:
        gaps.append("缺少 FAQ 頁面，建議整理常見問題")
    has_specs = sum(1 for e in entities if len(e.get("extracted_data", {}).get("specifications", [])) > 3)
    if has_specs < len([e for e in entities if e["entity_type"] == "product"]) * 0.5:
        gaps.append("超過一半的產品頁面缺少結構化規格表，需要補充")
    if not any("認證" in (p.get("title") or "") or "ISO" in (p.get("text") or "")[:500] for p in pages):
        gaps.append("未發現認證相關頁面，建議新增認證/品質保證頁面")

    report = {
        "site_url": TARGET_URL,
        "crawl_date": "2026-03-31",
        "summary": {
            "total_pages_crawled": len(pages),
            "pages_by_type": dict(type_counts),
            "total_entities_extracted": len(entities),
            "entities_by_type": dict(entity_type_counts),
            "total_model_numbers_found": len(set(all_models)),
            "model_numbers": sorted(set(all_models)),
            "total_redirects": len(redirects),
            "total_briefs": len(briefs),
        },
        "pilot_recommendation": {
            "strategy": "Start with the richest product pages that have the most specifications and model numbers",
            "top_candidates": pilot_candidates,
            "suggested_pilot_page_count": min(10, len(pilot_candidates)),
        },
        "content_gaps": gaps,
        "intake_readiness": {
            "can_auto_extract": True,
            "estimated_manual_review_hours": max(2, len(entities) // 10),
            "recommended_approach": "standard_intake" if len(entities) > 10 else "pilot_intake",
        },
    }
    return report


async def main():
    """Run the full pipeline."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Phase 1: Crawl
    print("\n" + "=" * 60)
    print("Phase 1: 網站探索 (Site Discovery)")
    print("=" * 60)
    pages = await crawl_site(TARGET_URL)
    print(f"  → 發現 {len(pages)} 個頁面")

    type_counts = Counter(p["page_type"] for p in pages)
    for ptype, count in type_counts.most_common():
        print(f"    {ptype}: {count}")

    # Phase 2: Extract
    print("\n" + "=" * 60)
    print("Phase 2: 實體抽取 (Entity Extraction)")
    print("=" * 60)
    entities = extract_entities(pages)
    entity_types = Counter(e["entity_type"] for e in entities)
    for etype, count in entity_types.most_common():
        print(f"    {etype}: {count}")

    all_models = []
    for e in entities:
        all_models.extend(e.get("extracted_data", {}).get("model_numbers", []))
    unique_models = sorted(set(all_models))
    print(f"  → 偵測到 {len(unique_models)} 個型號")
    if unique_models:
        print(f"    範例: {', '.join(unique_models[:15])}")

    # Phase 3: Redirects
    print("\n" + "=" * 60)
    print("Phase 3: Redirect 對應表 (SEO Migration)")
    print("=" * 60)
    redirects = generate_redirects(pages, entities)
    print(f"  → 產生 {len(redirects)} 筆 redirect 候選")
    for r in redirects[:5]:
        print(f"    {r['from_path']} → {r['to_path']}")
    if len(redirects) > 5:
        print(f"    ... 及其他 {len(redirects) - 5} 筆")

    # Phase 4: Briefs
    print("\n" + "=" * 60)
    print("Phase 4: PageBrief 草稿 (Content Strategy)")
    print("=" * 60)
    briefs = generate_briefs(entities)
    print(f"  → 產生 {len(briefs)} 份 PageBrief 草稿")
    for b in briefs[:5]:
        print(f"    [{b['target_page_type']}] {b['title_draft']} → /{b['suggested_slug']}")
        print(f"       主關鍵字: {b['primary_keyword']} · 買家階段: {b['buyer_stage']}")

    # Phase 5: Analysis report
    print("\n" + "=" * 60)
    print("Phase 5: 分析報告 (Analysis Report)")
    print("=" * 60)
    report = build_analysis_report(pages, entities, redirects, briefs)

    if report["content_gaps"]:
        print("  內容缺口:")
        for gap in report["content_gaps"]:
            print(f"    ⚠ {gap}")

    print(f"\n  Pilot 建議:")
    print(f"    策略: {report['pilot_recommendation']['strategy']}")
    print(f"    建議起步頁數: {report['pilot_recommendation']['suggested_pilot_page_count']}")
    print(f"    預估人工審核時數: {report['intake_readiness']['estimated_manual_review_hours']}h")

    # Save outputs
    print("\n" + "=" * 60)
    print("輸出檔案 (Output Files)")
    print("=" * 60)

    # 1. Raw crawl data
    crawl_path = OUTPUT_DIR / "king_a_crawl_raw.json"
    crawl_path.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ {crawl_path.name} ({len(pages)} pages)")

    # 2. Analysis report
    report_path = OUTPUT_DIR / "king_a_analysis_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ {report_path.name}")

    # 3. ForgeBase seed (URL candidates + entities + redirects + briefs)
    seed = {
        "project": {
            "project_name": "欣榮貿易 (king-a.com.tw) 導入",
            "source_url": TARGET_URL,
            "locale": "zh-tw",
        },
        "url_candidates": [
            {
                "url": p["url"],
                "page_type": p["page_type"],
                "title": p["title"],
                "confidence": p["confidence"],
            }
            for p in pages
        ],
        "entity_candidates": [
            {
                "entity_type": e["entity_type"],
                "display_name": e["display_name"],
                "extracted_data": e["extracted_data"],
                "confidence": e["confidence"],
                "source_url": e["source_url"],
            }
            for e in entities
        ],
        "redirect_candidates": redirects,
        "brief_candidates": briefs,
    }
    seed_path = OUTPUT_DIR / "king_a_forgebase_seed.json"
    seed_path.write_text(
        json.dumps(seed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ {seed_path.name}")

    # 4. ForgeBase-ready content (products, categories, etc.)
    content_seed = {
        "categories": [],
        "products": [],
        "applications": [],
        "faq_items": [],
    }
    for e in entities:
        data = e.get("extracted_data", {})
        if e["entity_type"] == "category":
            content_seed["categories"].append({
                "name": e["display_name"],
                "slug": slugify(e["display_name"]),
                "description": data.get("description", ""),
            })
        elif e["entity_type"] == "product":
            content_seed["products"].append({
                "name": e["display_name"],
                "slug": slugify(e["display_name"]),
                "model_numbers": data.get("model_numbers", []),
                "short_description": data.get("short_description", ""),
                "specifications": data.get("specifications", []),
                "images": data.get("images", []),
            })
        elif e["entity_type"] == "application":
            content_seed["applications"].append({
                "name": e["display_name"],
                "slug": slugify(e["display_name"]),
                "description": data.get("description", ""),
                "related_models": data.get("related_models", []),
            })
        elif e["entity_type"] == "faq":
            for q in data.get("questions", []):
                content_seed["faq_items"].append(q)

    content_path = OUTPUT_DIR / "king_a_content_seed.json"
    content_path.write_text(
        json.dumps(content_seed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ {content_path.name}")

    print("\n" + "=" * 60)
    print("Pipeline 完成！")
    print(f"  所有輸出已儲存至: {OUTPUT_DIR}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    asyncio.run(main())
