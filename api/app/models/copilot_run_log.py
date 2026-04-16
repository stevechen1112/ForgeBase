import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

from app.core.datetime import utcnow_naive


class CopilotRunLog(SQLModel, table=True):
    """
    One row per Copilot AI run (one user message → one assistant reply).
    Provides lightweight observability: tool hit rate, error rate, latency.
    """
    __tablename__ = "copilot_run_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tenants.id", index=True
    )
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    channel: str = Field(max_length=20)         # 'web' | 'telegram'
    llm_calls: int = Field(default=1)            # how many LLM round-trips in this run
    tool_count: int = Field(default=0)           # number of tool calls executed
    tool_names: Optional[str] = Field(default=None)  # JSON array of tool name strings
    duration_ms: int = Field(default=0)          # wall-clock time of run() in ms
    had_error: bool = Field(default=False)       # True when reply was a fallback/error message
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
