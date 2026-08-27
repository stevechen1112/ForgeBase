"""Controlled public applications for ForgeBase managed delivery."""

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    ValidationInfo,
    field_validator,
)
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_superuser
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.adoption_application import AdoptionApplication
from app.models.user import User
from app.services.email_governance import is_authorized_synthetic_request
from app.services.form_challenge import (
    issue_form_challenge,
    validate_form_challenge,
    verify_turnstile,
)

forms_router = APIRouter(prefix="/forms/adoption", tags=["Adoption Applications"])
admin_router = APIRouter(prefix="/admin/adoption-applications", tags=["Platform Admin"])

VALID_STATUSES = {"new", "reviewing", "invited", "declined", "archived"}
VALID_SITUATIONS = {"no_site", "replace_site", "improve_site", "evaluating"}


class AdoptionApplicationIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    website_url: HttpUrl | None = None
    contact_name: str = Field(min_length=2, max_length=100)
    work_email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=100)
    industry: str = Field(min_length=2, max_length=120)
    target_markets: str | None = Field(default=None, max_length=500)
    current_situation: str = Field(max_length=40)
    requested_scope: str = Field(min_length=20, max_length=4000)
    preferred_language: Literal["zh-TW", "en"] = "zh-TW"
    consent: bool
    source_page: str | None = Field(default=None, max_length=500)
    bot_challenge: str | None = Field(default=None, max_length=1000)
    turnstile_token: str | None = Field(default=None, max_length=2000)
    website: str | None = Field(default=None, max_length=200)  # honeypot

    @field_validator(
        "company_name",
        "contact_name",
        "phone",
        "job_title",
        "industry",
        "target_markets",
        "requested_scope",
        "source_page",
    )
    @classmethod
    def clean_text(cls, value, info: ValidationInfo):
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if not cleaned and info.field_name in {"company_name", "contact_name", "industry", "requested_scope"}:
            raise ValueError("Text value cannot be blank")
        return cleaned

    @field_validator("current_situation")
    @classmethod
    def validate_situation(cls, value: str) -> str:
        if value not in VALID_SITUATIONS:
            raise ValueError("Invalid current_situation")
        return value

    @field_validator("consent")
    @classmethod
    def validate_consent(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("consent must be accepted")
        return value


class AdoptionApplicationRead(BaseModel):
    id: str
    application_number: str
    company_name: str
    website_url: str | None
    contact_name: str
    work_email: str
    phone: str | None
    job_title: str | None
    industry: str
    target_markets: str | None
    current_situation: str
    requested_scope: str
    preferred_language: str
    status: str
    internal_note: str | None
    source_page: str | None
    is_test_data: bool
    created_at: datetime
    reviewed_at: datetime | None


class AdoptionApplicationUpdate(BaseModel):
    status: str | None = None
    internal_note: str | None = Field(default=None, max_length=4000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_STATUSES:
            raise ValueError("Invalid status")
        return value


def _to_read(item: AdoptionApplication) -> AdoptionApplicationRead:
    payload = item.model_dump()
    payload["id"] = str(item.id)
    return AdoptionApplicationRead.model_validate(payload)


@forms_router.get("/challenge")
async def get_adoption_challenge():
    return {
        "challenge": issue_form_challenge(None),
        "turnstile_required": bool(settings.TURNSTILE_SECRET_KEY),
    }


@forms_router.post("", status_code=status.HTTP_201_CREATED)
async def submit_adoption_application(
    body: AdoptionApplicationIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if body.website:
        raise HTTPException(status_code=422, detail="Form verification failed")
    challenge_required = settings.is_production or settings.RFQ_BOT_CHALLENGE_REQUIRED
    if challenge_required and (
        not body.bot_challenge or not validate_form_challenge(body.bot_challenge, None)
    ):
        raise HTTPException(status_code=422, detail="Form challenge is invalid or expired")
    remote_ip = request.client.host if request.client else None
    if not await verify_turnstile(
        body.turnstile_token,
        remote_ip,
        expected_action="adoption_submit",
    ):
        raise HTTPException(status_code=422, detail="Bot verification failed")

    now = utcnow_naive()
    is_test_data = is_authorized_synthetic_request(
        request.headers.get("x-forgebase-test-token")
    )
    application_number = f"APP-{now:%Y%m%d}-{secrets.token_hex(8).upper()}"
    source_ip_hash = None
    if remote_ip:
        source_ip_hash = hmac.new(
            settings.SECRET_KEY.encode(),
            remote_ip.encode(),
            hashlib.sha256,
        ).hexdigest()

    item = AdoptionApplication(
        application_number=application_number,
        company_name=body.company_name,
        website_url=str(body.website_url) if body.website_url else None,
        contact_name=body.contact_name,
        work_email=str(body.work_email).lower(),
        phone=body.phone,
        job_title=body.job_title,
        industry=body.industry,
        target_markets=body.target_markets,
        current_situation=body.current_situation,
        requested_scope=body.requested_scope,
        preferred_language=body.preferred_language,
        consent=body.consent,
        consent_policy_version=settings.CONSENT_POLICY_VERSION,
        source_page=body.source_page,
        source_ip_hash=source_ip_hash,
        is_test_data=is_test_data,
        test_run_id=(request.headers.get("x-forgebase-test-run", "")[:100] or None)
        if is_test_data
        else None,
    )
    session.add(item)
    await session.commit()
    return {
        "application_number": application_number,
        "status": "received",
        "message": "Application received for assessment; no account or trial was created.",
    }


@admin_router.get("")
async def list_adoption_applications(
    application_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
    include_test: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
):
    query = select(AdoptionApplication)
    count_query = select(func.count()).select_from(AdoptionApplication)
    filters = []
    if application_status:
        if application_status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid status")
        filters.append(AdoptionApplication.status == application_status)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            col(AdoptionApplication.company_name).ilike(pattern)
            | col(AdoptionApplication.work_email).ilike(pattern)
        )
    if not include_test:
        filters.append(AdoptionApplication.is_test_data.is_(False))
    for expression in filters:
        query = query.where(expression)
        count_query = count_query.where(expression)
    total = (await session.exec(count_query)).one()
    items = (
        await session.exec(
            query.order_by(AdoptionApplication.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "data": [_to_read(item).model_dump() for item in items],
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
        },
    }


@admin_router.patch("/{application_id}")
async def update_adoption_application(
    application_id: str,
    body: AdoptionApplicationUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
):
    try:
        import uuid

        parsed_id = uuid.UUID(application_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid application id") from exc
    item = await session.get(AdoptionApplication, parsed_id)
    if not item:
        raise HTTPException(status_code=404, detail="Application not found")
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(item, key, value)
    item.updated_at = utcnow_naive()
    if "status" in updates and updates["status"] != "new":
        item.reviewed_at = item.reviewed_at or item.updated_at
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _to_read(item)
