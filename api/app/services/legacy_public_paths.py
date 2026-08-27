"""Rewrite stale public marketing hrefs stored on site profiles."""

from __future__ import annotations

from typing import Any

LEGACY_PUBLIC_PATHS = {
    "/technical-docs": "/docs",
    "/dealer-locator": "/dealers",
    "/cookie-policy": "/cookies",
    "/custom-solutions": "/oem-odm",
}


def rewrite_legacy_public_path(href: str) -> str:
    if not isinstance(href, str) or not href.startswith("/") or href.startswith("//"):
        return href
    path, sep, query = href.partition("?")
    if path == "/zh-TW" or path.startswith("/zh-TW/"):
        path = "/" if path == "/zh-TW" else path[len("/zh-TW") :]
    path = LEGACY_PUBLIC_PATHS.get(path, path)
    return f"{path}?{query}" if sep else path


def rewrite_legacy_public_hrefs(value: Any) -> Any:
    if isinstance(value, dict):
        rewritten = {key: rewrite_legacy_public_hrefs(item) for key, item in value.items()}
        href = rewritten.get("href")
        if isinstance(href, str):
            rewritten["href"] = rewrite_legacy_public_path(href)
        return rewritten
    if isinstance(value, list):
        return [rewrite_legacy_public_hrefs(item) for item in value]
    return value
