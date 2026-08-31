"""Remove retired Copilot, ML scoring, and generic integration storage.

Revision ID: 0100_remove_copilot_ml_integrations
Revises: 0099_managed_tenant_subdomains
"""

import sqlalchemy as sa
from alembic import op

revision = "0100_remove_copilot_ml_integrations"
down_revision = "0099_managed_tenant_subdomains"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These retirement-ledger entries describe code that is no longer part of
    # the product. Usage events are removed by the ledger FK's ON DELETE CASCADE.
    op.execute(
        """
        DELETE FROM retirement_candidate_observations
        WHERE candidate_key IN ('ml_scoring_runtime', 'copilot_floating_widget')
        """
    )

    op.drop_table("copilot_run_logs")
    op.drop_table("copilot_conversations")
    op.drop_table("integration_credentials")
    op.drop_column("visitors", "ml_score_updated_at")
    op.drop_column("visitors", "ml_intent_score")


def downgrade() -> None:
    op.add_column("visitors", sa.Column("ml_intent_score", sa.Float(), nullable=True))
    op.add_column(
        "visitors",
        sa.Column("ml_score_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("credential_key", sa.String(), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "service", "credential_key", name="uq_integration_credential"
        ),
    )
    op.create_index(
        "ix_integration_credentials_tenant_id", "integration_credentials", ["tenant_id"]
    )
    op.create_index(
        "ix_integration_credentials_service", "integration_credentials", ["service"]
    )

    op.create_table(
        "copilot_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("channel_user_id", sa.String(200), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_copilot_conversations_user_id", "copilot_conversations", ["user_id"]
    )
    op.create_index(
        "ix_copilot_conversations_channel_user_id",
        "copilot_conversations",
        ["channel_user_id"],
    )

    op.create_table(
        "copilot_run_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tool_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_names", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("had_error", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copilot_run_logs_tenant_id", "copilot_run_logs", ["tenant_id"])
    op.create_index("ix_copilot_run_logs_created_at", "copilot_run_logs", ["created_at"])

    op.execute(
        """
        INSERT INTO retirement_candidate_observations (
            candidate_key, display_name, required_observation_days, code_state,
            status, started_at, decision_reason, updated_at
        ) VALUES
            ('ml_scoring_runtime', 'ML scoring 線上 runtime／UI', 30, 'disabled',
             'observing', TIMEZONE('utc', NOW()), NULL, TIMEZONE('utc', NOW())),
            ('copilot_floating_widget', '重複 Copilot floating widget', 0, 'removed',
             'removed', TIMEZONE('utc', NOW()),
             'Restored by downgrade of retired feature removal.', TIMEZONE('utc', NOW()))
        ON CONFLICT (candidate_key) DO NOTHING
        """
    )
