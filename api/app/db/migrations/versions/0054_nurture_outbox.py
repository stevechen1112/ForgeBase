"""0054_nurture_outbox

Add per-email outbox queue: due nurture steps are queued as pending emails
that require manual approval (send/skip) instead of being sent automatically.

Revision ID: 0054_nurture_outbox
Revises: 0053_nurture_approval_gate
"""
import sqlalchemy as sa
from alembic import op

revision = "0054_nurture_outbox"
down_revision = "0053_nurture_approval_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nurture_outbox",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("enrollment_id", sa.UUID(), nullable=False),
        sa.Column("sequence_id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["enrollment_id"], ["nurture_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sequence_id"], ["nurture_sequences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["nurture_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nurture_outbox_enrollment_id", "nurture_outbox", ["enrollment_id"])
    op.create_index("ix_nurture_outbox_sequence_id", "nurture_outbox", ["sequence_id"])
    op.create_index("ix_nurture_outbox_tenant_id", "nurture_outbox", ["tenant_id"])
    op.create_index("ix_nurture_outbox_status", "nurture_outbox", ["status"])


def downgrade() -> None:
    op.drop_table("nurture_outbox")
