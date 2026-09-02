"""Remove retired nurture and audience-segmentation persistence.

Revision ID: 0103_remove_nurture_and_segments
Revises: 0102_realign_rfq_to_handoff_scope

ForgeBase now ends when a website inquiry is handed to a sales owner. These
tables powered post-handoff email campaigns and must not remain as dormant
runtime capability.
"""

from alembic import op

revision = "0103_remove_nurture_and_segments"
down_revision = "0102_realign_rfq_to_handoff_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Outreach revisions previously retained optional nurture references.
    op.execute("ALTER TABLE IF EXISTS outreach_messages DROP COLUMN IF EXISTS nurture_sequence_id")
    op.execute("ALTER TABLE IF EXISTS outreach_messages DROP COLUMN IF EXISTS nurture_step_id")
    op.execute("DROP TABLE IF EXISTS nurture_outbox CASCADE")
    op.execute("DROP TABLE IF EXISTS nurture_enrollments CASCADE")
    op.execute("DROP TABLE IF EXISTS nurture_steps CASCADE")
    op.execute("DROP TABLE IF EXISTS nurture_sequences CASCADE")
    op.execute("DROP TABLE IF EXISTS segments CASCADE")


def downgrade() -> None:
    raise RuntimeError("0103 intentionally retires post-handoff campaign data; restore a verified backup instead.")
