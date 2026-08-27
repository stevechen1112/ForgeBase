"""Public advisor knowledge index, chat qualification, shared rate-limit hits.

Revision ID: 0076_knowledge_index_and_rate_limit
Revises: 0075_tenant_feature_entitlements
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0076_knowledge_index_and_rate_limit"
down_revision = "0075_tenant_feature_entitlements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("qualification_json", sa.Text(), nullable=True))
    op.add_column(
        "content_assets",
        sa.Column("index_status", sa.String(30), nullable=False, server_default="not_indexed"),
    )
    op.add_column(
        "content_assets",
        sa.Column("index_error", sa.String(500), nullable=True),
    )

    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="public"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("canonical_url", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("index_error", sa.String(500), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_sources_tenant_id", "knowledge_sources", ["tenant_id"])
    op.create_index("ix_knowledge_sources_source_type", "knowledge_sources", ["source_type"])
    op.create_index("ix_knowledge_sources_source_id", "knowledge_sources", ["source_id"])
    op.create_index("ix_knowledge_sources_status", "knowledge_sources", ["status"])
    op.create_unique_constraint(
        "uq_knowledge_sources_tenant_type_id_locale",
        "knowledge_sources",
        ["tenant_id", "source_type", "source_id", "locale"],
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])
    op.create_index("ix_knowledge_chunks_tenant_id", "knowledge_chunks", ["tenant_id"])
    op.execute(
        "ALTER TABLE knowledge_chunks "
        "ADD COLUMN tsv tsvector GENERATED ALWAYS AS "
        "(to_tsvector('simple', coalesce(text, ''))) STORED"
    )
    op.execute("CREATE INDEX ix_knowledge_chunks_tsv ON knowledge_chunks USING GIN (tsv)")

    op.create_table(
        "knowledge_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column("action", sa.String(20), nullable=False, server_default="compile"),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(2000), nullable=True),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_sync_jobs_tenant_id", "knowledge_sync_jobs", ["tenant_id"])
    op.create_index("ix_knowledge_sync_jobs_status", "knowledge_sync_jobs", ["status"])
    op.create_index("ix_knowledge_sync_jobs_available_at", "knowledge_sync_jobs", ["available_at"])
    op.create_unique_constraint("uq_knowledge_sync_jobs_dedupe_key", "knowledge_sync_jobs", ["dedupe_key"])

    op.create_table(
        "rate_limit_hits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bucket_key", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rate_limit_hits_bucket_key", "rate_limit_hits", ["bucket_key"])
    op.create_index("ix_rate_limit_hits_created_at", "rate_limit_hits", ["created_at"])
    op.create_index(
        "ix_rate_limit_hits_bucket_created",
        "rate_limit_hits",
        ["bucket_key", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("rate_limit_hits")
    op.drop_table("knowledge_sync_jobs")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
    op.drop_column("content_assets", "index_error")
    op.drop_column("content_assets", "index_status")
    op.drop_column("chat_sessions", "qualification_json")
