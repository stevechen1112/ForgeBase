"""Add agent_analysis_summary and agent_draft_body to rfq_requests (Condition 4: writeback)

Revision ID: 0043_add_rfq_agent_draft_fields
Revises: 0042_add_rfq_agent_run_id
Create Date: 2026-04-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0043_add_rfq_agent_draft_fields'
down_revision = '0042_add_rfq_agent_run_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('rfq_requests', sa.Column('agent_analysis_summary', sa.String(length=2000), nullable=True))
    op.add_column('rfq_requests', sa.Column('agent_draft_body', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('rfq_requests', 'agent_draft_body')
    op.drop_column('rfq_requests', 'agent_analysis_summary')
