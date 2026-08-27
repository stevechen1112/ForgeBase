"""Alembic migration 0015 — add persisted slug to certifications

- certifications: add slug, backfill existing rows, enforce unique index
"""
import re
import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "0015_certification_slug"
down_revision = "0014_phase3_ml_scoring"
branch_labels = None
depends_on = None


def _to_slug(text: str) -> str:
    """Minimal slug helper — no external deps, safe for use in migrations."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "certification"


def _build_unique_slug(name: str, seen: set[str]) -> str:
    base = _to_slug(name)[:110] or "certification"
    candidate = base
    counter = 2
    while candidate in seen:
        suffix = f"-{counter}"
        candidate = f"{base[:120 - len(suffix)]}{suffix}"
        counter += 1
    seen.add(candidate)
    return candidate


def upgrade() -> None:
    op.add_column("certifications", sa.Column("slug", sa.String(length=120), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, cert_name FROM certifications ORDER BY created_at, id")).fetchall()
    seen: set[str] = set()

    for row in rows:
        slug = _build_unique_slug(row.cert_name, seen)
        bind.execute(
            sa.text("UPDATE certifications SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": row.id},
        )

    op.alter_column("certifications", "slug", existing_type=sa.String(length=120), nullable=False)
    op.create_index("ix_certifications_slug", "certifications", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_certifications_slug", table_name="certifications")
    op.drop_column("certifications", "slug")
