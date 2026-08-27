"""Whitelist tenant-editable site copy, images, and nav labels."""
from __future__ import annotations

import json
from typing import Any

from app.core.locale import normalize_locale

LOCALE_KEYS = ("en", "zh-TW")
ASSET_KEYS = ("homeHero", "aboutHero", "productsHero", "qualityInspection", "customPackaging")
HIDDEN_BLOCK_KEYS = (
    "productInspection",
    "productPackaging",
    "productReadiness",
    "productSpecControl",
    "productContext",
)
STRING_PATHS = {
    "header.nav.products",
    "header.nav.applications",
    "header.nav.certifications",
    "header.nav.about",
    "header.nav.contact",
    "home.hero.eyebrow",
    "home.hero.titleLine1",
    "home.hero.titleLine2",
    "home.hero.description",
    "home.featured.title",
    "home.featured.description",
    "home.why.title",
    "home.why.description",
    "home.finalCta.title",
    "home.finalCta.description",
    "about.heroTitle",
    "about.heroDescription",
    "about.storyTitle",
    "about.ctaTitle",
    "about.ctaDescription",
    "productDetail.introBox",
    "productDetail.inspectionTitle",
    "productDetail.inspectionDescription",
    "productDetail.packagingTitle",
    "productDetail.packagingDescription",
    "productDetail.readinessTitle",
    "productDetail.readinessDescription",
    "productDetail.specControlTitle",
    "productDetail.specControlDescription",
    "productDetail.contextTitle",
    "productDetail.contextDescription",
    "newsPage.title",
    "newsPage.description",
}
STAT_PATHS = {"home.stats", "about.stats"}
STORY_PATH = "about.storyParagraphs"
TIMELINE_PATH = "about.timeline"
NEWS_ITEMS_PATH = "newsPage.items"
MAX_STRING = 2000


def parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def locale_key(raw: str | None) -> str:
    normalized = normalize_locale(raw, default="en")
    return "zh-TW" if normalized.lower().startswith("zh") else "en"


def _has_path(tree: dict[str, Any], path: str) -> bool:
    cursor: Any = tree
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return False
        cursor = cursor[part]
    return True


def _get_path(tree: dict[str, Any], path: str) -> Any:
    cursor: Any = tree
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _set_path(tree: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = tree
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = value


def _delete_path(tree: dict[str, Any], path: str) -> None:
    parts = path.split(".")
    cursor: Any = tree
    stack: list[tuple[dict[str, Any], str]] = []
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            return
        stack.append((cursor, part))
        cursor = cursor[part]
    if isinstance(cursor, dict):
        cursor.pop(parts[-1], None)
    for parent, key in reversed(stack):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key, None)


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:MAX_STRING]


def _clean_stats(value: Any) -> list[dict[str, str]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("stats must be a list")
    rows: list[dict[str, str]] = []
    for item in value[:6]:
        if not isinstance(item, dict):
            continue
        label = _clean_string(item.get("label")) or ""
        stat = _clean_string(item.get("value")) or ""
        if label or stat:
            rows.append({"value": stat[:40], "label": label[:80]})
    return rows


def _clean_paragraphs(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("story paragraphs must be a list")
    return [text for text in (_clean_string(item) for item in value[:8]) if text]


def _clean_timeline(value: Any) -> list[dict[str, str]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("timeline must be a list")
    rows: list[dict[str, str]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        year = _clean_string(item.get("year")) or ""
        event = _clean_string(item.get("event")) or ""
        if year or event:
            rows.append({"year": year[:20], "event": event[:300]})
    return rows


def _clean_news_items(value: Any) -> list[dict[str, str]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("news items must be a list")
    rows: list[dict[str, str]] = []
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        title = _clean_string(item.get("title")) or ""
        summary = _clean_string(item.get("summary")) or ""
        date = _clean_string(item.get("date")) or ""
        if title or summary:
            rows.append({"date": date[:20], "title": title[:160], "summary": summary[:400]})
    return rows


def extract_locale_overlay(site_copy: dict[str, Any], locale: str) -> dict[str, Any]:
    locales = site_copy.get("locales")
    if isinstance(locales, dict):
        overlay = locales.get(locale_key(locale)) or locales.get("zh-tw") or {}
        return overlay if isinstance(overlay, dict) else {}
    return {}


def public_site_copy_overlay(site_copy: dict[str, Any], locale: str) -> dict[str, Any]:
    """Legacy top-level keys plus locale overlay; strip control keys."""
    reserved = {"locales", "hiddenBlocks"}
    legacy = {key: value for key, value in site_copy.items() if key not in reserved}
    overlay = extract_locale_overlay(site_copy, locale)
    if not legacy:
        return overlay
    if not overlay:
        return legacy

    def merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in extra.items():
            current = merged.get(key)
            if isinstance(current, dict) and isinstance(value, dict):
                merged[key] = merge(current, value)
            else:
                merged[key] = value
        return merged

    return merge(legacy, overlay)


def read_hidden_blocks(site_copy: dict[str, Any]) -> dict[str, bool]:
    raw = site_copy.get("hiddenBlocks")
    if not isinstance(raw, dict):
        return {key: False for key in HIDDEN_BLOCK_KEYS}
    return {key: bool(raw.get(key)) for key in HIDDEN_BLOCK_KEYS}


def read_assets(manifest: dict[str, Any]) -> dict[str, str]:
    return {key: str(manifest.get(key) or "") for key in ASSET_KEYS}


def apply_copy_overlay(existing: dict[str, Any], locale: str, incoming: dict[str, Any]) -> dict[str, Any]:
    locales = existing.get("locales")
    if not isinstance(locales, dict):
        locales = {}
    current = locales.get(locale_key(locale))
    overlay = dict(current) if isinstance(current, dict) else {}

    for path in STRING_PATHS:
        if not _has_path(incoming, path):
            continue
        cleaned = _clean_string(_get_path(incoming, path))
        if cleaned is None:
            _delete_path(overlay, path)
        else:
            _set_path(overlay, path, cleaned)
    for path in STAT_PATHS:
        if not _has_path(incoming, path):
            continue
        cleaned_stats = _clean_stats(_get_path(incoming, path))
        if cleaned_stats is None:
            _delete_path(overlay, path)
        else:
            _set_path(overlay, path, cleaned_stats)
    if _has_path(incoming, STORY_PATH):
        paragraphs = _clean_paragraphs(_get_path(incoming, STORY_PATH))
        if paragraphs is None:
            _delete_path(overlay, STORY_PATH)
        else:
            _set_path(overlay, STORY_PATH, paragraphs)
    if _has_path(incoming, TIMELINE_PATH):
        timeline = _clean_timeline(_get_path(incoming, TIMELINE_PATH))
        if timeline is None:
            _delete_path(overlay, TIMELINE_PATH)
        else:
            _set_path(overlay, TIMELINE_PATH, timeline)
    if _has_path(incoming, NEWS_ITEMS_PATH):
        news_items = _clean_news_items(_get_path(incoming, NEWS_ITEMS_PATH))
        if news_items is None:
            _delete_path(overlay, NEWS_ITEMS_PATH)
        else:
            _set_path(overlay, NEWS_ITEMS_PATH, news_items)

    locales[locale_key(locale)] = overlay
    next_copy = dict(existing)
    next_copy["locales"] = locales
    return next_copy


def apply_hidden_blocks(existing: dict[str, Any], incoming: dict[str, Any] | None) -> dict[str, Any]:
    next_copy = dict(existing)
    if incoming is None:
        return next_copy
    next_copy["hiddenBlocks"] = {key: bool(incoming.get(key)) for key in HIDDEN_BLOCK_KEYS}
    return next_copy


def apply_assets(manifest: dict[str, Any], incoming: dict[str, Any] | None) -> dict[str, Any]:
    next_manifest = dict(manifest)
    if incoming is None:
        return next_manifest
    for key in ASSET_KEYS:
        if key not in incoming:
            continue
        value = _clean_string(incoming.get(key))
        if value:
            next_manifest[key] = value[:500]
        else:
            next_manifest.pop(key, None)
    return next_manifest


def serialize_overlay(overlay: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for path in STRING_PATHS:
        value = _get_path(overlay, path)
        if isinstance(value, str):
            _set_path(payload, path, value)
    for path in STAT_PATHS:
        value = _get_path(overlay, path)
        if isinstance(value, list):
            _set_path(payload, path, value)
    for path, reader in (
        (STORY_PATH, lambda item: item if isinstance(item, list) else None),
        (TIMELINE_PATH, lambda item: item if isinstance(item, list) else None),
        (NEWS_ITEMS_PATH, lambda item: item if isinstance(item, list) else None),
    ):
        value = reader(_get_path(overlay, path))
        if value is not None:
            _set_path(payload, path, value)
    return payload
