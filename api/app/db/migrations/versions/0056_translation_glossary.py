"""0056_translation_glossary

Add translation_glossary_json to site_profiles (per-tenant glossary for
LLM-assisted locale drafting).

Revision ID: 0056_translation_glossary
Revises: 0055_nurture_outbox_unique_pending
"""
import sqlalchemy as sa
from alembic import op

revision = "0056_translation_glossary"
down_revision = "0055_nurture_outbox_unique_pending"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_profiles",
        sa.Column("translation_glossary_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site_profiles", "translation_glossary_json")
