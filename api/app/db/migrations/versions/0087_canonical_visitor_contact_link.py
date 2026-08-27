"""Use visitors.contact_id as the canonical identity link.

Revision ID: 0087_canonical_visitor_contact_link
Revises: 0086_retirement_observability
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0087_canonical_visitor_contact_link"
down_revision = "0086_retirement_observability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve every unambiguous legacy link. Existing visitor-side identity
    # wins if the two historical columns disagree.
    op.execute(
        """
        UPDATE visitors AS v
        SET contact_id = c.id
        FROM contacts AS c
        WHERE c.visitor_id = v.visitor_id
          AND v.contact_id IS NULL
          AND (c.tenant_id IS NULL OR v.tenant_id IS NULL OR c.tenant_id = v.tenant_id)
        """
    )
    op.drop_index("ix_contacts_visitor_id", table_name="contacts")
    op.drop_constraint("fk_contacts_visitor_id", "contacts", type_="foreignkey")
    op.drop_column("contacts", "visitor_id")


def downgrade() -> None:
    op.add_column(
        "contacts",
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_contacts_visitor_id",
        "contacts",
        "visitors",
        ["visitor_id"],
        ["visitor_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_contacts_visitor_id", "contacts", ["visitor_id"])
    # The old schema could represent only one visitor per contact. Choose the
    # earliest known visitor deterministically when rolling back.
    op.execute(
        """
        UPDATE contacts AS c
        SET visitor_id = linked.visitor_id
        FROM (
            SELECT DISTINCT ON (contact_id) contact_id, visitor_id
            FROM visitors
            WHERE contact_id IS NOT NULL
            ORDER BY contact_id, first_seen ASC, visitor_id ASC
        ) AS linked
        WHERE linked.contact_id = c.id
        """
    )
