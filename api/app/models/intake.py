"""
Legacy Site Intake models — stores crawl projects, discovered URLs,
extracted entity candidates, redirect candidates, and brief drafts.

Used by the Intake engine that converts legacy catalogue websites
into ForgeBase-ready structured content.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text

from app.core.datetime import utcnow_naive


class IntakeProject(SQLModel, table=True):
    """
    Top-level container for a single legacy-site intake job.
    One project = one source website being analysed.
    """
    __tablename__ = "intake_projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_name: str = Field(max_length=200)
    source_url: str = Field(max_length=500)
    # overall status: created → crawling → extracting → ready_for_review → committed → archived
    status: str = Field(default="created", max_length=30)
    locale: str = Field(default="zh-tw", max_length=5)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    # summary stats (populated after discovery)
    total_urls_found: int = Field(default=0)
    total_entities_extracted: int = Field(default=0)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class IntakeUrlCandidate(SQLModel, table=True):
    """
    A single URL discovered from the legacy site.
    Each URL is classified into a page_type and assigned a priority.
    """
    __tablename__ = "intake_url_candidates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="intake_projects.id", index=True)
    url: str = Field(max_length=1000)
    # page_type detected: company | category | product | application | faq | contact | resource | blog | unknown
    page_type: str = Field(default="unknown", max_length=40)
    title: Optional[str] = Field(default=None, max_length=500)
    meta_description: Optional[str] = Field(default=None, max_length=500)
    http_status: Optional[int] = Field(default=None)
    content_length: Optional[int] = Field(default=None)
    # AI confidence in page_type classification (0.0 - 1.0)
    confidence: Optional[float] = Field(default=None)
    # review status: pending → accepted → skipped
    review_status: str = Field(default="pending", max_length=20)
    raw_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow_naive)


class IntakeEntityCandidate(SQLModel, table=True):
    """
    A structured entity extracted from one or more IntakeUrlCandidates.
    Represents a product, category, application, FAQ, certification, or asset
    that can be committed into ForgeBase's content models.
    """
    __tablename__ = "intake_entity_candidates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="intake_projects.id", index=True)
    source_url_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="intake_url_candidates.id"
    )
    # entity_type: product | category | application | faq | certification | asset
    entity_type: str = Field(max_length=40)
    # extracted fields stored as flexible JSON
    extracted_data: str = Field(default="{}", sa_column=Column(Text))
    # human-readable label for review UI
    display_name: Optional[str] = Field(default=None, max_length=300)
    # AI confidence in extraction quality (0.0 - 1.0)
    confidence: Optional[float] = Field(default=None)
    # review status: pending → accepted → merged → skipped
    review_status: str = Field(default="pending", max_length=20)
    # after commit, stores the id of the created ForgeBase entity
    committed_entity_id: Optional[uuid.UUID] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class IntakeRedirectCandidate(SQLModel, table=True):
    """
    Proposed 301 redirect from old URL to new ForgeBase URL.
    Generated after entity candidates are committed, to preserve SEO equity.
    """
    __tablename__ = "intake_redirect_candidates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="intake_projects.id", index=True)
    from_path: str = Field(max_length=500)
    suggested_to_path: Optional[str] = Field(default=None, max_length=500)
    # review status: pending → accepted → skipped
    review_status: str = Field(default="pending", max_length=20)
    # if accepted, the id of the created Redirect row
    committed_redirect_id: Optional[uuid.UUID] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)


class IntakeBriefCandidate(SQLModel, table=True):
    """
    Draft PageBrief generated from intake analysis.
    After review, committed as a real PageBrief for AI content generation.
    """
    __tablename__ = "intake_brief_candidates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="intake_projects.id", index=True)
    entity_candidate_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="intake_entity_candidates.id"
    )
    target_page_type: str = Field(max_length=40)
    suggested_slug: Optional[str] = Field(default=None, max_length=120)
    title_draft: Optional[str] = Field(default=None, max_length=200)
    primary_keyword: Optional[str] = Field(default=None, max_length=100)
    secondary_keywords: Optional[str] = Field(default=None, sa_column=Column(Text))
    audience_persona: Optional[str] = Field(default=None, max_length=200)
    buyer_stage: Optional[str] = Field(default=None, max_length=40)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    # review status: pending → accepted → skipped
    review_status: str = Field(default="pending", max_length=20)
    # after commit, stores the id of the created PageBrief
    committed_brief_id: Optional[uuid.UUID] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
