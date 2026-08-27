"""Safe-retirement observation windows and PII-free usage evidence.

Revision ID: 0086_retirement_observability
Revises: 0085_closed_loop_attribution
"""

import sqlalchemy as sa
from alembic import op

revision = "0086_retirement_observability"
down_revision = "0085_closed_loop_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retirement_candidate_observations",
        sa.Column("candidate_key", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column(
            "required_observation_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "code_state",
            sa.String(length=20),
            nullable=False,
            server_default="disabled",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="observing",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("TIMEZONE('utc', NOW())"),
        ),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decision_reason", sa.String(length=2000), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("TIMEZONE('utc', NOW())"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("candidate_key"),
        sa.CheckConstraint(
            "status IN ('observing', 'retained', 'approved_removal', 'removed')",
            name="ck_retirement_candidate_status",
        ),
        sa.CheckConstraint(
            "code_state IN ('active', 'disabled', 'removed')",
            name="ck_retirement_candidate_code_state",
        ),
        sa.CheckConstraint(
            "required_observation_days >= 0",
            name="ck_retirement_candidate_days",
        ),
    )
    for column in ("code_state", "status", "started_at", "decided_by", "updated_at"):
        op.create_index(
            f"ix_retirement_candidate_observations_{column}",
            "retirement_candidate_observations",
            [column],
        )

    op.create_table(
        "retirement_usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_key", sa.String(length=80), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("TIMEZONE('utc', NOW())"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_key"],
            ["retirement_candidate_observations.candidate_key"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "candidate_key",
        "tenant_id",
        "event_name",
        "occurred_at",
    ):
        op.create_index(
            f"ix_retirement_usage_events_{column}",
            "retirement_usage_events",
            [column],
        )

    observations = sa.table(
        "retirement_candidate_observations",
        sa.column("candidate_key", sa.String),
        sa.column("display_name", sa.String),
        sa.column("required_observation_days", sa.Integer),
        sa.column("code_state", sa.String),
        sa.column("status", sa.String),
        sa.column("decision_reason", sa.String),
    )
    op.bulk_insert(
        observations,
        [
            {
                "candidate_key": "agentos_runtime",
                "display_name": "AgentOS／automation runtime",
                "required_observation_days": 30,
                "code_state": "disabled",
                "status": "observing",
                "decision_reason": None,
            },
            {
                "candidate_key": "ml_scoring_runtime",
                "display_name": "ML scoring 線上 runtime／UI",
                "required_observation_days": 30,
                "code_state": "disabled",
                "status": "observing",
                "decision_reason": None,
            },
            {
                "candidate_key": "notification_telegram",
                "display_name": "Telegram 通知渠道",
                "required_observation_days": 60,
                "code_state": "active",
                "status": "observing",
                "decision_reason": None,
            },
            {
                "candidate_key": "notification_line",
                "display_name": "LINE 通知渠道",
                "required_observation_days": 60,
                "code_state": "active",
                "status": "observing",
                "decision_reason": None,
            },
            {
                "candidate_key": "relation_recommender",
                "display_name": "AI relation 推薦介面",
                "required_observation_days": 60,
                "code_state": "disabled",
                "status": "observing",
                "decision_reason": None,
            },
            {
                "candidate_key": "copilot_floating_widget",
                "display_name": "重複 Copilot floating widget",
                "required_observation_days": 0,
                "code_state": "removed",
                "status": "removed",
                "decision_reason": "Static dependency audit found no imports or bundle entry; dedicated Copilot page remains.",
            },
            {
                "candidate_key": "legacy_ip_resolver",
                "display_name": "不安全且未接線的舊 IP resolver",
                "required_observation_days": 0,
                "code_state": "removed",
                "status": "removed",
                "decision_reason": "Static dependency audit found no caller; trusted NetworkObservation provider path replaced it.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("retirement_usage_events")
    op.drop_table("retirement_candidate_observations")
