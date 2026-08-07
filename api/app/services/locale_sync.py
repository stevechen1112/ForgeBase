"""
Locale auto-sync: when an English content row is saved, upsert zh-tw sibling.

- No approval UI: target follows source status and is written immediately.
- Manual field locks: fields previously edited on the target locale are skipped.
- Runs in-process via asyncio.create_task + get_session_ctx (same pattern as revalidate).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.core.locale import SOURCE_LOCALE, TARGET_LOCALES, is_source_locale, to_content_locale
from app.db.session import get_session_ctx
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.content_field_lock import ContentFieldLock
from app.models.cta import CTA
from app.models.faq_item import FAQItem
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.site_profile import SiteProfile
from app.models.tenant import Tenant
from app.services.subscription import get_plan_feature
from app.services.translator import (
    TRANSLATABLE_FIELDS,
    TranslationError,
    load_glossary,
    translate_fields,
    translate_specifications,
)

logger = logging.getLogger(__name__)


def _as_naive(value: Any) -> Any:
    """TIMESTAMP WITHOUT TIME ZONE columns reject aware datetimes."""
    from datetime import datetime, timezone
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# entity_type → (Model, identity_attr, copy_attrs)
# identity_attr is shared across locales (slug / variant_key / cta_key)
ENTITY_REGISTRY: dict[str, tuple[type, str, tuple[str, ...]]] = {    "product": (
        Product,
        "slug",
        (
            "slug", "model_number", "category_id", "image_url", "og_image_url",
            "is_featured", "display_priority", "specifications",
        ),
    ),
    "category": (
        ProductCategory,
        "slug",
        ("slug", "image_url", "og_image_url", "parent_id", "sort_order"),
    ),
    "application": (
        Application,
        "slug",
        ("slug", "hero_image_url", "og_image_url", "sort_order"),
    ),
    "faq": (FAQItem, "variant_key", ("variant_key", "category_tag", "sort_order")),
    "certification": (
        Certification,
        "slug",
        ("slug", "issuer", "cert_number", "issued_at", "expires_at", "badge_image_url", "document_url"),
    ),
    "capability": (
        Capability,
        "slug",
        ("slug", "icon_url", "image_url", "metrics", "category_tag", "sort_order"),
    ),
    "comparison": (
        ComparisonTopic,
        "slug",
        ("slug", "dimensions", "sort_order"),
    ),
    "page": (
        Page,
        "slug",
        (
            "slug", "page_type", "hero_image_url", "og_image_url", "canonical_url",
            "structured_data", "noindex", "entity_type", "entity_id", "brief_id",
        ),
    ),
    "cta": (
        CTA,
        "cta_key",
        (
            "cta_key", "cta_type", "button_action", "button_url", "bg_color",
            "image_url", "target_intent_stage", "sort_order",
        ),
    ),
}


# entity_type → (fk_attr, ref_entity_type or None = read from source.entity_type)
# Cross-locale FK: an EN row's category_id/parent_id/entity_id points at the EN
# counterpart; the target-locale row must point at the target-locale counterpart
# (matched by the registry identity attr) or the link breaks on the public site.
_FK_REMAP: dict[str, tuple[str, Optional[str]]] = {
    "product": ("category_id", "category"),
    "category": ("parent_id", "category"),
    "page": ("entity_id", None),
}


async def _resolve_cross_locale_fk(
    session: AsyncSession,
    *,
    ref_entity_type: Optional[str],
    ref_id: Any,
    target_locale: str,
    tenant_id: Optional[uuid.UUID],
) -> Any:
    """Map a source-locale FK to the target-locale row with the same identity."""
    if not ref_id or not ref_entity_type or ref_entity_type not in ENTITY_REGISTRY:
        return None
    RefModel, ref_identity, _ = ENTITY_REGISTRY[ref_entity_type]
    ref_source = await session.get(RefModel, ref_id)
    if ref_source is None:
        return None
    if to_content_locale(getattr(ref_source, "locale", None)) == target_locale:
        return ref_id  # already points at a target-locale row
    identity_val = getattr(ref_source, ref_identity, None)
    if not identity_val:
        return None
    q = select(RefModel).where(
        getattr(RefModel, ref_identity) == identity_val,
        RefModel.locale == target_locale,
    )
    if hasattr(RefModel, "tenant_id"):
        if tenant_id is not None:
            q = q.where((RefModel.tenant_id == tenant_id) | (RefModel.tenant_id.is_(None)))
        else:
            q = q.where(RefModel.tenant_id.is_(None))
    ref_target = (await session.exec(q)).first()
    return ref_target.id if ref_target else None


_background_tasks: set[asyncio.Task] = set()


def schedule_locale_sync(entity_type: str, source_id: uuid.UUID) -> None:
    """Fire-and-forget from request handlers after successful commit.

    Keep a strong reference to the task: the event loop only holds weak refs,
    so an unreferenced task may be garbage-collected before it finishes.
    """
    try:
        task = asyncio.create_task(_run_sync_safe(entity_type, source_id))
    except RuntimeError:
        logger.warning("No running event loop; skipped locale sync for %s %s", entity_type, source_id)
        return
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _run_sync_safe(entity_type: str, source_id: uuid.UUID) -> None:
    try:
        async with get_session_ctx() as session:
            await sync_source_to_targets(session, entity_type, source_id)
    except Exception:
        logger.exception("locale sync failed for %s %s", entity_type, source_id)


async def sync_source_to_targets(
    session: AsyncSession,
    entity_type: str,
    source_id: uuid.UUID,
) -> None:
    if entity_type not in ENTITY_REGISTRY:
        return
    Model, identity_attr, copy_attrs = ENTITY_REGISTRY[entity_type]
    source = await session.get(Model, source_id)
    if not source:
        return
    if not is_source_locale(getattr(source, "locale", None)):
        return

    tenant_id = getattr(source, "tenant_id", None)
    if tenant_id:
        tenant = await session.get(Tenant, tenant_id)
        plan = tenant.plan if tenant else "starter"
        if not get_plan_feature(plan, "multilingual"):
            logger.info("Skip locale sync (no multilingual feature) tenant=%s", tenant_id)
            return

    glossary: list[dict[str, str]] = []
    if tenant_id:
        profile = (
            await session.exec(select(SiteProfile).where(SiteProfile.tenant_id == tenant_id))
        ).first()
        if profile:
            glossary = load_glossary(profile.translation_glossary_json)

    for target_locale in TARGET_LOCALES:
        await _upsert_target(
            session,
            entity_type=entity_type,
            Model=Model,
            identity_attr=identity_attr,
            copy_attrs=copy_attrs,
            source=source,
            target_locale=target_locale,
            glossary=glossary,
        )
    await session.commit()

    # Target-locale ISR caches must refresh too — otherwise zh-tw pages keep
    # serving stale content even though the DB row was synced (存英文即上線).
    if entity_type == "page" and getattr(source, "status", None) == "published":
        from app.services.revalidate import revalidate_page

        route_locales = {"zh-tw": "zh-TW"}  # content locale → next-intl route tag
        for target_locale in TARGET_LOCALES:
            try:
                await revalidate_page(
                    source.slug, route_locales.get(target_locale, target_locale),
                    include_sitemap=True,
                )
            except Exception:
                logger.warning("revalidate after sync failed: %s %s", source.slug, target_locale)


async def _upsert_target(
    session: AsyncSession,
    *,
    entity_type: str,
    Model: type,
    identity_attr: str,
    copy_attrs: tuple[str, ...],
    source: Any,
    target_locale: str,
    glossary: list[dict[str, str]],
) -> None:
    identity_val = getattr(source, identity_attr, None)
    if not identity_val:
        logger.warning("Skip sync %s %s: missing identity %s", entity_type, source.id, identity_attr)
        return

    q = select(Model).where(getattr(Model, identity_attr) == identity_val)
    q = q.where(Model.locale == target_locale)
    tenant_id = getattr(source, "tenant_id", None)
    if tenant_id is not None and hasattr(Model, "tenant_id"):
        q = q.where(Model.tenant_id == tenant_id)
    elif hasattr(Model, "tenant_id"):
        q = q.where(Model.tenant_id.is_(None))
    target = (await session.exec(q)).first()

    # Collect source text fields
    field_names = TRANSLATABLE_FIELDS.get(entity_type, [])
    source_fields = {
        f: getattr(source, f)
        for f in field_names
        if isinstance(getattr(source, f, None), str) and str(getattr(source, f)).strip()
    }

    locked: set[str] = set()
    if target:
        locked = await get_locked_fields(session, entity_type, target.id)

    to_translate = {k: v for k, v in source_fields.items() if k not in locked}
    translated: dict[str, Any] = {}
    if to_translate:
        try:
            translated = await translate_fields(entity_type, to_translate, target_locale, glossary)
        except TranslationError as e:
            # Degrade to a partial sync: copy/status still update so the target
            # row never stalls behind a transient LLM failure. Text fields fall
            # back to source (English) on create / stay unchanged on update.
            logger.error("LLM translate failed %s→%s %s: %s", entity_type, target_locale, source.id, e)

    # Cross-locale FK remap (category_id / parent_id / entity_id)
    fk_overrides: dict[str, Any] = {}
    if entity_type in _FK_REMAP:
        fk_attr, ref_type = _FK_REMAP[entity_type]
        ref_id = getattr(source, fk_attr, None)
        if ref_type is None:
            ref_type = getattr(source, "entity_type", None)
        if ref_id and ref_type:
            resolved = await _resolve_cross_locale_fk(
                session,
                ref_entity_type=ref_type,
                ref_id=ref_id,
                target_locale=target_locale,
                tenant_id=tenant_id,
            )
            if resolved is None:
                logger.warning(
                    "locale sync %s %s: no %s counterpart for %s=%s in %s; cleared",
                    entity_type, source.id, ref_type, fk_attr, ref_id, target_locale,
                )
            fk_overrides[fk_attr] = resolved

    # Product specs: only when not locked
    if entity_type == "product" and "specifications" not in locked and getattr(source, "specifications", None):
        try:
            translated_specs = await translate_specifications(
                source.specifications, target_locale, glossary
            )
            translated["_specifications"] = translated_specs
        except TranslationError as e:
            logger.warning("Spec translate failed for product %s: %s", source.id, e)

    now = utcnow_naive()
    if target is None:
        data: dict[str, Any] = {
            "locale": target_locale,
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        }
        for attr in copy_attrs:
            if hasattr(source, attr):
                data[attr] = _as_naive(getattr(source, attr))
        for f in field_names:
            if f in translated:
                data[f] = translated[f]
            elif f not in locked:
                data[f] = getattr(source, f, None)
        if "_specifications" in translated:
            data["specifications"] = translated["_specifications"]
        data.update(fk_overrides)
        if hasattr(Model, "status"):
            data["status"] = getattr(source, "status", "draft")
        if hasattr(Model, "published_at"):
            pub = getattr(source, "published_at", None) if data.get("status") == "published" else None
            data["published_at"] = _as_naive(pub)
        # Required non-null fallbacks for models that need name-like fields
        for f in field_names:
            if f not in data or data[f] is None:
                data[f] = getattr(source, f, "") or ""
        target = Model(**data)
        session.add(target)
        await session.flush()
        logger.info("locale sync created %s %s locale=%s", entity_type, target.id, target_locale)
    else:
        for attr in copy_attrs:
            if attr == "specifications":
                continue  # handled via translate / lock
            if hasattr(source, attr) and hasattr(target, attr):
                setattr(target, attr, _as_naive(getattr(source, attr)))
        for f, val in translated.items():
            if f.startswith("_"):
                continue
            setattr(target, f, val)
        if "_specifications" in translated:
            target.specifications = translated["_specifications"]
        elif entity_type == "product" and "specifications" not in locked:
            target.specifications = getattr(source, "specifications", None)
        if hasattr(target, "status") and hasattr(source, "status"):
            target.status = source.status
        if hasattr(target, "published_at") and hasattr(source, "published_at"):
            if getattr(source, "status", None) == "published":
                target.published_at = _as_naive(source.published_at or now)
            else:
                target.published_at = None
        target.updated_at = now
        for k, v in fk_overrides.items():
            if hasattr(target, k):
                setattr(target, k, v)
        # Prefer binding legacy NULL-tenant targets to the source tenant when known
        if getattr(target, "tenant_id", None) is None and tenant_id is not None:
            target.tenant_id = tenant_id
        session.add(target)
        logger.info("locale sync updated %s %s locale=%s skipped=%s", entity_type, target.id, target_locale, sorted(locked))


async def get_locked_fields(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
) -> set[str]:
    rows = (
        await session.exec(
            select(ContentFieldLock.field_name).where(
                ContentFieldLock.entity_type == entity_type,
                ContentFieldLock.entity_id == entity_id,
            )
        )
    ).all()
    return set(rows)


async def lock_changed_fields(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
    changed_fields: list[str],
) -> None:
    """Record manual edits on a non-source locale so future sync skips them."""
    allowed = set(TRANSLATABLE_FIELDS.get(entity_type, []))
    if entity_type == "product":
        allowed.add("specifications")
    for name in changed_fields:
        if name not in allowed:
            continue
        existing = (
            await session.exec(
                select(ContentFieldLock).where(
                    ContentFieldLock.entity_type == entity_type,
                    ContentFieldLock.entity_id == entity_id,
                    ContentFieldLock.field_name == name,
                )
            )
        ).first()
        if existing:
            continue
        session.add(
            ContentFieldLock(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=name,
            )
        )


def normalize_payload_locale(dump: dict[str, Any]) -> dict[str, Any]:
    if "locale" in dump and dump["locale"] is not None:
        dump["locale"] = to_content_locale(str(dump["locale"]))
    return dump


def detect_changed_translatable_fields(
    entity_type: str,
    before: Any,
    updates: dict[str, Any],
) -> list[str]:
    allowed = set(TRANSLATABLE_FIELDS.get(entity_type, []))
    if entity_type == "product":
        allowed.add("specifications")
    changed: list[str] = []
    for key, new_val in updates.items():
        if key not in allowed:
            continue
        old_val = getattr(before, key, None)
        if old_val != new_val:
            changed.append(key)
    return changed
