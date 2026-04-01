"""0025_legacy_site_intake

Create tables for the Legacy Site Intake module:
  - intake_projects
  - intake_url_candidates
  - intake_entity_candidates
  - intake_redirect_candidates
  - intake_brief_candidates

Revision ID: 0025_legacy_site_intake
Revises: 0024_redirects_table
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_legacy_site_intake"
down_revision = "0024_redirects_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── intake_projects ───────────────────────────────────────────────────
    op.create_table(
        "intake_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="created"),
        sa.Column("locale", sa.String(5), nullable=False, server_default="zh-tw"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_urls_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_entities_extracted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )

    # ── intake_url_candidates ─────────────────────────────────────────────
    op.create_table(
        "intake_url_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("page_type", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["intake_projects.id"]),
    )
    op.create_index("ix_intake_url_candidates_project", "intake_url_candidates", ["project_id"])

    # ── intake_entity_candidates ──────────────────────────────────────────
    op.create_table(
        "intake_entity_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_url_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("extracted_data", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("display_name", sa.String(300), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("committed_entity_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["intake_projects.id"]),
        sa.ForeignKeyConstraint(["source_url_id"], ["intake_url_candidates.id"]),
    )
    op.create_index("ix_intake_entity_candidates_project", "intake_entity_candidates", ["project_id"])

    # ── intake_redirect_candidates ────────────────────────────────────────
    op.create_table(
        "intake_redirect_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("from_path", sa.String(500), nullable=False),
        sa.Column("suggested_to_path", sa.String(500), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("committed_redirect_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["intake_projects.id"]),
    )

    # ── intake_brief_candidates ───────────────────────────────────────────
    op.create_table(
        "intake_brief_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("entity_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("target_page_type", sa.String(40), nullable=False),
        sa.Column("suggested_slug", sa.String(120), nullable=True),
        sa.Column("title_draft", sa.String(200), nullable=True),
        sa.Column("primary_keyword", sa.String(100), nullable=True),
        sa.Column("secondary_keywords", sa.Text(), nullable=True),
        sa.Column("audience_persona", sa.String(200), nullable=True),
        sa.Column("buyer_stage", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("committed_brief_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["intake_projects.id"]),
        sa.ForeignKeyConstraint(["entity_candidate_id"], ["intake_entity_candidates.id"]),
    )


def downgrade() -> None:
    op.drop_table("intake_brief_candidates")
    op.drop_table("intake_redirect_candidates")
    op.drop_table("intake_entity_candidates")
    op.drop_table("intake_url_candidates")
    op.drop_table("intake_projects")
