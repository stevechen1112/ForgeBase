"""Enforce evidence, data disposition, and rollback before retirement approval.

Revision ID: 0095_retirement_governance_gate
Revises: 0094_slo_incident_console
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0095_retirement_governance_gate"
down_revision = "0094_slo_incident_console"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "retirement_candidate_observations",
        sa.Column("telemetry_verified_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "retirement_candidate_observations",
        sa.Column("telemetry_verified_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "retirement_candidate_observations",
        sa.Column("telemetry_evidence_ref", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "retirement_candidate_observations",
        sa.Column("data_disposition", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "retirement_candidate_observations",
        sa.Column("rollback_revision", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "retirement_candidate_observations",
        sa.Column("removal_plan_ref", sa.String(length=500), nullable=True),
    )
    op.create_foreign_key(
        "fk_retirement_candidate_telemetry_verified_by",
        "retirement_candidate_observations",
        "users",
        ["telemetry_verified_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_retirement_candidate_data_disposition",
        "retirement_candidate_observations",
        "data_disposition IS NULL OR data_disposition IN "
        "('not_applicable', 'retained', 'exported', 'deleted')",
    )
    op.create_index(
        "ix_retirement_candidate_observations_telemetry_verified_by",
        "retirement_candidate_observations",
        ["telemetry_verified_by"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retirement_candidate_observations_telemetry_verified_by",
        table_name="retirement_candidate_observations",
    )
    op.drop_constraint(
        "ck_retirement_candidate_data_disposition",
        "retirement_candidate_observations",
        type_="check",
    )
    op.drop_constraint(
        "fk_retirement_candidate_telemetry_verified_by",
        "retirement_candidate_observations",
        type_="foreignkey",
    )
    for column in (
        "removal_plan_ref",
        "rollback_revision",
        "data_disposition",
        "telemetry_evidence_ref",
        "telemetry_verified_by",
        "telemetry_verified_at",
    ):
        op.drop_column("retirement_candidate_observations", column)
