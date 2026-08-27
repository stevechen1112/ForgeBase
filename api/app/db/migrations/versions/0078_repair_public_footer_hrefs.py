"""Rewrite stale public footer hrefs stored on site profiles.

Revision ID: 0078_repair_public_footer_hrefs
Revises: 0077_tenant_content_maintenance
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0078_repair_public_footer_hrefs"
down_revision = "0077_tenant_content_maintenance"
branch_labels = None
depends_on = None

_LEGACY_HREFS = {
    "/technical-docs": "/docs",
    "/dealer-locator": "/dealers",
    "/cookie-policy": "/cookies",
    "/custom-solutions": "/oem-odm",
}

_JSON_COLUMNS = (
    "footer_sections_json",
    "header_nav_json",
    "header_actions_json",
)


def _rewrite_href(href: str) -> str:
    if not isinstance(href, str) or not href.startswith("/") or href.startswith("//"):
        return href
    path, sep, query = href.partition("?")
    if path == "/zh-TW" or path.startswith("/zh-TW/"):
        path = "/" if path == "/zh-TW" else path[len("/zh-TW") :]
    path = _LEGACY_HREFS.get(path, path)
    return f"{path}?{query}" if sep else path


def _rewrite_value(value):
    if isinstance(value, dict):
        rewritten = {key: _rewrite_value(item) for key, item in value.items()}
        href = rewritten.get("href")
        if isinstance(href, str):
            rewritten["href"] = _rewrite_href(href)
        return rewritten
    if isinstance(value, list):
        return [_rewrite_value(item) for item in value]
    return value


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, footer_sections_json, header_nav_json, header_actions_json, footer_cta_href FROM site_profiles"
        )
    ).mappings()
    for row in rows:
        updates = {}
        for column in _JSON_COLUMNS:
            raw = row[column]
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            rewritten = _rewrite_value(parsed)
            if rewritten == parsed:
                continue
            updates[column] = json.dumps(rewritten, ensure_ascii=False)
        cta_href = row["footer_cta_href"]
        if isinstance(cta_href, str) and cta_href:
            rewritten_cta = _rewrite_href(cta_href)
            if rewritten_cta != cta_href:
                updates["footer_cta_href"] = rewritten_cta
        if not updates:
            continue
        connection.execute(
            sa.text(
                "UPDATE site_profiles SET "
                + ", ".join(f"{column} = :{column}" for column in updates)
                + " WHERE id = :id"
            ),
            {"id": str(row["id"]), **updates},
        )


def downgrade() -> None:
    return
