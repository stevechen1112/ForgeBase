"""Content-locale normalization for CMS rows and public queries."""

from __future__ import annotations

SOURCE_LOCALE = "en"
TARGET_LOCALES = ("zh-tw",)
SUPPORTED_CONTENT_LOCALES = (SOURCE_LOCALE, *TARGET_LOCALES)

# Public next-intl route locale → content DB locale
_ROUTE_TO_CONTENT = {
    "en": "en",
    "zh-tw": "zh-tw",
    "zh-TW": "zh-tw",
    "zh_tw": "zh-tw",
    "zh_TW": "zh-tw",
}


def to_content_locale(raw: str | None, default: str = SOURCE_LOCALE) -> str:
    """Normalize any locale tag to the CMS canonical form (e.g. zh-TW → zh-tw)."""
    if not raw:
        return default
    key = raw.strip()
    if key in _ROUTE_TO_CONTENT:
        return _ROUTE_TO_CONTENT[key]
    lowered = key.lower().replace("_", "-")
    if lowered in _ROUTE_TO_CONTENT:
        return _ROUTE_TO_CONTENT[lowered]
    if lowered == "zh-tw":
        return "zh-tw"
    if lowered == "en":
        return "en"
    return default


def is_source_locale(raw: str | None) -> bool:
    return to_content_locale(raw) == SOURCE_LOCALE
