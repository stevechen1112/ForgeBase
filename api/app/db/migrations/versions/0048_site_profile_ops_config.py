"""SiteProfile: ops_config_json for per-tenant ops settings

Revision ID: 0048_site_profile_ops_config
Revises: 0047_rfq_sla_fields
Create Date: 2026-08-03

單一 JSON 欄位承載 per-tenant 營運設定，避免每個開關都加欄位：
  {
    "sla_response_hours": 4,          // T7 首回 SLA 目標（買家工作小時）
    "auto_reply_enabled": false,      // T6 自動專業確認信開關（預設關）
    "auto_reply_signature": "...",    // T6 簽名檔（純文字）
    "auto_reply_from_name": "..."     // T6 寄件人顯示名稱
  }
"""
from alembic import op
import sqlalchemy as sa


revision = "0048_site_profile_ops_config"
down_revision = "0047_rfq_sla_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_profiles", sa.Column("ops_config_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("site_profiles", "ops_config_json")
