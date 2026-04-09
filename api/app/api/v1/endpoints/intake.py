"""
Legacy Site Intake API — endpoints for managing intake projects,
reviewing candidates, and committing results into ForgeBase.

Routes (all require auth):
  POST   /intake/projects                           — create a new intake project
  GET    /intake/projects                           — list all projects
  GET    /intake/projects/{id}                      — get project detail + summary
  PATCH  /intake/projects/{id}                      — update project metadata
  POST   /intake/projects/{id}/discover             — trigger site discovery (Phase 1)
  POST   /intake/projects/{id}/extract              — trigger content extraction (Phase 2)
  GET    /intake/projects/{id}/urls                 — list URL candidates
  PATCH  /intake/urls/{id}/review                   — review a URL candidate
  GET    /intake/projects/{id}/entities             — list entity candidates
  PATCH  /intake/entities/{id}/review               — review an entity candidate
  GET    /intake/projects/{id}/redirects            — list redirect candidates
  PATCH  /intake/redirects/{id}/review              — review a redirect candidate
  GET    /intake/projects/{id}/briefs               — list brief candidates
  PATCH  /intake/briefs/{id}/review                 — review a brief candidate
  POST   /intake/projects/{id}/commit               — commit accepted items to ForgeBase
"""
from __future__ import annotations

from datetime import datetime
import json
import re
import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session, get_session_ctx
from app.models.intake import (
    IntakeBriefCandidate,
    IntakeEntityCandidate,
    IntakeProject,
    IntakeRedirectCandidate,
    IntakeUrlCandidate,
)
from app.models.user import User
from app.schemas.intake import (
    IntakeBriefCandidateRead,
    IntakeBriefReview,
    IntakeEntityCandidateRead,
    IntakeEntityReview,
    IntakeProjectCreate,
    IntakeProjectRead,
    IntakeProjectSummary,
    IntakeProjectUpdate,
    IntakeRedirectCandidateRead,
    IntakeRedirectReview,
    IntakeUrlCandidateRead,
    IntakeUrlReview,
)
from app.core.datetime import utcnow_naive

router = APIRouter(prefix="/intake", tags=["Legacy Site Intake"])


def _normalize_content_locale(locale: str | None) -> str:
    if not locale:
        return "en"

    normalized = locale.replace("_", "-").strip()
    lowered = normalized.lower()
    if lowered == "zh-tw":
        return "zh-TW"
    if lowered.startswith("en"):
        return "en"
    return normalized


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None


def _truncate_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:max_length]


def _lookup_key(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text or value.strip().lower()


def _slug_candidate(value: str | None, fallback: str, max_length: int) -> str:
    base = _lookup_key(value or fallback)
    if not base:
        base = _lookup_key(fallback)
    if not base:
        base = f"item-{uuid.uuid4().hex[:8]}"
    return base[:max_length].strip("-") or f"item-{uuid.uuid4().hex[:8]}"


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
        return [part.strip() for part in text.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return json.dumps(value, ensure_ascii=False)


def _parse_datetime_value(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    normalized = text.replace("/", "-")
    for candidate in (normalized, f"{normalized}T00:00:00"):
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _apply_published_state(obj: Any) -> None:
    if hasattr(obj, "status"):
        obj.status = "published"
    if hasattr(obj, "published_at") and getattr(obj, "published_at", None) is None:
        obj.published_at = utcnow_naive()
    if hasattr(obj, "updated_at"):
        obj.updated_at = utcnow_naive()


async def _ensure_unique_slug(
    db: AsyncSession,
    Model: Any,
    base_slug: str,
    *,
    locale: str | None,
    max_length: int,
    global_unique: bool,
) -> str:
    candidate = base_slug[:max_length].strip("-") or f"item-{uuid.uuid4().hex[:8]}"
    suffix = 2

    while True:
        stmt = select(Model).where(Model.slug == candidate)
        if not global_unique and locale is not None and hasattr(Model, "locale"):
            stmt = stmt.where(Model.locale == locale)
        existing = (await db.exec(stmt)).first()
        if not existing:
            return candidate

        suffix_text = f"-{suffix}"
        stem = base_slug[: max_length - len(suffix_text)].rstrip("-") or "item"
        candidate = f"{stem}{suffix_text}"
        suffix += 1


def _category_path(slug: str) -> str:
    return f"/products/{slug}"


def _product_path(category_slug: str | None, product_slug: str) -> str:
    if category_slug:
        return f"/products/{category_slug}/{product_slug}"
    return f"/products/{product_slug}"


def _application_path(slug: str) -> str:
    return f"/applications/{slug}"


def _faq_path() -> str:
    return "/faq"


# ── Project CRUD ──────────────────────────────────────────────────────────────

@router.post("/projects", response_model=IntakeProjectRead, status_code=201)
async def create_project(
    body: IntakeProjectCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = IntakeProject(
        **body.model_dump(),
        created_by=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[IntakeProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    result = await db.exec(
        select(IntakeProject).order_by(IntakeProject.created_at.desc())
    )
    return result.all()


@router.get("/projects/{project_id}", response_model=IntakeProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    project = await db.get(IntakeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=IntakeProjectRead)
async def update_project(
    project_id: uuid.UUID,
    body: IntakeProjectUpdate,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    project = await db.get(IntakeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(project, key, val)
    project.updated_at = utcnow_naive()
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


# ── Discovery & Extraction triggers ──────────────────────────────────────────

async def _run_discover(project_id: uuid.UUID) -> None:
    """Background task: run site discovery."""
    from app.services.intake_engine import discover_site

    async with get_session_ctx() as db:
        project = await db.get(IntakeProject, project_id)
        if project:
            await discover_site(project, db)


async def _run_extract(project_id: uuid.UUID) -> None:
    """Background task: run content extraction."""
    from app.services.intake_engine import extract_entities

    async with get_session_ctx() as db:
        project = await db.get(IntakeProject, project_id)
        if project:
            await extract_entities(project, db)


@router.post("/projects/{project_id}/discover")
async def trigger_discovery(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    project = await db.get(IntakeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("created", "discovered", "ready_for_review"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start discovery while project is '{project.status}'",
        )

    background_tasks.add_task(_run_discover, project_id)
    return {"message": "Discovery started", "project_id": str(project_id)}


@router.post("/projects/{project_id}/extract")
async def trigger_extraction(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    project = await db.get(IntakeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("discovered", "ready_for_review"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot extract while project is '{project.status}'. Run discovery first.",
        )

    background_tasks.add_task(_run_extract, project_id)
    return {"message": "Extraction started", "project_id": str(project_id)}


# ── URL Candidates ────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/urls", response_model=list[IntakeUrlCandidateRead])
async def list_url_candidates(
    project_id: uuid.UUID,
    page_type: Optional[str] = Query(default=None),
    review_status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    stmt = select(IntakeUrlCandidate).where(
        IntakeUrlCandidate.project_id == project_id
    )
    if page_type:
        stmt = stmt.where(IntakeUrlCandidate.page_type == page_type)
    if review_status:
        stmt = stmt.where(IntakeUrlCandidate.review_status == review_status)
    stmt = stmt.order_by(IntakeUrlCandidate.page_type, IntakeUrlCandidate.url)
    result = await db.exec(stmt)
    return result.all()


@router.patch("/urls/{url_id}/review", response_model=IntakeUrlCandidateRead)
async def review_url_candidate(
    url_id: uuid.UUID,
    body: IntakeUrlReview,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    candidate = await db.get(IntakeUrlCandidate, url_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="URL candidate not found")

    candidate.review_status = body.review_status
    if body.page_type:
        candidate.page_type = body.page_type
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


# ── Entity Candidates ─────────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/entities",
    response_model=list[IntakeEntityCandidateRead],
)
async def list_entity_candidates(
    project_id: uuid.UUID,
    entity_type: Optional[str] = Query(default=None),
    review_status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    stmt = select(IntakeEntityCandidate).where(
        IntakeEntityCandidate.project_id == project_id
    )
    if entity_type:
        stmt = stmt.where(IntakeEntityCandidate.entity_type == entity_type)
    if review_status:
        stmt = stmt.where(IntakeEntityCandidate.review_status == review_status)
    stmt = stmt.order_by(IntakeEntityCandidate.entity_type, IntakeEntityCandidate.display_name)
    result = await db.exec(stmt)
    return result.all()


@router.patch("/entities/{entity_id}/review", response_model=IntakeEntityCandidateRead)
async def review_entity_candidate(
    entity_id: uuid.UUID,
    body: IntakeEntityReview,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    entity = await db.get(IntakeEntityCandidate, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity candidate not found")

    entity.review_status = body.review_status
    if body.extracted_data is not None:
        entity.extracted_data = body.extracted_data
    entity.updated_at = utcnow_naive()
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


# ── Redirect Candidates ──────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/redirects",
    response_model=list[IntakeRedirectCandidateRead],
)
async def list_redirect_candidates(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    result = await db.exec(
        select(IntakeRedirectCandidate)
        .where(IntakeRedirectCandidate.project_id == project_id)
        .order_by(IntakeRedirectCandidate.from_path)
    )
    return result.all()


@router.patch("/redirects/{redirect_id}/review", response_model=IntakeRedirectCandidateRead)
async def review_redirect_candidate(
    redirect_id: uuid.UUID,
    body: IntakeRedirectReview,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    candidate = await db.get(IntakeRedirectCandidate, redirect_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Redirect candidate not found")

    candidate.review_status = body.review_status
    if body.suggested_to_path is not None:
        candidate.suggested_to_path = body.suggested_to_path
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


# ── Brief Candidates ─────────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/briefs",
    response_model=list[IntakeBriefCandidateRead],
)
async def list_brief_candidates(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    result = await db.exec(
        select(IntakeBriefCandidate)
        .where(IntakeBriefCandidate.project_id == project_id)
        .order_by(IntakeBriefCandidate.target_page_type, IntakeBriefCandidate.title_draft)
    )
    return result.all()


@router.patch("/briefs/{brief_id}/review", response_model=IntakeBriefCandidateRead)
async def review_brief_candidate(
    brief_id: uuid.UUID,
    body: IntakeBriefReview,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    candidate = await db.get(IntakeBriefCandidate, brief_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Brief candidate not found")

    candidate.review_status = body.review_status
    if body.title_draft is not None:
        candidate.title_draft = body.title_draft
    if body.primary_keyword is not None:
        candidate.primary_keyword = body.primary_keyword
    if body.suggested_slug is not None:
        candidate.suggested_slug = body.suggested_slug
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


# ── Commit to ForgeBase ──────────────────────────────────────────────────────

@router.post("/projects/{project_id}/commit")
async def commit_to_forgebase(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Commit reviewed intake outputs into ForgeBase production tables.

        Current implementation:
        - Accepted categories / products / applications / certifications / FAQs
            -> formal ForgeBase content tables
        - Product ↔ application / certification links
        - FAQ ↔ product / application links when strong name matches are found
    - Accepted redirects → Redirect table
        - Accepted briefs → PageBrief table, bound to committed entities
    """
    project = await db.get(IntakeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("ready_for_review",):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot commit while project is '{project.status}'",
        )

    from app.models.application import Application
    from app.models.associations import (
        ApplicationFAQLink,
        ProductApplicationLink,
        ProductCertificationLink,
        ProductFAQLink,
    )
    from app.models.certification import Certification
    from app.models.faq_item import FAQItem
    from app.models.page_brief import PageBrief
    from app.models.product import Product
    from app.models.product_category import ProductCategory
    from app.models.redirect import Redirect

    locale = _normalize_content_locale(project.locale)
    committed = {"entities": 0, "relationships": 0, "redirects": 0, "briefs": 0}

    url_result = await db.exec(
        select(IntakeUrlCandidate).where(IntakeUrlCandidate.project_id == project_id)
    )
    url_candidates = url_result.all()
    url_by_id = {candidate.id: candidate for candidate in url_candidates}

    entity_result = await db.exec(
        select(IntakeEntityCandidate).where(
            IntakeEntityCandidate.project_id == project_id,
            IntakeEntityCandidate.review_status == "accepted",
        )
    )
    accepted_entities = entity_result.all()
    entities_by_id = {entity.id: entity for entity in accepted_entities}

    entity_sort_order = {
        "category": 0,
        "application": 1,
        "certification": 2,
        "product": 3,
        "faq": 4,
    }
    accepted_entities.sort(
        key=lambda entity: (
            entity_sort_order.get(entity.entity_type, 99),
            entity.display_name or "",
        )
    )

    category_by_lookup: dict[str, ProductCategory] = {}
    category_by_id: dict[uuid.UUID, ProductCategory] = {}
    application_by_lookup: dict[str, Application] = {}
    certification_by_lookup: dict[str, Certification] = {}
    product_by_lookup: dict[str, Product] = {}
    product_by_model: dict[str, Product] = {}
    faq_by_question: dict[str, FAQItem] = {}
    entity_slug_by_id: dict[uuid.UUID, str] = {}
    source_path_to_target: dict[str, str] = {}
    fallback_category: ProductCategory | None = None

    async def ensure_link(Model: Any, **filters: Any) -> bool:
        stmt = select(Model)
        for field_name, value in filters.items():
            stmt = stmt.where(getattr(Model, field_name) == value)
        existing = (await db.exec(stmt)).first()
        if existing:
            return False
        db.add(Model(**filters))
        return True

    async def get_or_create_fallback_category() -> ProductCategory:
        nonlocal fallback_category
        if fallback_category is not None:
            return fallback_category

        fallback_name = _truncate_text(
            f"{project.project_name} Imported Products",
            60,
        ) or "Imported Products"
        stmt = select(ProductCategory).where(
            ProductCategory.category_name == fallback_name,
            ProductCategory.locale == locale,
        )
        existing = (await db.exec(stmt)).first()
        if existing:
            fallback_category = existing
        else:
            base_slug = _slug_candidate(fallback_name, f"intake-{project_id.hex[:8]}", 60)
            unique_slug = await _ensure_unique_slug(
                db,
                ProductCategory,
                base_slug,
                locale=locale,
                max_length=60,
                global_unique=True,
            )
            fallback_category = ProductCategory(
                category_name=fallback_name,
                slug=unique_slug,
                description=f"Auto-created fallback category for intake project {project.project_name}.",
                status="published",
                locale=locale,
            )
            db.add(fallback_category)
            await db.flush()

        _apply_published_state(fallback_category)
        category_by_id[fallback_category.id] = fallback_category
        lookup_key = _lookup_key(fallback_category.category_name)
        if lookup_key:
            category_by_lookup[lookup_key] = fallback_category
        return fallback_category

    def resolve_entity_source_path(entity: IntakeEntityCandidate) -> str | None:
        if not entity.source_url_id:
            return None
        url_candidate = url_by_id.get(entity.source_url_id)
        if not url_candidate:
            return None
        source_path = url_candidate.url.strip()
        if not source_path:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(source_path)
        return parsed.path or None

    for entity in accepted_entities:
        if entity.committed_entity_id is not None:
            continue

        data = _parse_json_object(entity.extracted_data)

        if entity.entity_type == "category":
            category_name = _truncate_text(
                _first_text(data.get("category_name"), entity.display_name, project.project_name),
                60,
            ) or "Imported Category"
            base_slug = _slug_candidate(category_name, f"category-{entity.id.hex[:8]}", 60)

            existing = (await db.exec(
                select(ProductCategory).where(ProductCategory.slug == base_slug)
            )).first()
            if not existing:
                existing = (await db.exec(
                    select(ProductCategory).where(
                        ProductCategory.category_name == category_name,
                        ProductCategory.locale == locale,
                    )
                )).first()

            if existing:
                if not existing.description and data.get("description"):
                    existing.description = data.get("description")
                _apply_published_state(existing)
                category = existing
            else:
                unique_slug = await _ensure_unique_slug(
                    db,
                    ProductCategory,
                    base_slug,
                    locale=locale,
                    max_length=60,
                    global_unique=True,
                )
                category = ProductCategory(
                    category_name=category_name,
                    slug=unique_slug,
                    description=data.get("description"),
                    status="published",
                    locale=locale,
                )
                db.add(category)
                await db.flush()

            entity.committed_entity_id = category.id
            entity.review_status = "merged"
            entity.updated_at = utcnow_naive()
            db.add(entity)

            lookup_key = _lookup_key(category.category_name)
            if lookup_key:
                category_by_lookup[lookup_key] = category
            category_by_id[category.id] = category
            entity_slug_by_id[entity.id] = category.slug
            source_path = resolve_entity_source_path(entity)
            if source_path:
                source_path_to_target[source_path] = _category_path(category.slug)
            committed["entities"] += 1

        elif entity.entity_type == "application":
            application_name = _truncate_text(
                _first_text(data.get("application_name"), entity.display_name),
                100,
            ) or f"Application {entity.id.hex[:6]}"
            base_slug = _slug_candidate(application_name, f"application-{entity.id.hex[:8]}", 100)

            existing = (await db.exec(
                select(Application).where(
                    Application.slug == base_slug,
                    Application.locale == locale,
                )
            )).first()
            if not existing:
                existing = (await db.exec(
                    select(Application).where(
                        Application.application_name == application_name,
                        Application.locale == locale,
                    )
                )).first()

            if existing:
                if not existing.description and data.get("description"):
                    existing.description = data.get("description")
                if not existing.challenge and data.get("challenge"):
                    existing.challenge = data.get("challenge")
                if not existing.solution and data.get("solution"):
                    existing.solution = data.get("solution")
                if not existing.industry and data.get("industry"):
                    existing.industry = _truncate_text(data.get("industry"), 60) or "General Industrial"
                _apply_published_state(existing)
                application = existing
            else:
                unique_slug = await _ensure_unique_slug(
                    db,
                    Application,
                    base_slug,
                    locale=locale,
                    max_length=100,
                    global_unique=False,
                )
                application = Application(
                    application_name=application_name,
                    slug=unique_slug,
                    industry=_truncate_text(data.get("industry"), 60) or "General Industrial",
                    description=data.get("description"),
                    challenge=data.get("challenge"),
                    solution=data.get("solution"),
                    status="published",
                    locale=locale,
                    published_at=utcnow_naive(),
                )
                db.add(application)
                await db.flush()

            entity.committed_entity_id = application.id
            entity.review_status = "merged"
            entity.updated_at = utcnow_naive()
            db.add(entity)

            for key in {
                _lookup_key(application.application_name),
                _lookup_key(application.slug),
            }:
                if key:
                    application_by_lookup[key] = application
            entity_slug_by_id[entity.id] = application.slug
            source_path = resolve_entity_source_path(entity)
            if source_path:
                source_path_to_target[source_path] = _application_path(application.slug)
            committed["entities"] += 1

        elif entity.entity_type == "certification":
            cert_name = _truncate_text(
                _first_text(data.get("certification_name"), entity.display_name),
                100,
            ) or f"Certification {entity.id.hex[:6]}"
            cert_number = _truncate_text(_first_text(data.get("cert_number")), 80)
            base_slug = _slug_candidate(cert_name, f"certification-{entity.id.hex[:8]}", 120)

            existing = None
            if cert_number:
                existing = (await db.exec(
                    select(Certification).where(Certification.cert_number == cert_number)
                )).first()
            if not existing:
                existing = (await db.exec(
                    select(Certification).where(
                        Certification.slug == base_slug,
                        Certification.locale == locale,
                    )
                )).first()
            if not existing:
                existing = (await db.exec(
                    select(Certification).where(
                        Certification.cert_name == cert_name,
                        Certification.locale == locale,
                    )
                )).first()

            if existing:
                if not existing.issuer and data.get("issuing_body"):
                    existing.issuer = _truncate_text(data.get("issuing_body"), 120)
                if not existing.description and data.get("scope"):
                    existing.description = data.get("scope")
                if not existing.expires_at and data.get("valid_until"):
                    existing.expires_at = _parse_datetime_value(data.get("valid_until"))
                if not existing.cert_number and cert_number:
                    existing.cert_number = cert_number
                _apply_published_state(existing)
                certification = existing
            else:
                unique_slug = await _ensure_unique_slug(
                    db,
                    Certification,
                    base_slug,
                    locale=locale,
                    max_length=120,
                    global_unique=False,
                )
                certification = Certification(
                    cert_name=cert_name,
                    slug=unique_slug,
                    issuer=_truncate_text(data.get("issuing_body"), 120),
                    cert_number=cert_number,
                    expires_at=_parse_datetime_value(data.get("valid_until")),
                    description=data.get("scope"),
                    status="published",
                    locale=locale,
                )
                db.add(certification)
                await db.flush()

            entity.committed_entity_id = certification.id
            entity.review_status = "merged"
            entity.updated_at = utcnow_naive()
            db.add(entity)

            for key in {
                _lookup_key(certification.cert_name),
                _lookup_key(certification.slug),
                _lookup_key(certification.cert_number),
            }:
                if key:
                    certification_by_lookup[key] = certification
            entity_slug_by_id[entity.id] = certification.slug
            committed["entities"] += 1

        elif entity.entity_type == "product":
            product_name = _truncate_text(
                _first_text(data.get("product_name"), entity.display_name),
                100,
            ) or f"Product {entity.id.hex[:6]}"
            base_slug = _slug_candidate(product_name, f"product-{entity.id.hex[:8]}", 100)
            model_number = _truncate_text(
                _first_text(data.get("model_number")),
                50,
            ) or f"INTAKE-{entity.id.hex[:8].upper()}"
            short_description = _truncate_text(
                _first_text(data.get("short_description"), data.get("description"), product_name),
                200,
            ) or product_name

            if len(category_by_id) == 1:
                product_category = next(iter(category_by_id.values()))
            else:
                product_category = await get_or_create_fallback_category()

            existing = (await db.exec(
                select(Product).where(Product.model_number == model_number)
            )).first()
            if not existing:
                existing = (await db.exec(
                    select(Product).where(
                        Product.slug == base_slug,
                        Product.locale == locale,
                    )
                )).first()

            specs_text = _json_text(data.get("specifications"))
            if existing:
                if not existing.product_name:
                    existing.product_name = product_name
                if not existing.short_description:
                    existing.short_description = short_description
                if not existing.full_description and data.get("description"):
                    existing.full_description = data.get("description")
                if not existing.specifications and specs_text:
                    existing.specifications = specs_text
                if not existing.category_id:
                    existing.category_id = product_category.id
                _apply_published_state(existing)
                product = existing
            else:
                unique_slug = await _ensure_unique_slug(
                    db,
                    Product,
                    base_slug,
                    locale=locale,
                    max_length=100,
                    global_unique=False,
                )
                product = Product(
                    product_name=product_name,
                    slug=unique_slug,
                    model_number=model_number,
                    short_description=short_description,
                    full_description=data.get("description"),
                    specifications=specs_text,
                    category_id=product_category.id,
                    status="published",
                    locale=locale,
                    published_at=utcnow_naive(),
                )
                db.add(product)
                await db.flush()

            entity.committed_entity_id = product.id
            entity.review_status = "merged"
            entity.updated_at = utcnow_naive()
            db.add(entity)

            for key in {
                _lookup_key(product.product_name),
                _lookup_key(product.slug),
            }:
                if key:
                    product_by_lookup[key] = product
            product_by_model[product.model_number.upper()] = product
            entity_slug_by_id[entity.id] = product.slug
            category_slug = category_by_id.get(product.category_id).slug if product.category_id in category_by_id else None
            source_path = resolve_entity_source_path(entity)
            if source_path:
                source_path_to_target[source_path] = _product_path(category_slug, product.slug)
            committed["entities"] += 1

        elif entity.entity_type == "faq":
            questions = data.get("questions")
            if not isinstance(questions, list):
                single_question = _first_text(data.get("question"))
                single_answer = _first_text(data.get("answer"))
                questions = [{"question": single_question, "answer": single_answer}] if single_question and single_answer else []

            first_faq_id: uuid.UUID | None = None
            source_path = resolve_entity_source_path(entity)
            for pair in questions:
                if not isinstance(pair, dict):
                    continue

                question = _truncate_text(_first_text(pair.get("question")), 300)
                answer = _first_text(pair.get("answer"))
                if not question or not answer:
                    continue

                existing = (await db.exec(
                    select(FAQItem).where(
                        FAQItem.question == question,
                        FAQItem.locale == locale,
                    )
                )).first()
                if existing:
                    if not existing.answer:
                        existing.answer = answer
                    _apply_published_state(existing)
                    faq_item = existing
                else:
                    faq_item = FAQItem(
                        question=question,
                        answer=answer,
                        category_tag=_truncate_text(_first_text(pair.get("category_tag"), data.get("category_tag")), 60),
                        locale=locale,
                        status="published",
                    )
                    db.add(faq_item)
                    await db.flush()

                if first_faq_id is None:
                    first_faq_id = faq_item.id

                faq_by_question[question] = faq_item

                haystack = f"{question} {answer}".lower()
                for product in product_by_model.values():
                    if product.model_number.lower() in haystack or product.product_name.lower() in haystack:
                        if await ensure_link(
                            ProductFAQLink,
                            product_id=product.id,
                            faq_item_id=faq_item.id,
                            sort_order=0,
                        ):
                            committed["relationships"] += 1

                for application in application_by_lookup.values():
                    if application.application_name.lower() in haystack:
                        if await ensure_link(
                            ApplicationFAQLink,
                            application_id=application.id,
                            faq_item_id=faq_item.id,
                            sort_order=0,
                        ):
                            committed["relationships"] += 1

            if first_faq_id is not None:
                entity.committed_entity_id = first_faq_id
                entity.review_status = "merged"
                entity.updated_at = utcnow_naive()
                db.add(entity)
                entity_slug_by_id[entity.id] = "faq"
                if source_path:
                    source_path_to_target[source_path] = _faq_path()
                committed["entities"] += 1

    for entity in accepted_entities:
        if entity.entity_type not in {"product", "application"}:
            continue
        if entity.committed_entity_id is None:
            continue

        data = _parse_json_object(entity.extracted_data)
        if entity.entity_type == "product":
            product = product_by_model.get(
                (_truncate_text(_first_text(data.get("model_number")), 50) or f"INTAKE-{entity.id.hex[:8].upper()}").upper()
            )
            if not product:
                continue

            for app_name in _string_list(data.get("applications")):
                lookup_key = _lookup_key(app_name)
                application = application_by_lookup.get(lookup_key) if lookup_key else None
                if application and await ensure_link(
                    ProductApplicationLink,
                    product_id=product.id,
                    application_id=application.id,
                ):
                    committed["relationships"] += 1

            for cert_name in _string_list(data.get("certifications")):
                lookup_key = _lookup_key(cert_name)
                certification = certification_by_lookup.get(lookup_key) if lookup_key else None
                if certification and await ensure_link(
                    ProductCertificationLink,
                    product_id=product.id,
                    certification_id=certification.id,
                ):
                    committed["relationships"] += 1

        elif entity.entity_type == "application":
            lookup_key = _lookup_key(_first_text(data.get("application_name"), entity.display_name))
            application = application_by_lookup.get(lookup_key) if lookup_key else None
            if not application:
                continue

            for product_label in _string_list(data.get("related_products")):
                related_product = product_by_model.get(product_label.upper())
                if not related_product:
                    related_product = product_by_lookup.get(_lookup_key(product_label) or "")
                if related_product and await ensure_link(
                    ProductApplicationLink,
                    product_id=related_product.id,
                    application_id=application.id,
                ):
                    committed["relationships"] += 1

    await db.flush()

    result = await db.exec(
        select(IntakeRedirectCandidate).where(
            IntakeRedirectCandidate.project_id == project_id,
            IntakeRedirectCandidate.review_status == "accepted",
            IntakeRedirectCandidate.committed_redirect_id.is_(None),  # type: ignore
        )
    )
    for rc in result.all():
        target_path = source_path_to_target.get(rc.from_path) or rc.suggested_to_path
        if not target_path:
            continue

        redirect = (await db.exec(
            select(Redirect).where(Redirect.from_path == rc.from_path)
        )).first()
        if redirect:
            redirect.to_path = target_path
            redirect.status_code = 301
            redirect.is_active = True
            redirect.note = f"Intake project: {project.project_name}"
            redirect.updated_at = utcnow_naive()
        else:
            redirect = Redirect(
                from_path=rc.from_path,
                to_path=target_path,
                status_code=301,
                note=f"Intake project: {project.project_name}",
            )
            db.add(redirect)
            await db.flush()

        rc.committed_redirect_id = redirect.id
        db.add(rc)
        committed["redirects"] += 1

    # Commit accepted briefs
    result = await db.exec(
        select(IntakeBriefCandidate).where(
            IntakeBriefCandidate.project_id == project_id,
            IntakeBriefCandidate.review_status == "accepted",
            IntakeBriefCandidate.committed_brief_id.is_(None),  # type: ignore
        )
    )
    for bc in result.all():
        related_entity_type = None
        related_entity_id = None
        target_slug = bc.suggested_slug
        if bc.entity_candidate_id:
            entity = entities_by_id.get(bc.entity_candidate_id)
            if entity and entity.committed_entity_id:
                related_entity_type = entity.entity_type
                related_entity_id = entity.committed_entity_id
                target_slug = entity_slug_by_id.get(entity.id, target_slug)

        brief = PageBrief(
            target_page_type=bc.target_page_type,
            target_slug=target_slug,
            title_draft=bc.title_draft,
            primary_keyword=bc.primary_keyword,
            secondary_keywords=bc.secondary_keywords,
            audience_persona=bc.audience_persona,
            buyer_stage=bc.buyer_stage or "awareness",
            notes=bc.notes or f"Auto-generated from intake project: {project.project_name}",
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            brief_status="draft",
            ai_status="pending",
            locale=locale,
            created_by=current_user.id,
        )
        db.add(brief)
        await db.flush()
        bc.committed_brief_id = brief.id
        db.add(bc)
        committed["briefs"] += 1

    # Update project status
    project.status = "committed"
    project.updated_at = utcnow_naive()
    db.add(project)
    await db.commit()

    return {
        "message": "Commit complete",
        "project_id": str(project_id),
        "committed": committed,
    }


# ── Project Summary ──────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/summary", response_model=IntakeProjectSummary)
async def get_project_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    project = await db.get(IntakeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # URL stats
    url_result = await db.exec(
        select(IntakeUrlCandidate.page_type, func.count(IntakeUrlCandidate.id))
        .where(IntakeUrlCandidate.project_id == project_id)
        .group_by(IntakeUrlCandidate.page_type)
    )
    urls_by_type = dict(url_result.all())
    total_urls = sum(urls_by_type.values())

    # Entity stats
    entity_result = await db.exec(
        select(IntakeEntityCandidate.entity_type, func.count(IntakeEntityCandidate.id))
        .where(IntakeEntityCandidate.project_id == project_id)
        .group_by(IntakeEntityCandidate.entity_type)
    )
    entities_by_type = dict(entity_result.all())
    total_entities = sum(entities_by_type.values())

    # Redirect & brief counts
    redirect_count = await db.exec(
        select(func.count(IntakeRedirectCandidate.id)).where(
            IntakeRedirectCandidate.project_id == project_id
        )
    )
    brief_count = await db.exec(
        select(func.count(IntakeBriefCandidate.id)).where(
            IntakeBriefCandidate.project_id == project_id
        )
    )

    return IntakeProjectSummary(
        project_id=project_id,
        status=project.status,
        total_urls=total_urls,
        urls_by_type=urls_by_type,
        total_entities=total_entities,
        entities_by_type=entities_by_type,
        total_redirects=redirect_count.one(),
        total_briefs=brief_count.one(),
    )
