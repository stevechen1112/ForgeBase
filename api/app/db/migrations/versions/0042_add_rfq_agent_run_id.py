"""Add agent_run_id to rfq_requests (Condition 1: auto-trigger)

Revision ID: 0042_add_rfq_agent_run_id
Revises: 0041_ai_generation_log_audit_fields
Create Date: 2026-04-26 09:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0042_add_rfq_agent_run_id'
down_revision = '0041_ai_generation_log_audit_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('rfq_requests', sa.Column('agent_run_id', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_rfq_requests_agent_run_id'), 'rfq_requests', ['agent_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rfq_requests_agent_run_id'), table_name='rfq_requests')
    op.drop_column('rfq_requests', 'agent_run_id')
