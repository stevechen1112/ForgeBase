"""Tenant source locale, buyer-locale pairing, and stale / publish guards."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.locale import SUPPORTED_CONTENT_LOCALES, to_content_locale
from app.models.site_profile import SiteProfile

_CJK_RE = re.compile(r"[\u3400-\u9fff]")


def profile_to_content_locale(raw: str | None) -> str:
    """Site profile stores en / zh-TW; CMS rows use en / zh-tw."""
    return to_content_locale(raw, default="zh-tw")


async def get_source_locale(session: AsyncSession, tenant_id: UUID | None) -> str:
    stmt = select(SiteProfile)
    if tenant_id:
        stmt = stmt.where(SiteProfile.tenant_id == tenant_id)
    else:
        stmt = stmt.where(SiteProfile.tenant_id.is_(None))
    profile = (await session.exec(stmt.limit(1))).first()
    if profile is None:
        return "zh-tw"
    return profile_to_content_locale(profile.default_locale)


def buyer_locales(source_locale: str) -> tuple[str, ...]:
    source = to_content_locale(source_locale, default="zh-tw")
    return tuple(locale for locale in SUPPORTED_CONTENT_LOCALES if locale != source)


def default_buyer_locale(source_locale: str) -> str:
    buyers = buyer_locales(source_locale)
    return buyers[0] if buyers else "en"


def is_live_status(status: str | None) -> bool:
    return (status or "") in {"published", "active"}


def is_stale(source: Any, target: Any) -> bool:
    """Published buyer-locale row is stale after a later source publish."""
    if source is None or target is None:
        return False
    if not is_live_status(getattr(target, "status", None)):
        return False
    if not is_live_status(getattr(source, "status", None)):
        return False
    source_published = getattr(source, "published_at", None) or getattr(source, "updated_at", None)
    target_updated = getattr(target, "updated_at", None) or getattr(target, "published_at", None)
    if not isinstance(source_published, datetime) or not isinstance(target_updated, datetime):
        return False
    return source_published > target_updated


def contains_cjk(value: str | None) -> bool:
    return bool(value and _CJK_RE.search(value))


def apply_pair_status_filter(
    query: Any,
    Model: type,
    *,
    tenant_id: UUID | None,
    source_locale: str,
    target_locale: str,
    pair_status: str,
    key_field: str,
):
    """Filter list queries to missing / draft / stale buyer-locale variants."""
    if pair_status not in {"missing_target", "draft_target", "stale"}:
        return query
    Target = aliased(Model)
    source_key = getattr(Model, key_field)
    target_key = getattr(Target, key_field)
    tenant_match = True
    if tenant_id is not None and hasattr(Model, "tenant_id"):
        tenant_match = Target.tenant_id == Model.tenant_id

    pair_exists = (
        select(Target.id)
        .where(tenant_match, target_key == source_key, Target.locale == target_locale)
        .exists()
    )

    if pair_status == "missing_target":
        return query.where(Model.locale == source_locale).where(~pair_exists)

    if pair_status == "draft_target":
        return query.where(Model.locale == target_locale, Model.status == "draft")

    # stale: buyer-locale live rows whose source was published later
    Source = aliased(Model)
    source_key_on_source = getattr(Source, key_field)
    source_row = Source.locale == source_locale
    if tenant_id is not None and hasattr(Model, "tenant_id"):
        source_row = source_row & (Source.tenant_id == Model.tenant_id)
    source_published = Source.updated_at
    target_updated = Model.updated_at
    live_target = Model.status.in_(("published", "active"))
    live_source = Source.status.in_(("published", "active"))
    return query.where(Model.locale == target_locale, live_target).where(
        select(Source.id)
        .where(
            source_row,
            source_key_on_source == getattr(Model, key_field),
            live_source,
            source_published > target_updated,
        )
        .exists()
    )
