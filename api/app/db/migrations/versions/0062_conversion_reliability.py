"""Conversion reliability, provenance, and tenant isolation.

Revision ID: 0062_conversion_reliability
Revises: 0061_content_asset_tenant_scope
"""
import sqlalchemy as sa
from alembic import op

revision = "0062_conversion_reliability"
down_revision = "0061_content_asset_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_assets", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.create_index("ix_content_assets_sha256", "content_assets", ["sha256"])

    op.add_column("segments", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_segments_tenant_id", "segments", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_segments_tenant_id", "segments", ["tenant_id"])
    op.execute(
        """
        UPDATE segments AS segment
        SET tenant_id = users.tenant_id
        FROM users
        WHERE segment.created_by = users.id AND segment.tenant_id IS NULL
        """
    )
    connection = op.get_bind()
    orphan_count = connection.execute(
        sa.text("SELECT count(*) FROM segments WHERE tenant_id IS NULL")
    ).scalar_one()
    if orphan_count:
        tenant_count = connection.execute(sa.text("SELECT count(*) FROM tenants")).scalar_one()
        if tenant_count != 1:
            raise RuntimeError(
                f"Cannot tenant-scope {orphan_count} segment(s); assign created_by before migrating"
            )
        op.execute("UPDATE segments SET tenant_id = (SELECT id FROM tenants LIMIT 1) WHERE tenant_id IS NULL")
    op.alter_column("segments", "tenant_id", nullable=False)

    op.create_table(
        "rfq_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("chat_session_id", sa.Uuid(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("tenant_id", "visitor_id", "chat_session_id", "expires_at"):
        op.create_index(f"ix_rfq_drafts_{column}", "rfq_drafts", [column])

    op.add_column("rfq_requests", sa.Column("intent_snapshot_json", sa.Text(), nullable=True))
    op.add_column("rfq_requests", sa.Column("attribution_json", sa.Text(), nullable=True))
    op.add_column("rfq_requests", sa.Column("source_chat_session_id", sa.Uuid(), nullable=True))
    op.add_column("rfq_requests", sa.Column("source_draft_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_rfq_requests_source_chat_session_id",
        "rfq_requests", "chat_sessions", ["source_chat_session_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_rfq_requests_source_draft_id",
        "rfq_requests", "rfq_drafts", ["source_draft_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_rfq_requests_source_chat_session_id", "rfq_requests", ["source_chat_session_id"])
    op.create_index("ix_rfq_requests_source_draft_id", "rfq_requests", ["source_draft_id"])

    op.create_table(
        "operational_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in ("tenant_id", "job_type", "status", "available_at", "idempotency_key"):
        op.create_index(f"ix_operational_jobs_{column}", "operational_jobs", [column])


def downgrade() -> None:
    op.drop_table("operational_jobs")
    op.drop_index("ix_rfq_requests_source_draft_id", table_name="rfq_requests")
    op.drop_index("ix_rfq_requests_source_chat_session_id", table_name="rfq_requests")
    op.drop_constraint("fk_rfq_requests_source_draft_id", "rfq_requests", type_="foreignkey")
    op.drop_constraint("fk_rfq_requests_source_chat_session_id", "rfq_requests", type_="foreignkey")
    op.drop_column("rfq_requests", "source_draft_id")
    op.drop_column("rfq_requests", "source_chat_session_id")
    op.drop_column("rfq_requests", "attribution_json")
    op.drop_column("rfq_requests", "intent_snapshot_json")
    op.drop_table("rfq_drafts")
    op.drop_index("ix_segments_tenant_id", table_name="segments")
    op.drop_constraint("fk_segments_tenant_id", "segments", type_="foreignkey")
    op.drop_column("segments", "tenant_id")
    op.drop_index("ix_content_assets_sha256", table_name="content_assets")
    op.drop_column("content_assets", "sha256")
