"""Alembic migration 0014 — Phase 3 ML Intent Scoring fields (3.2.1)

- visitors: add ml_intent_score (float, nullable), ml_score_updated_at (timestamptz, nullable)
"""
import sqlalchemy as sa
from alembic import op

revision = "0014_phase3_ml_scoring"
down_revision = "0013_phase2_download_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visitors",
        sa.Column("ml_intent_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "visitors",
        sa.Column(
            "ml_score_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("visitors", "ml_score_updated_at")
    op.drop_column("visitors", "ml_intent_score")
