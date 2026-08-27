"""0053_nurture_approval_gate

Add approval gate to nurture_sequences: emails are only sent for sequences
that have been explicitly approved by an admin/owner.

Revision ID: 0053_nurture_approval_gate
Revises: 0052_restore_nurture_engine
"""
import sqlalchemy as sa
from alembic import op

revision = "0053_nurture_approval_gate"
down_revision = "0052_restore_nurture_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nurture_sequences",
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "nurture_sequences",
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "nurture_sequences",
        sa.Column("approved_by", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_nurture_sequences_approved_by_users",
        "nurture_sequences",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_nurture_sequences_approved_by_users", "nurture_sequences", type_="foreignkey"
    )
    op.drop_column("nurture_sequences", "approved_by")
    op.drop_column("nurture_sequences", "approved_at")
    op.drop_column("nurture_sequences", "is_approved")
