"""Draft a buyer-locale content row from the tenant source locale.

Never publishes. Never overwrites a published target row.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.locale import (
    SUPPORTED_CONTENT_LOCALES,
    content_locale_label,
    to_content_locale,
)
from app.core.tracing import (
    WorkflowType,
    attach_trace_metadata,
    chat_completion_kwargs,
    get_openai_client,
    observe_workflow,
)
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.content_field_lock import ContentFieldLock
from app.models.faq_item import FAQItem
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.site_profile import SiteProfile
from app.services.locale_support import (
    default_buyer_locale,
    get_source_locale,
    is_live_status,
)

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class EntitySpec:
    model: type
    key_field: str
    copy_fields: tuple[str, ...]
    translate_fields: tuple[str, ...]
    required_publish_fields: tuple[str, ...]
    remap_fk: tuple[tuple[str, type, str], ...] = ()
    field_limits: dict[str, int] | None = None


SPECS: dict[str, EntitySpec] = {
    "products": EntitySpec(
        model=Product,
        key_field="slug",
        copy_fields=("model_number", "specifications", "image_url", "og_image_url", "is_featured", "display_priority", "category_id"),
        translate_fields=("product_name", "short_description", "full_description", "seo_title", "seo_description", "image_alt"),
        required_publish_fields=("product_name", "short_description"),
        remap_fk=(("category_id", ProductCategory, "slug"),),
        field_limits={"product_name": 100, "short_description": 200, "seo_title": 70, "seo_description": 160, "image_alt": 200},
    ),
    "categories": EntitySpec(
        model=ProductCategory,
        key_field="slug",
        copy_fields=("image_url", "og_image_url", "sort_order", "parent_id"),
        translate_fields=("category_name", "description", "seo_title", "seo_description"),
        required_publish_fields=("category_name",),
        remap_fk=(("parent_id", ProductCategory, "slug"),),
        field_limits={"category_name": 60, "seo_title": 70, "seo_description": 160},
    ),
    "pages": EntitySpec(
        model=Page,
        key_field="slug",
        copy_fields=("page_type", "hero_image_url", "og_image_url", "canonical_url", "structured_data", "entity_type", "entity_id"),
        translate_fields=("title", "subtitle", "body", "seo_title", "seo_description"),
        required_publish_fields=("title",),
        field_limits={"title": 120, "subtitle": 240, "seo_title": 70, "seo_description": 160},
    ),
    "applications": EntitySpec(
        model=Application,
        key_field="slug",
        copy_fields=("hero_image_url", "og_image_url", "sort_order"),
        translate_fields=("application_name", "industry", "description", "challenge", "solution", "seo_title", "seo_description"),
        required_publish_fields=("application_name", "industry"),
        field_limits={"application_name": 100, "industry": 60, "seo_title": 70, "seo_description": 160},
    ),
    "faqs": EntitySpec(
        model=FAQItem,
        key_field="variant_key",
        copy_fields=("variant_key", "category_tag", "sort_order"),
        translate_fields=("question", "answer"),
        required_publish_fields=("question", "answer"),
        field_limits={"question": 300},
    ),
    "certifications": EntitySpec(
        model=Certification,
        key_field="slug",
        copy_fields=("cert_number", "issued_at", "expires_at", "badge_image_url", "document_url"),
        translate_fields=("cert_name", "issuer", "description"),
        required_publish_fields=("cert_name",),
        field_limits={"cert_name": 100, "issuer": 120},
    ),
    "capabilities": EntitySpec(
        model=Capability,
        key_field="slug",
        copy_fields=("icon_url", "image_url", "metrics", "category_tag", "sort_order"),
        translate_fields=("capability_name", "short_description", "detail"),
        required_publish_fields=("capability_name", "short_description"),
        field_limits={"capability_name": 100, "short_description": 200},
    ),
    "comparisons": EntitySpec(
        model=ComparisonTopic,
        key_field="slug",
        copy_fields=("dimensions", "sort_order"),
        translate_fields=("topic_title", "summary", "conclusion", "seo_title", "seo_description"),
        required_publish_fields=("topic_title",),
        field_limits={"topic_title": 120, "summary": 500, "seo_title": 70, "seo_description": 160},
    ),
}

def _clip(value: Any, limit: int | None) -> Any:
    if limit is None or not isinstance(value, str):
        return value
    return value[:limit]


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = _FENCE_RE.sub("", (raw or "").strip())
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="翻譯服務回傳無法解析的內容，請稍後再試。") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=503, detail="翻譯服務回傳格式不正確。")
    return payload


async def _load_glossary(session: AsyncSession, tenant_id: uuid.UUID | None) -> list[dict[str, str]]:
    stmt = select(SiteProfile)
    if tenant_id:
        stmt = stmt.where(SiteProfile.tenant_id == tenant_id)
    else:
        stmt = stmt.where(SiteProfile.tenant_id.is_(None))
    profile = (await session.exec(stmt.limit(1))).first()
    raw = getattr(profile, "translation_glossary_json", None) if profile else None
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    rows: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if source and target:
            rows.append({"source": source, "target": target, "note": str(item.get("note") or "")})
    return rows[:80]


async def _remap_fk(
    session: AsyncSession,
    spec: EntitySpec,
    source: Any,
    tenant_id: uuid.UUID | None,
    target_locale: str,
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for field_name, Related, related_key in spec.remap_fk:
        related_id = getattr(source, field_name, None)
        if not related_id:
            continue
        related = await session.get(Related, related_id)
        if related is None:
            continue
        key_value = getattr(related, related_key, None)
        if not key_value:
            continue
        q = select(Related).where(getattr(Related, related_key) == key_value, Related.locale == target_locale)
        if tenant_id is not None and hasattr(Related, "tenant_id"):
            q = q.where(Related.tenant_id == tenant_id)
        mapped = (await session.exec(q.limit(1))).first()
        if mapped is not None:
            updates[field_name] = mapped.id
    return updates


async def _locked_fields(session: AsyncSession, entity: str, entity_id: uuid.UUID) -> set[str]:
    rows = (
        await session.exec(
            select(ContentFieldLock).where(
                ContentFieldLock.entity_type == entity,
                ContentFieldLock.entity_id == entity_id,
            )
        )
    ).all()
    return {row.field_name for row in rows}


@observe_workflow(name=WorkflowType.TRANSLATE)
async def _draft_fields(
    *,
    fields: dict[str, Any],
    source_locale: str,
    target_locale: str,
    glossary: list[dict[str, str]],
    tenant_id: uuid.UUID | None,
) -> dict[str, Any]:
    attach_trace_metadata(
        workflow=WorkflowType.TRANSLATE,
        tenant_id=str(tenant_id) if tenant_id else "none",
        extra={"source_locale": source_locale, "target_locale": target_locale},
    )
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="尚未設定翻譯服務，請稍後再試或改為人工填寫。")

    glossary_lines = "\n".join(
        f"- {row['source']} → {row['target']}" + (f" ({row['note']})" if row["note"] else "")
        for row in glossary
    ) or "(none)"
    payload = {key: (value[:8000] if isinstance(value, str) else value) for key, value in fields.items() if value not in (None, "")}
    if not payload:
        return {}

    source_label = content_locale_label(source_locale) or source_locale
    target_label = content_locale_label(target_locale) or target_locale
    system = (
        "You draft buyer-language website copy for an export manufacturer. "
        "Return a JSON object with the SAME keys you were given. "
        "Translate prose into the target language. "
        "Do not invent specifications, prices, lead times, certifications, or legal claims. "
        "Keep model numbers, SKUs, numeric values, units, URLs, and HTML/JSON structure unchanged. "
        "Honor the glossary exactly. "
        "If a value is already in the target language, keep it."
    )
    user = (
        f"Source language: {source_label} ({source_locale})\n"
        f"Target language: {target_label} ({target_locale})\n"
        f"Glossary:\n{glossary_lines}\n\n"
        f"Fields:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            **chat_completion_kwargs(temperature=0.2, max_output_tokens=2500),
        )
        content = response.choices[0].message.content or ""
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("locale draft translation failed")
        raise HTTPException(status_code=503, detail="翻譯服務暫時無法使用，請稍後再試。") from exc
    drafted = _parse_json_object(content)
    return {key: drafted[key] for key in payload if key in drafted and drafted[key] not in (None, "")}


async def create_locale_draft(
    session: AsyncSession,
    *,
    entity: str,
    source_id: uuid.UUID,
    tenant_id: uuid.UUID,
    target_locale: str | None = None,
) -> dict[str, Any]:
    spec = SPECS.get(entity)
    if spec is None:
        raise HTTPException(status_code=404, detail="不支援此內容類型的語系草稿")

    source = await session.get(spec.model, source_id)
    if source is None or getattr(source, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=404, detail="Content not found")

    source_locale = await get_source_locale(session, tenant_id)
    item_locale = to_content_locale(getattr(source, "locale", None))
    if item_locale != source_locale:
        raise HTTPException(
            status_code=422,
            detail="請從來源語系的內容產草稿。目前這筆不是來源語系。",
        )

    target = to_content_locale(target_locale or default_buyer_locale(source_locale), default="")
    if target not in SUPPORTED_CONTENT_LOCALES or target == source_locale:
        raise HTTPException(status_code=422, detail="目標語系必須是支援的買方內容語系")

    key_value = getattr(source, spec.key_field)
    existing_q = select(spec.model).where(
        getattr(spec.model, spec.key_field) == key_value,
        spec.model.locale == target,
        spec.model.tenant_id == tenant_id,
    )
    existing = (await session.exec(existing_q.limit(1))).first()
    if existing is not None and is_live_status(getattr(existing, "status", None)):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "target_published",
                "message": "買方語系已上架，系統不會用新草稿覆蓋。請開啟該語系頁面修改後再上架。",
                "target_id": str(existing.id),
            },
        )

    translate_input = {field: getattr(source, field, None) for field in spec.translate_fields}
    glossary = await _load_glossary(session, tenant_id)
    drafted = await _draft_fields(
        fields=translate_input,
        source_locale=source_locale,
        target_locale=target,
        glossary=glossary,
        tenant_id=tenant_id,
    )
    limits = spec.field_limits or {}
    for field in spec.required_publish_fields:
        if not str(drafted.get(field) or "").strip():
            raise HTTPException(status_code=503, detail="翻譯結果缺少必要欄位，請稍後再試。")

    locked: set[str] = set()
    if existing is not None:
        locked = await _locked_fields(session, entity, existing.id)

    fk_updates = await _remap_fk(session, spec, source, tenant_id, target)
    now = utcnow_naive()
    values: dict[str, Any] = {}
    for field in spec.copy_fields:
        values[field] = fk_updates.get(field, getattr(source, field, None))
    for field in spec.translate_fields:
        if field in locked:
            continue
        if field in drafted:
            values[field] = _clip(drafted[field], limits.get(field))
    values[spec.key_field] = key_value
    values["locale"] = target
    values["status"] = "draft"
    values["tenant_id"] = tenant_id
    if hasattr(spec.model, "slug") and spec.key_field != "slug" and getattr(source, "slug", None):
        values.setdefault("slug", source.slug)

    if existing is None:
        row = spec.model(**values)
        row.id = uuid.uuid4()
        if hasattr(row, "created_at"):
            row.created_at = now
        action = "created"
    else:
        row = existing
        for field, value in values.items():
            setattr(row, field, value)
        action = "updated_draft"

    if hasattr(row, "published_at"):
        row.published_at = None
    if hasattr(row, "noindex"):
        row.noindex = True
    if hasattr(row, "updated_at"):
        row.updated_at = now

    session.add(row)
    await session.commit()
    await session.refresh(row)
    return {
        "action": action,
        "entity": entity,
        "source_id": str(source.id),
        "target_id": str(row.id),
        "source_locale": source_locale,
        "target_locale": target,
        "status": getattr(row, "status", "draft"),
    }
