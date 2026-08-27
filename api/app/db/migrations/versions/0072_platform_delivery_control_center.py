"""Platform delivery control-center fields.

Revision ID: 0072_platform_delivery_control_center
Revises: 0071_adoption_applications
"""

import sqlalchemy as sa
from alembic import op

revision = "0072_platform_delivery_control_center"
down_revision = "0071_adoption_applications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_builds",
        sa.Column("delivery_stage", sa.String(30), nullable=False, server_default="intake"),
    )
    op.add_column(
        "site_builds",
        sa.Column("delivery_owner_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_site_builds_delivery_owner_id_users",
        "site_builds",
        "users",
        ["delivery_owner_id"],
        ["id"],
    )
    op.add_column("site_builds", sa.Column("target_launch_at", sa.DateTime(), nullable=True))
    op.add_column("site_builds", sa.Column("handoff_at", sa.DateTime(), nullable=True))
    op.add_column(
        "site_builds",
        sa.Column("acceptance_status", sa.String(30), nullable=False, server_default="pending"),
    )
    op.add_column("site_builds", sa.Column("internal_note", sa.String(4000), nullable=True))
    op.create_index("ix_site_builds_delivery_stage", "site_builds", ["delivery_stage"])
    op.create_index("ix_site_builds_delivery_owner_id", "site_builds", ["delivery_owner_id"])
    op.create_index("ix_site_builds_target_launch_at", "site_builds", ["target_launch_at"])
    op.create_index("ix_site_builds_acceptance_status", "site_builds", ["acceptance_status"])


def downgrade() -> None:
    op.drop_index("ix_site_builds_acceptance_status", table_name="site_builds")
    op.drop_index("ix_site_builds_target_launch_at", table_name="site_builds")
    op.drop_index("ix_site_builds_delivery_owner_id", table_name="site_builds")
    op.drop_index("ix_site_builds_delivery_stage", table_name="site_builds")
    op.drop_constraint("fk_site_builds_delivery_owner_id_users", "site_builds", type_="foreignkey")
    op.drop_column("site_builds", "internal_note")
    op.drop_column("site_builds", "acceptance_status")
    op.drop_column("site_builds", "handoff_at")
    op.drop_column("site_builds", "target_launch_at")
    op.drop_column("site_builds", "delivery_owner_id")
    op.drop_column("site_builds", "delivery_stage")
