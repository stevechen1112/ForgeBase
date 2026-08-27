import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Computed, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class KnowledgeSource(SQLModel, table=True):
    """One published CMS object or opted-in public document per tenant/locale."""

    __tablename__ = "knowledge_sources"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_type",
            "source_id",
            "locale",
            name="uq_knowledge_sources_tenant_type_id_locale",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    source_type: str = Field(max_length=30, index=True)
    source_id: uuid.UUID = Field(index=True)
    locale: str = Field(default="en", max_length=10)
    visibility: str = Field(default="public", max_length=20)
    status: str = Field(default="pending", max_length=20, index=True)
    title: str = Field(max_length=300)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    content_hash: Optional[str] = Field(default=None, max_length=64)
    index_error: Optional[str] = Field(default=None, max_length=500)
    page_count: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class KnowledgeChunk(SQLModel, table=True):
    """Searchable public-advisor slice. Tombstoned sources have zero live rows."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_tsv", "tsv", postgresql_using="gin"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_id: uuid.UUID = Field(
        foreign_key="knowledge_sources.id", ondelete="CASCADE", index=True
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    chunk_index: int = Field(default=0)
    page_number: Optional[int] = Field(default=None)
    text: str = Field(sa_column=Column(Text, nullable=False))
    # Migration 0076 creates this stored search vector. Declaring the generated
    # column here keeps runtime metadata aligned without making application code
    # responsible for maintaining it.
    tsv: Optional[str] = Field(
        default=None,
        sa_column=Column(
            TSVECTOR,
            Computed("to_tsvector('simple', coalesce(text, ''))", persisted=True),
        ),
    )
    embedding_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    metadata_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utcnow_naive)


class KnowledgeSyncJob(SQLModel, table=True):
    """Durable compile/tombstone work so publish and file extract can retry."""

    __tablename__ = "knowledge_sync_jobs"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_knowledge_sync_jobs_dedupe_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    source_type: str = Field(max_length=30)
    source_id: uuid.UUID
    locale: str = Field(default="en", max_length=10)
    action: str = Field(default="compile", max_length=20)
    dedupe_key: str = Field(max_length=200)
    status: str = Field(default="queued", max_length=20, index=True)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=5)
    locked_at: Optional[datetime] = Field(default=None)
    last_error: Optional[str] = Field(default=None, max_length=2000)
    available_at: datetime = Field(default_factory=utcnow_naive, index=True)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class RateLimitHit(SQLModel, table=True):
    """Shared sliding-window counters across API workers."""

    __tablename__ = "rate_limit_hits"
    __table_args__ = (
        Index("ix_rate_limit_hits_bucket_created", "bucket_key", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    bucket_key: str = Field(max_length=300, index=True)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
