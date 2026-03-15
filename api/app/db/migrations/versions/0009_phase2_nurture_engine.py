"""0009_phase2_nurture_engine

2.1.4 Email Nurture Engine — creates nurture_sequences, nurture_steps,
nurture_enrollments tables.

Revision ID: 0009_phase2_nurture_engine
Revises: 0008_phase2_ip_to_company
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_phase2_nurture_engine"
down_revision = "0008_phase2_ip_to_company"
branch_labels = None
depends_on = None


def upgrade():
    # ── nurture_sequences ────────────────────────────────────────────────────
    op.create_table(
        "nurture_sequences",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("trigger_value", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_re_enrollment", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nurture_sequences_name", "nurture_sequences", ["name"])

    # ── nurture_steps ────────────────────────────────────────────────────────
    op.create_table(
        "nurture_steps",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("sequence_id", sa.UUID(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delay_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("from_name", sa.String(200), nullable=True),
        sa.Column("from_email", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["sequence_id"], ["nurture_sequences.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nurture_steps_sequence_id", "nurture_steps", ["sequence_id"])

    # ── nurture_enrollments ──────────────────────────────────────────────────
    op.create_table(
        "nurture_enrollments",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("sequence_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="'active'"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_type", sa.String(30), nullable=True),
        sa.Column("trigger_value", sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(["sequence_id"], ["nurture_sequences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nurture_enrollments_sequence_id", "nurture_enrollments", ["sequence_id"])
    op.create_index("ix_nurture_enrollments_contact_id", "nurture_enrollments", ["contact_id"])
    op.create_index(
        "ix_nurture_enrollments_status",
        "nurture_enrollments",
        ["status"],
    )


def downgrade():
    op.drop_table("nurture_enrollments")
    op.drop_table("nurture_steps")
    op.drop_table("nurture_sequences")
