"""phase2 multilingual schema: composite slug+locale unique constraints

Revision ID: 0007_phase2_multilingual_schema
Revises: 0006_phase2_audience_segments
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op

revision = "0007_phase2_multilingual_schema"
down_revision = "0006_phase2_audience_segments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Products ──────────────────────────────────────────────────────────────
    # Drop the existing unique constraint on products.slug (name varies by how
    # Alembic+SQLModel generated it — try both common names)
    op.execute(
        """
        DO $$
        BEGIN
            -- drop the unique index created by SQLModel unique=True on slug
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'products' AND indexname = 'uq_products_slug'
            ) THEN
                DROP INDEX uq_products_slug;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'products'::regclass AND conname = 'products_slug_key'
            ) THEN
                ALTER TABLE products DROP CONSTRAINT products_slug_key;
            END IF;
        END
        $$;
        """
    )
    # Add composite unique constraint (slug, locale)
    op.create_unique_constraint(
        "uq_products_slug_locale", "products", ["slug", "locale"]
    )

    # ── Applications ──────────────────────────────────────────────────────────
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'applications' AND indexname = 'uq_applications_slug'
            ) THEN
                DROP INDEX uq_applications_slug;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'applications'::regclass AND conname = 'applications_slug_key'
            ) THEN
                ALTER TABLE applications DROP CONSTRAINT applications_slug_key;
            END IF;
        END
        $$;
        """
    )
    op.create_unique_constraint(
        "uq_applications_slug_locale", "applications", ["slug", "locale"]
    )


def downgrade() -> None:
    # Remove composite constraints
    op.drop_constraint("uq_products_slug_locale", "products", type_="unique")
    op.drop_constraint("uq_applications_slug_locale", "applications", type_="unique")

    # Restore single-column unique constraints
    op.create_unique_constraint("products_slug_key", "products", ["slug"])
    op.create_unique_constraint("applications_slug_key", "applications", ["slug"])
