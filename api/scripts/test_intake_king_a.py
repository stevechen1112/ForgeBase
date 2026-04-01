"""
king-a.com.tw Intake 實測腳本 — 不需要 DB 連線即可驗證爬蟲與結構化邏輯。

用法：
  cd api
  python scripts/test_intake_king_a.py

會輸出：
  1. 全站 URL 清單（含頁型分類）
  2. 站點結構分析報告
  3. 建議的 Pilot 範圍
  4. 匯出的 JSON seed 檔案（可直接匯入 ForgeBase）
"""
import asyncio
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_URL = "https://king-a.com.tw/"
MAX_PAGES = 200
REQUEST_TIMEOUT = 20.0
USER_AGENT = "ForgeBase-Intake/1.0 (+https://forgebase.io)"

OUTPUT_DIR = Path(__file__).parent.parent.parent / "intake_output"

# ── Page type heuristics ──────────────────────────────────────────────────────

PAGE_TYPE_KEYWORDS = {
    "contact": ["聯絡", "聯繫", "contact", "聯絡我們", "諮詢"],
    "company": ["關於", "about", "沿革", "理念"],
    "product": ["產品", "product", "型號", "規格", "series", "機型",
                "熔接", "焊接", "焊機", "切割", "接著劑", "固化劑", "密封",
                "矽膠", "機械手臂", "手持式", "雷射", "離子", "焊槍",
                "零件", "配件", "樹脂", "固定劑", "加工機"],
    "category": ["系列", "category", "分類", "品牌", "brand"],
    "application": ["應用", "案例", "application", "solution", "案場", "搬運"],
    "faq": ["faq", "常見問題", "Q&A", "問答"],
    "resource": ["下載", "download", "型錄", "catalogue", "catalog"],
    "blog": ["新聞", "news", "最新", "公告", "消息"],
}


def classify_page(url: str, title: str, text: str) -> tuple[str, float]:
    """Classify page by URL pattern, title and text content — pure heuristic."""
    url_lower = url.lower()
    title_lower = (title or "").lower()
    combined = f"{url_lower} {title_lower} {text[:500].lower()}"

    scores: dict[str, float] = {}
    for ptype, keywords in PAGE_TYPE_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in combined:
                score += 1.0
            if kw in url_lower:
                score += 0.5
            if kw in title_lower:
                score += 0.5
        scores[ptype] = score

    # Special patterns
    if url == TARGET_URL or url == TARGET_URL.rstrip("/"):
        return "company", 0.9  # homepage

    # /article/ paths on this site are product detail pages, not blog posts
    if "/article/" in url_lower:
        scores["product"] = scores.get("product", 0) + 1.5
    if "/page/" in url_lower:
        scores["product"] = scores.get("product", 0) + 0.3

    # Suppress false 'company' when product signals are stronger
    if scores.get("product", 0) > scores.get("company", 0):
        scores["company"] = 0

    # Category pages: pages with multiple product links but no single spec
    if "/page/" in url_lower and title_lower:
        # Pages listing sub-items (e.g. "Panasonic CO2 & MAG 熔接機")
        # whose text has many model numbers likely are category pages
        model_count = len(re.findall(r'[A-Z]{1,5}[-_]?\d{2,5}', text[:2000]))
        if model_count >= 4:
            scores["category"] = scores.get("category", 0) + 2.0

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    if best_score < 0.5:
        return "unknown", 0.3
    confidence = min(best_score / 3.0, 1.0)
    return best_type, round(confidence, 2)


# ── Entity extraction heuristics ──────────────────────────────────────────────

def extract_products_from_page(soup: BeautifulSoup, url: str, title: str) -> list[dict]:
    """Try to extract product-like entities from HTML."""
    entities = []

    # Look for specification tables
    tables = soup.find_all("table")
    specs = {}
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                val = cells[1].get_text(strip=True)
                if key and val and len(key) < 100:
                    specs[key] = val

    # Look for images (product images)
    images = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src and not any(skip in src.lower() for skip in ["logo", "icon", "banner", "bg", "arrow"]):
            full_src = urljoin(url, src)
            images.append({"src": full_src, "alt": alt})

    # Look for model numbers (patterns like: TM-5, TS-950, GR-series)
    text = soup.get_text()
    model_patterns = re.findall(r'[A-Z]{1,5}[-_]?\d{2,5}[A-Z]?(?:[-/]\d+)?', text)
    model_numbers = list(set(model_patterns))[:10]  # dedupe, limit

    # Look for PDF download links
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if href.lower().endswith(".pdf"):
            pdfs.append({
                "url": urljoin(url, href),
                "text": a.get_text(strip=True) or "PDF",
            })

    entity = {
        "entity_type": "product",
        "display_name": title or "Unknown Product",
        "source_url": url,
        "model_numbers": model_numbers,
        "specifications": specs,
        "images": images[:5],  # limit
        "pdfs": pdfs,
    }

    if specs or model_numbers or pdfs:
        entity["confidence"] = 0.7
    else:
        entity["confidence"] = 0.4

    entities.append(entity)
    return entities


def extract_faq_from_page(soup: BeautifulSoup) -> list[dict]:
    """Try to extract FAQ Q&A pairs."""
    faqs = []
    # Look for patterns: <h3>Q: ...</h3> <p>A: ...</p>
    headers = soup.find_all(["h2", "h3", "h4", "dt"])
    for h in headers:
        q_text = h.get_text(strip=True)
        if not q_text or len(q_text) < 5:
            continue
        # Find the answer - next sibling p or dd
        answer_el = h.find_next_sibling(["p", "dd", "div"])
        if answer_el:
            a_text = answer_el.get_text(strip=True)
            if a_text:
                faqs.append({"question": q_text, "answer": a_text})

    return faqs


# ── Crawl ─────────────────────────────────────────────────────────────────────

async def crawl_site() -> dict:
    """Main crawl logic — returns full site analysis."""
    base_url = TARGET_URL
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc

    visited: set[str] = set()
    to_visit: list[str] = [base_url]
    pages: list[dict] = []

    print(f"\n{'='*60}")
    print(f"ForgeBase Legacy Site Intake — 實測")
    print(f"目標: {TARGET_URL}")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        verify=False,  # Some legacy sites have cert issues
    ) as client:
        while to_visit and len(visited) < MAX_PAGES:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            # Normalize
            current_url = current_url.split("#")[0].rstrip("/")
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                resp = await client.get(current_url)
            except Exception as exc:
                print(f"  ✗ {current_url}: {exc}")
                continue

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract metadata
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else None
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta_desc_tag.get("content", "") if meta_desc_tag else None

            visible_text = _extract_visible_text(soup)
            page_type, confidence = classify_page(current_url, title, visible_text)

            page_data = {
                "url": current_url,
                "title": title,
                "meta_description": meta_desc,
                "page_type": page_type,
                "confidence": confidence,
                "status_code": resp.status_code,
                "content_length": len(html),
                "text_preview": visible_text[:300],
            }

            # Extract entities based on type
            if page_type in ("product", "category"):
                page_data["extracted_entities"] = extract_products_from_page(soup, current_url, title)
            elif page_type == "faq":
                page_data["extracted_faqs"] = extract_faq_from_page(soup)

            pages.append(page_data)
            print(f"  ✓ [{page_type:10s}] ({confidence:.1f}) {title or current_url}")

            # Find internal links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(current_url, href)
                parsed = urlparse(full_url)
                if (
                    parsed.netloc == domain
                    and parsed.scheme in ("http", "https")
                    and full_url.split("#")[0].rstrip("/") not in visited
                ):
                    clean = full_url.split("#")[0].split("?")[0].rstrip("/")
                    if clean not in visited and clean not in to_visit:
                        to_visit.append(clean)

    return {
        "source_url": TARGET_URL,
        "crawled_at": datetime.now().isoformat(),
        "total_pages": len(pages),
        "pages": pages,
    }


def _extract_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyse(crawl_result: dict) -> dict:
    """Produce structured analysis report."""
    pages = crawl_result["pages"]

    # Type distribution
    type_dist: dict[str, list] = {}
    for p in pages:
        pt = p["page_type"]
        type_dist.setdefault(pt, []).append(p)

    # Collect all extracted entities
    all_products = []
    all_faqs = []
    for p in pages:
        all_products.extend(p.get("extracted_entities", []))
        all_faqs.extend(p.get("extracted_faqs", []))

    # Collect all model numbers
    all_models = set()
    for prod in all_products:
        all_models.update(prod.get("model_numbers", []))

    # Collect all PDFs
    all_pdfs = []
    for prod in all_products:
        all_pdfs.extend(prod.get("pdfs", []))

    report = {
        "summary": {
            "total_pages": len(pages),
            "pages_by_type": {k: len(v) for k, v in type_dist.items()},
            "total_products_extracted": len(all_products),
            "total_model_numbers": len(all_models),
            "total_pdfs": len(all_pdfs),
            "total_faqs": len(all_faqs),
        },
        "pages_by_type": {
            ptype: [{"url": p["url"], "title": p["title"]} for p in plist]
            for ptype, plist in type_dist.items()
        },
        "extracted_products": all_products,
        "extracted_faqs": all_faqs,
        "model_numbers": sorted(all_models),
        "pdf_resources": all_pdfs,
        "pilot_recommendation": generate_pilot_recommendation(type_dist, all_products),
        "forgebase_mapping": generate_forgebase_mapping(type_dist, all_products),
        "data_gaps": identify_data_gaps(pages, all_products),
    }

    return report


def generate_pilot_recommendation(type_dist: dict, products: list) -> dict:
    """Recommend what to include in the Pilot phase."""
    product_pages = type_dist.get("product", [])
    category_pages = type_dist.get("category", [])

    return {
        "recommended_strategy": "focused_product_line",
        "reasoning": "此站為多品牌代理商型態，建議聚焦單一產品線做 Pilot，避免定位失焦。",
        "suggested_pilot_scope": {
            "primary_line": "Panasonic 焊接機械手臂" if any("panasonic" in p.get("title", "").lower() for p in product_pages) else "主力產品線",
            "pages_to_build": [
                "1x Category 頁（焊接解決方案總覽）",
                "3-5x Product 頁（主力機型）",
                "1x Application 頁（典型焊接應用場景）",
                "1x FAQ 頁",
                "1x RFQ 表單頁（預填產品參數）",
            ],
            "estimated_content_pages": "6-8 頁",
            "estimated_time": "2-3 週",
        },
        "data_needed_from_client": [
            "主力機型確認（哪些型號還在推）",
            "原廠授權範圍說明",
            "技術規格書 PDF 原檔",
            "成功案例或客戶見證（若有）",
            "目標市場（台灣 / 東南亞 / 其他）",
            "業務回覆 SLA 承諾",
        ],
    }


def generate_forgebase_mapping(type_dist: dict, products: list) -> dict:
    """Map crawled content to ForgeBase entity structure."""
    return {
        "categories": [
            {"source": "Panasonic 焊接手臂", "target_entity": "category", "slug": "welding-robots"},
            {"source": "雷射焊接 / 切割", "target_entity": "category", "slug": "laser-welding"},
            {"source": "工業接著劑", "target_entity": "category", "slug": "industrial-adhesives"},
            {"source": "亞臨界水處理", "target_entity": "category", "slug": "subcritical-water"},
        ],
        "suggested_taxonomy": {
            "approach": "依買家任務分類，非依品牌分類",
            "top_level": ["焊接自動化", "雷射加工", "接合技術", "環保設備"],
            "reason": "原站以品牌分類（Panasonic / DAINICHI / 三鍵），但買家通常是按「我要解決什麼問題」來找。ForgeBase 應以任務與應用場景為第一層分類。",
        },
    }


def identify_data_gaps(pages: list, products: list) -> list[str]:
    """Identify what's missing for a complete ForgeBase import."""
    gaps = []

    # Check for English content
    has_en = any("en" in (p.get("url", "") + (p.get("title", "") or "")).lower() for p in pages)
    if not has_en:
        gaps.append("無英語內容 — ForgeBase 需要至少英語版本才能做外銷行銷")

    # Check for spec sheets
    total_specs = sum(len(p.get("specifications", {})) for p in products)
    if total_specs < 5:
        gaps.append("規格表資料稀少 — 需要企業補充產品技術規格")

    # Check for certifications
    all_text = " ".join(p.get("text_preview", "") for p in pages)
    cert_keywords = ["ISO", "CE", "UL", "VDE", "認證", "certificate"]
    found_certs = [k for k in cert_keywords if k.lower() in all_text.lower()]
    if not found_certs:
        gaps.append("未發現認證資訊 — 需要企業提供認證文件清單")

    # Check for testimonials
    testi_keywords = ["客戶", "案例", "見證", "testimonial", "case study"]
    found_testi = [k for k in testi_keywords if k.lower() in all_text.lower()]
    if not found_testi:
        gaps.append("無客戶見證或案例 — 建議企業提供至少 2-3 個成功案例")

    # Check for RFQ/Contact sophistication
    gaps.append("現有聯絡表單過於簡單 — ForgeBase 會建立分產品線的 RFQ 表單")
    gaps.append("無訪客追蹤機制 — ForgeBase 會加入意圖評分與 Dynamic CTA")

    return gaps


# ── Output ────────────────────────────────────────────────────────────────────

def print_report(report: dict) -> None:
    """Print analysis report to console."""
    s = report["summary"]

    print(f"\n{'='*60}")
    print("站點分析報告")
    print(f"{'='*60}")

    print(f"\n■ 總覽")
    print(f"  總頁數: {s['total_pages']}")
    print(f"  頁型分佈:")
    for ptype, count in sorted(s["pages_by_type"].items(), key=lambda x: -x[1]):
        print(f"    {ptype:15s} : {count} 頁")
    print(f"  抽取的產品實體: {s['total_products_extracted']}")
    print(f"  偵測的型號數: {s['total_model_numbers']}")
    print(f"  PDF 資源: {s['total_pdfs']}")
    print(f"  FAQ 條目: {s['total_faqs']}")

    print(f"\n■ 頁面清單（依類型）")
    for ptype, pages in report["pages_by_type"].items():
        print(f"\n  [{ptype}]")
        for p in pages:
            print(f"    - {p['title'] or '(無標題)'}")
            print(f"      {p['url']}")

    if report["model_numbers"]:
        print(f"\n■ 偵測到的型號")
        for m in report["model_numbers"][:20]:
            print(f"    {m}")

    if report["pdf_resources"]:
        print(f"\n■ PDF 資源")
        for pdf in report["pdf_resources"]:
            print(f"    {pdf['text']}: {pdf['url']}")

    pilot = report["pilot_recommendation"]
    print(f"\n■ Pilot 建議")
    print(f"  策略: {pilot['reasoning']}")
    ps = pilot["suggested_pilot_scope"]
    print(f"  主打產品線: {ps['primary_line']}")
    print(f"  預估頁數: {ps['estimated_content_pages']}")
    print(f"  預估時程: {ps['estimated_time']}")
    print(f"  建議頁面:")
    for page in ps["pages_to_build"]:
        print(f"    - {page}")
    print(f"  需企業補充的資料:")
    for d in pilot["data_needed_from_client"]:
        print(f"    - {d}")

    mapping = report["forgebase_mapping"]
    print(f"\n■ ForgeBase 結構映射")
    print(f"  分類策略: {mapping['suggested_taxonomy']['approach']}")
    print(f"  建議頂層分類: {', '.join(mapping['suggested_taxonomy']['top_level'])}")
    for cat in mapping["categories"]:
        print(f"    {cat['source']} → /{cat['slug']}/")

    print(f"\n■ 資料缺口")
    for gap in report["data_gaps"]:
        print(f"  ⚠ {gap}")

    print(f"\n{'='*60}")
    print("報告結束")
    print(f"{'='*60}\n")


def save_outputs(crawl_result: dict, report: dict) -> None:
    """Save to files for later reference."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Raw crawl data
    crawl_path = OUTPUT_DIR / "king_a_crawl_raw.json"
    with open(crawl_path, "w", encoding="utf-8") as f:
        json.dump(crawl_result, f, ensure_ascii=False, indent=2)
    print(f"✓ 原始爬取資料已儲存: {crawl_path}")

    # Analysis report
    report_path = OUTPUT_DIR / "king_a_analysis_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✓ 分析報告已儲存: {report_path}")

    # ForgeBase seed file (entities ready for import)
    seed_data = {
        "project_name": "欣榮貿易（king-a.com.tw）導入",
        "source_url": TARGET_URL,
        "generated_at": datetime.now().isoformat(),
        "url_candidates": [
            {
                "url": p["url"],
                "page_type": p["page_type"],
                "title": p["title"],
                "confidence": p["confidence"],
                "review_status": "pending",
            }
            for p in crawl_result["pages"]
        ],
        "entity_candidates": report["extracted_products"],
        "redirect_candidates": [
            {
                "from_path": urlparse(p["url"]).path,
                "suggested_to_path": None,  # To be filled after taxonomy setup
                "review_status": "pending",
            }
            for p in crawl_result["pages"]
            if p["page_type"] in ("product", "category", "application")
        ],
        "data_gaps": report["data_gaps"],
        "pilot_recommendation": report["pilot_recommendation"],
    }
    seed_path = OUTPUT_DIR / "king_a_forgebase_seed.json"
    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(seed_data, f, ensure_ascii=False, indent=2)
    print(f"✓ ForgeBase seed 檔案已儲存: {seed_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("開始爬取 king-a.com.tw ...")
    crawl_result = await crawl_site()

    print(f"\n爬取完成，共 {crawl_result['total_pages']} 頁")
    print("正在分析...")

    report = analyse(crawl_result)
    print_report(report)
    save_outputs(crawl_result, report)

    print("\n完成！你可以在 intake_output/ 目錄查看所有輸出檔案。")


if __name__ == "__main__":
    asyncio.run(main())
