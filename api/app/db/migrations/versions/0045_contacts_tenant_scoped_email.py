"""Contacts: email uniqueness scoped to (tenant_id, email)

Revision ID: 0045_contacts_tenant_scoped_email
Revises: 0044_add_page_brief_agent_fields
Create Date: 2026-08-03

Multi-tenant isolation (T2): different tenants must be able to hold the
same email address. Replaces the global unique constraint uq_contacts_email
with a composite (tenant_id, email) constraint. Rows with tenant_id IS NULL
remain mutually non-conflicting under Postgres NULL semantics, and dedup
queries match them with `tenant_id IS NULL`.
"""
from alembic import op

revision = "0045_contacts_tenant_scoped_email"
down_revision = "0044_add_page_brief_agent_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_contacts_email", "contacts", type_="unique")
    op.create_unique_constraint(
        "uq_contacts_tenant_email", "contacts", ["tenant_id", "email"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_contacts_tenant_email", "contacts", type_="unique")
    op.create_unique_constraint("uq_contacts_email", "contacts", ["email"])
