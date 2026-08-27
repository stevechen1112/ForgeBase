"""0058_normalize_locale_case

Normalize legacy 'zh-TW' locale values to 'zh-tw'. The admin forms now use
lowercase 'zh-tw' everywhere; pre-existing rows saved with the old 'zh-TW'
option would be orphaned (invisible to the zh-tw list filter and treated as
missing by the locale-variant switcher).

Revision ID: 0058_normalize_locale_case
Revises: 0057_products_image_url
"""
from alembic import op

revision = "0058_normalize_locale_case"
down_revision = "0057_products_image_url"
branch_labels = None
depends_on = None

TABLES = (
    "products",
    "product_categories",
    "applications",
    "pages",
    "faq_items",
    "certifications",
    "capabilities",
    "comparison_topics",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET locale = 'zh-tw' WHERE lower(locale) = 'zh-tw' AND locale <> 'zh-tw'"
        )


def downgrade() -> None:
    # Irreversible by design: we don't know which rows were originally 'zh-TW'.
    pass
