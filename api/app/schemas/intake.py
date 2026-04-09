"""Pydantic schemas for Legacy Site Intake API."""
import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator


# ── IntakeProject ─────────────────────────────────────────────────────────────

class IntakeProjectCreate(BaseModel):
    project_name: str = Field(max_length=200)
    source_url: str = Field(max_length=500)
    locale: str = Field(default="zh-tw", max_length=5)
    notes: Optional[str] = None

    @field_validator("source_url")
    @classmethod
    def must_be_valid_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("source_url must start with http:// or https://")
        return v.rstrip("/")


class IntakeProjectUpdate(BaseModel):
    project_name: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = Field(default=None, max_length=30)
    notes: Optional[str] = None


class IntakeProjectRead(BaseModel):
    id: uuid.UUID
    project_name: str
    source_url: str
    status: str
    locale: str
    notes: Optional[str]
    total_urls_found: int
    total_entities_extracted: int
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── IntakeUrlCandidate ────────────────────────────────────────────────────────

class IntakeUrlCandidateRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    url: str
    page_type: str
    title: Optional[str]
    meta_description: Optional[str]
    http_status: Optional[int]
    content_length: Optional[int]
    confidence: Optional[float]
    review_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IntakeUrlReview(BaseModel):
    """Accept or skip a URL candidate."""
    review_status: str = Field(max_length=20)
    page_type: Optional[str] = Field(default=None, max_length=40)

    @field_validator("review_status")
    @classmethod
    def valid_review_status(cls, v: str) -> str:
        if v not in ("accepted", "skipped", "pending"):
            raise ValueError("review_status must be 'accepted', 'skipped', or 'pending'")
        return v


# ── IntakeEntityCandidate ─────────────────────────────────────────────────────

class IntakeEntityCandidateRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_url_id: Optional[uuid.UUID]
    entity_type: str
    extracted_data: Any  # parsed as JSON in API
    display_name: Optional[str]
    confidence: Optional[float]
    review_status: str
    committed_entity_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IntakeEntityReview(BaseModel):
    """Accept, merge, or skip an entity candidate."""
    review_status: str = Field(max_length=20)
    extracted_data: Optional[str] = None  # allow manual edits

    @field_validator("review_status")
    @classmethod
    def valid_review_status(cls, v: str) -> str:
        if v not in ("accepted", "merged", "skipped", "pending"):
            raise ValueError("review_status must be 'accepted', 'merged', 'skipped', or 'pending'")
        return v


# ── IntakeRedirectCandidate ───────────────────────────────────────────────────

class IntakeRedirectCandidateRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    from_path: str
    suggested_to_path: Optional[str]
    review_status: str
    committed_redirect_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class IntakeRedirectReview(BaseModel):
    review_status: str = Field(max_length=20)
    suggested_to_path: Optional[str] = Field(default=None, max_length=500)

    @field_validator("review_status")
    @classmethod
    def valid_review_status(cls, v: str) -> str:
        if v not in ("accepted", "skipped", "pending"):
            raise ValueError("review_status must be 'accepted', 'skipped', or 'pending'")
        return v


# ── IntakeBriefCandidate ──────────────────────────────────────────────────────

class IntakeBriefCandidateRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    entity_candidate_id: Optional[uuid.UUID]
    target_page_type: str
    suggested_slug: Optional[str]
    title_draft: Optional[str]
    primary_keyword: Optional[str]
    secondary_keywords: Optional[str]
    audience_persona: Optional[str]
    buyer_stage: Optional[str]
    notes: Optional[str]
    review_status: str
    committed_brief_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class IntakeBriefReview(BaseModel):
    review_status: str = Field(max_length=20)
    title_draft: Optional[str] = Field(default=None, max_length=200)
    primary_keyword: Optional[str] = Field(default=None, max_length=100)
    suggested_slug: Optional[str] = Field(default=None, max_length=120)

    @field_validator("review_status")
    @classmethod
    def valid_review_status(cls, v: str) -> str:
        if v not in ("accepted", "skipped", "pending"):
            raise ValueError("review_status must be 'accepted', 'skipped', or 'pending'")
        return v


# ── Summary / Report ──────────────────────────────────────────────────────────

class IntakeProjectSummary(BaseModel):
    """Aggregated stats returned after discovery or extraction completes."""
    project_id: uuid.UUID
    status: str
    total_urls: int
    urls_by_type: dict[str, int]
    total_entities: int
    entities_by_type: dict[str, int]
    total_redirects: int
    total_briefs: int
