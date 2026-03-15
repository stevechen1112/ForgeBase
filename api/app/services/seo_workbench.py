from __future__ import annotations

import re
from typing import Any

from app.core.config import settings


STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "your", "that", "this", "are", "you",
    "產品", "分類", "應用", "方案", "說明", "介紹", "我們", "以及", "提供", "適用", "用於",
    "industrial", "manufacturer", "manufacturing", "solutions", "solution", "company", "page",
}

ENTITY_LABELS = {
    "page": "頁面",
    "product": "產品",
    "category": "分類",
    "application": "應用場景",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _truncate(text: str, limit: int) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _entity_name(entity_type: str, data: dict[str, Any]) -> str:
    if entity_type == "product":
        base = " ".join(filter(None, [data.get("model_number"), data.get("product_name")]))
        return _clean_text(base) or "未命名產品"
    if entity_type == "category":
        return _clean_text(data.get("category_name")) or "未命名分類"
    if entity_type == "application":
        return _clean_text(data.get("application_name")) or "未命名應用場景"
    return _clean_text(data.get("title")) or "未命名頁面"


def _body_text(entity_type: str, data: dict[str, Any]) -> str:
    fields_by_type = {
        "product": ["short_description", "full_description", "specifications"],
        "category": ["description"],
        "application": ["description", "challenge", "solution"],
        "page": ["subtitle", "body"],
    }
    fields = fields_by_type.get(entity_type, ["description", "body"])
    return " ".join(filter(None, (_clean_text(data.get(field)) for field in fields))).strip()


def _extract_keywords(*parts: str) -> list[str]:
    combined = " ".join(filter(None, parts)).lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9\-]{2,}|[\u4e00-\u9fff]{2,}", combined)
    counts: dict[str, int] = {}
    for token in tokens:
        if token in STOPWORDS or token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _count in ranked[:5]]


def build_entity_path(entity_type: str, data: dict[str, Any], site_url: str | None = None) -> str:
    base = (site_url or settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")
    slug = _clean_text(data.get("slug"))
    locale = _clean_text(data.get("locale"))
    locale_prefix = f"/{locale}" if locale and locale != "en" else ""

    if entity_type == "product":
        category_slug = _clean_text(data.get("category_slug")) or "category"
        return f"{base}{locale_prefix}/products/{category_slug}/{slug}" if slug else f"{base}{locale_prefix}/products/{category_slug}"
    if entity_type == "category":
        return f"{base}{locale_prefix}/products/{slug}" if slug else f"{base}{locale_prefix}/products"
    if entity_type == "application":
        return f"{base}{locale_prefix}/applications/{slug}" if slug else f"{base}{locale_prefix}/applications"
    return f"{base}{locale_prefix}/{slug}" if slug else base


def _recommended_title(entity_type: str, data: dict[str, Any], keywords: list[str]) -> str:
    name = _entity_name(entity_type, data)
    keyword_suffix = f" | {keywords[0]}" if keywords else ""
    if entity_type == "product":
        title = f"{name} Technical Specifications & RFQ"
    elif entity_type == "category":
        title = f"{name} Products for Industrial Applications"
    elif entity_type == "application":
        title = f"{name} Solutions for Manufacturing Teams"
    else:
        title = name
    return _truncate(f"{title}{keyword_suffix}", 60)


def _recommended_description(entity_type: str, data: dict[str, Any], keywords: list[str]) -> str:
    name = _entity_name(entity_type, data)
    body = _body_text(entity_type, data)
    if body:
        return _truncate(body, 150)

    keyword_hint = f"，聚焦 {keywords[0]}" if keywords else ""
    if entity_type == "product":
        text = f"查看 {name} 的關鍵規格、應用情境與詢價方式{keyword_hint}。"
    elif entity_type == "category":
        text = f"快速了解 {name} 產品分類、典型應用與推薦產品{keyword_hint}。"
    elif entity_type == "application":
        text = f"了解 {name} 的常見挑戰、解法與適用產品{keyword_hint}。"
    else:
        text = f"了解 {name} 的核心資訊與下一步行動建議{keyword_hint}。"
    return _truncate(text, 155)


def audit_entity_payload(entity_type: str, data: dict[str, Any], site_url: str | None = None) -> dict[str, Any]:
    entity_name = _entity_name(entity_type, data)
    body = _body_text(entity_type, data)
    seo_title = _clean_text(data.get("seo_title"))
    seo_description = _clean_text(data.get("seo_description"))
    slug = _clean_text(data.get("slug"))
    keywords = _extract_keywords(entity_name, body, seo_title, seo_description)

    checks: list[dict[str, str]] = []
    score = 100
    suggestions: list[dict[str, Any]] = []

    def add_check(check_id: str, label: str, status: str, message: str, penalty: int = 0):
        nonlocal score
        checks.append({"id": check_id, "label": label, "status": status, "message": message})
        score -= penalty

    if not slug:
        add_check("slug", "網址路徑", "critical", "缺少網址路徑，頁面無法形成穩定搜尋入口。", 18)
    elif len(slug) < 3 or slug != slug.lower():
        add_check("slug", "網址路徑", "warning", "網址建議使用簡短、全小寫、可讀的 slug。", 8)
    else:
        add_check("slug", "網址路徑", "good", "網址可讀性良好。")

    if not seo_title:
        add_check("seo_title", "Google 標題", "critical", "尚未設定 Google 搜尋標題。", 18)
        suggestions.append({
            "id": "fill-seo-title",
            "title": "補上 Google 搜尋標題",
            "detail": "系統已根據目前內容生成一版建議標題，可直接採用後再微調。",
            "priority": "high",
            "field": "seo_title",
            "suggested_value": _recommended_title(entity_type, data, keywords),
        })
    elif len(seo_title) < 30:
        add_check("seo_title", "Google 標題", "warning", f"標題偏短，目前 {len(seo_title)} 字元，建議 30 到 60。", 8)
        suggestions.append({
            "id": "expand-seo-title",
            "title": "把標題寫得更完整",
            "detail": "可加入產品型號、用途或商業語意，提升搜尋結果辨識度。",
            "priority": "medium",
            "field": "seo_title",
            "suggested_value": _recommended_title(entity_type, data, keywords),
        })
    elif len(seo_title) > 60:
        add_check("seo_title", "Google 標題", "warning", f"標題偏長，目前 {len(seo_title)} 字元，可能被截斷。", 8)
    else:
        add_check("seo_title", "Google 標題", "good", "Google 標題長度適中。")

    if not seo_description:
        add_check("seo_description", "搜尋摘要", "critical", "尚未設定搜尋摘要。", 16)
        suggestions.append({
            "id": "fill-seo-description",
            "title": "補上搜尋摘要",
            "detail": "搜尋摘要會直接影響搜尋結果點擊率，建議至少補一版可讀描述。",
            "priority": "high",
            "field": "seo_description",
            "suggested_value": _recommended_description(entity_type, data, keywords),
        })
    elif len(seo_description) < 80:
        add_check("seo_description", "搜尋摘要", "warning", f"搜尋摘要偏短，目前 {len(seo_description)} 字元。", 8)
        suggestions.append({
            "id": "expand-seo-description",
            "title": "把搜尋摘要寫得更具體",
            "detail": "建議補充產品價值、應用情境或下一步行動，避免只寫名稱。",
            "priority": "medium",
            "field": "seo_description",
            "suggested_value": _recommended_description(entity_type, data, keywords),
        })
    elif len(seo_description) > 160:
        add_check("seo_description", "搜尋摘要", "warning", f"搜尋摘要偏長，目前 {len(seo_description)} 字元。", 6)
    else:
        add_check("seo_description", "搜尋摘要", "good", "搜尋摘要長度適中。")

    body_length = len(body)
    if body_length < 180:
        add_check("content_depth", "內容深度", "critical", f"內容偏少，目前約 {body_length} 字元。", 18)
        suggestions.append({
            "id": "increase-depth",
            "title": "補強頁面內容深度",
            "detail": "建議補上規格、應用情境、常見問題或導向詢價的說明，讓搜尋與業務都更容易理解頁面價值。",
            "priority": "high",
        })
    elif body_length < 420:
        add_check("content_depth", "內容深度", "warning", f"內容仍偏精簡，目前約 {body_length} 字元。", 8)
    else:
        add_check("content_depth", "內容深度", "good", "內容深度足以支撐搜尋與轉換。")

    if not keywords:
        add_check("focus_keywords", "主題清晰度", "warning", "目前內容主題不夠明確，系統難以萃取焦點關鍵詞。", 8)
    else:
        add_check("focus_keywords", "主題清晰度", "good", f"已辨識出重點主題：{', '.join(keywords[:3])}。")

    score = max(0, min(100, score))
    status = "healthy" if score >= 85 else "needs-work" if score >= 65 else "critical"
    summary = {
        "healthy": "整體 SEO 結構穩定，可持續微調搜尋表現。",
        "needs-work": "已有基礎，但還有幾個會影響曝光與點擊率的缺口。",
        "critical": "目前缺少關鍵 SEO 元素，建議先補齊再發佈。",
    }[status]

    recommended_title = _recommended_title(entity_type, data, keywords)
    recommended_description = _recommended_description(entity_type, data, keywords)
    search_title = seo_title or recommended_title
    search_description = seo_description or recommended_description
    url = build_entity_path(entity_type, data, site_url=site_url)

    return {
        "entity_type": entity_type,
        "entity_label": ENTITY_LABELS.get(entity_type, entity_type),
        "entity_name": entity_name,
        "score": score,
        "status": status,
        "summary": summary,
        "focus_keywords": keywords,
        "search_preview": {
            "title": search_title,
            "description": search_description,
            "url": url,
        },
        "checks": checks,
        "suggestions": suggestions,
        "recommended": {
            "seo_title": recommended_title,
            "seo_description": recommended_description,
            "canonical_url": url,
        },
    }