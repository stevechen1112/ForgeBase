"""Non-rendering inbound content and attachment sanitization."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import PurePath
from typing import Any

from app.core.config import settings

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACE = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n{3,}")
_DANGEROUS_EXTENSIONS = {
    ".app",
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".hta",
    ".js",
    ".jse",
    ".msi",
    ".ps1",
    ".scr",
    ".vbs",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"br", "p", "div", "li", "tr", "blockquote"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"p", "div", "li", "tr", "blockquote"}:
            self.parts.append("\n")


def clean_text(value: str, *, limit: int) -> str:
    text = html.unescape(_CONTROL.sub("", str(value or ""))).replace("\r\n", "\n")
    text = "\n".join(_SPACE.sub(" ", line).strip() for line in text.splitlines())
    return _BLANKS.sub("\n\n", text).strip()[:limit]


def body_to_safe_text(text_body: str | None, html_body: str | None) -> str:
    if text_body:
        return clean_text(text_body, limit=settings.INBOUND_REPLY_MAX_BODY_CHARS)
    parser = _TextExtractor()
    try:
        parser.feed(str(html_body or "")[: settings.INBOUND_REPLY_MAX_FETCH_BYTES])
    except (ValueError, AssertionError):
        return ""
    return clean_text(
        "".join(parser.parts), limit=settings.INBOUND_REPLY_MAX_BODY_CHARS
    )


def safe_attachment_metadata(values: Any) -> tuple[list[dict[str, Any]], int, bool]:
    rows = values if isinstance(values, list) else []
    safe: list[dict[str, Any]] = []
    total_bytes = 0
    risky = len(rows) > settings.INBOUND_REPLY_MAX_ATTACHMENTS
    for item in rows[: settings.INBOUND_REPLY_MAX_ATTACHMENTS]:
        if not isinstance(item, dict):
            risky = True
            continue
        filename = clean_text(
            PurePath(str(item.get("filename") or "attachment")).name, limit=255
        )
        content_type = clean_text(
            str(item.get("content_type") or "application/octet-stream"), limit=120
        ).lower()
        try:
            size = max(0, int(item.get("size") or 0))
        except (TypeError, ValueError):
            size = 0
            risky = True
        total_bytes += size
        extension = PurePath(filename.lower()).suffix
        dangerous = extension in _DANGEROUS_EXTENSIONS or content_type in {
            "application/x-msdownload",
            "application/x-sh",
            "application/x-dosexec",
        }
        risky = risky or dangerous
        safe.append(
            {
                "provider_attachment_id": str(item.get("id") or "")[:120],
                "filename": filename,
                "content_type": content_type,
                "size": size,
                "dangerous": dangerous,
                "retrieved": False,
            }
        )
    if total_bytes > settings.INBOUND_REPLY_MAX_ATTACHMENT_BYTES:
        risky = True
    return safe, total_bytes, bool(rows) or risky
