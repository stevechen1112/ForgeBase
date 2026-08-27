"""Controlled managed-delivery adoption applications.

Revision ID: 0071_adoption_applications
Revises: 0070_external_test_hardening
"""

import sqlalchemy as sa
from alembic import op

revision = "0071_adoption_applications"
down_revision = "0070_external_test_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adoption_applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("application_number", sa.String(40), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("contact_name", sa.String(100), nullable=False),
        sa.Column("work_email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("job_title", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(120), nullable=False),
        sa.Column("target_markets", sa.String(500), nullable=True),
        sa.Column("current_situation", sa.String(40), nullable=False),
        sa.Column("requested_scope", sa.String(4000), nullable=False),
        sa.Column("preferred_language", sa.String(10), nullable=False, server_default="zh-TW"),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_policy_version", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("internal_note", sa.String(4000), nullable=True),
        sa.Column("source_page", sa.String(500), nullable=True),
        sa.Column("source_ip_hash", sa.String(64), nullable=True),
        sa.Column("is_test_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("test_run_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("application_number", name="uq_adoption_applications_number"),
    )
    for column in (
        "application_number",
        "company_name",
        "work_email",
        "industry",
        "status",
        "is_test_data",
        "created_at",
    ):
        op.create_index(
            f"ix_adoption_applications_{column}",
            "adoption_applications",
            [column],
        )


def downgrade() -> None:
    op.drop_table("adoption_applications")
