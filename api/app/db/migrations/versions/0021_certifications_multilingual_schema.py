"""certifications multilingual schema

Revision ID: 0021_certifications_multilingual_schema
Revises: 0020_chat_session_relax_fk
Create Date: 2026-03-18 00:00:00.000000
"""

from alembic import op

revision = "0021_certifications_multilingual_schema"
down_revision = "0020_chat_session_relax_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'certifications' AND indexname = 'ix_certifications_slug'
            ) THEN
                DROP INDEX ix_certifications_slug;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'certifications'::regclass AND conname = 'certifications_slug_key'
            ) THEN
                ALTER TABLE certifications DROP CONSTRAINT certifications_slug_key;
            END IF;
        END
        $$;
        """
    )

    op.create_index("ix_certifications_slug", "certifications", ["slug"], unique=False)
    op.create_unique_constraint(
        "uq_certifications_slug_locale", "certifications", ["slug", "locale"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_certifications_slug_locale", "certifications", type_="unique")
    op.drop_index("ix_certifications_slug", table_name="certifications")
    op.create_unique_constraint("certifications_slug_key", "certifications", ["slug"])