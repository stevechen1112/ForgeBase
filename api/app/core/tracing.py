"""
ForgeBase AI Tracing — Langfuse self-hosted integration wrapper

Provides a traced AsyncOpenAI client and workflow-span utilities that are
fully backward-compatible: when Langfuse is not configured, everything
degrades to plain OpenAI calls with zero overhead.

Phases of adoption
──────────────────
Phase 1 (start here):
  - Replace `AsyncOpenAI(api_key=settings.OPENAI_API_KEY)` with
    `get_openai_client()` in each AI service module.
  - Decorate each service entry-point with `@observe_workflow(name=WorkflowType.X)`.
  - Call `attach_trace_metadata(...)` at the top of each observed function.
  Result: every LLM call is captured as a span; traces are grouped by workflow,
  tenant, and session without touching OpenAI call signatures.

Phase 2 (next):
  - Pull prompt templates into Langfuse Prompt Management.
  - Add LLM-as-judge eval scorers on production traces.

Phase 3 (later):
  - Build datasets from production traces for offline regression testing.
  - Add online prompt experiments tied to tenant cohorts.

PII guarantee
─────────────
All prompt and completion text is passed through `_mask_fn` by the Langfuse
SDK *before* the data is written to ClickHouse. Email addresses and phone
numbers are replaced with [EMAIL_REDACTED] / [PHONE_REDACTED] at the SDK
masking layer. This means PII never reaches persistent storage even if a
service accidentally includes it in a prompt.

ForgeBase metadata schema
──────────────────────────
Required per trace:
  tenant_id   — UUID string; isolates traces per tenant in Langfuse UI
  workflow    — one of WorkflowType.*; groups traces by AI capability

Optional per trace:
  session_id  — chat_session_id / intake_project_id / rfq_id / visitor_id
  user_id     — authenticated user_id or visitor_id (for user-level analytics)

Extra metadata (free-form, passed via `extra` param):
  route           — e.g. "POST /api/v1/chat"
  model_override  — when a workflow uses a non-default model
  fallback_used   — True/False
  error_type      — classification on failure spans
"""

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── PII redaction ──────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
)
# Conservative phone pattern: starts/ends with digit, 7–20 chars total
_PHONE_RE = re.compile(
    r'\+?[0-9][\d\s\-().]{5,18}[0-9]'
)


def _redact_text(text: str) -> str:
    """Replace email addresses and phone numbers with redaction placeholders."""
    if not isinstance(text, str) or not text:
        return text
    text = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    text = _PHONE_RE.sub("[PHONE_REDACTED]", text)
    return text


def _redact_messages(messages: list) -> list:
    """Redact PII from an OpenAI-style messages list in-place structures."""
    result = []
    for msg in messages:
        if not isinstance(msg, dict):
            result.append(msg)
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            result.append({**msg, "content": _redact_text(content)})
        elif isinstance(content, list):
            # Multi-modal content — only redact text parts
            parts = [
                {**p, "text": _redact_text(p.get("text", ""))}
                if isinstance(p, dict) and p.get("type") == "text"
                else p
                for p in content
            ]
            result.append({**msg, "content": parts})
        else:
            result.append(msg)
    return result


def _mask_fn(data: Any) -> Any:
    """
    Langfuse SDK mask callback.

    Called by the SDK before persisting each observation to ClickHouse.
    Receives the raw observation dict and must return the (possibly modified) dict.
    Redacts PII from prompt inputs and completion outputs.
    """
    if not isinstance(data, dict):
        return data

    # Input — typically {"messages": [...]} for chat completions
    if "input" in data:
        inp = data["input"]
        if isinstance(inp, dict) and "messages" in inp:
            data = {
                **data,
                "input": {**inp, "messages": _redact_messages(inp["messages"])},
            }
        elif isinstance(inp, str):
            data = {**data, "input": _redact_text(inp)}

    # Output — typically a string or choices structure
    if "output" in data:
        out = data["output"]
        if isinstance(out, str):
            data = {**data, "output": _redact_text(out)}

    return data


# ── Langfuse initialisation ────────────────────────────────────────────────────

_langfuse_enabled: bool = bool(
    getattr(settings, "LANGFUSE_SECRET_KEY", None)
    and getattr(settings, "LANGFUSE_HOST", None)
)

# Assigned below if init succeeds; remains None as fallback otherwise.
_TracedAsyncOpenAI: type | None = None

if _langfuse_enabled:
    try:
        from langfuse import Langfuse
        from langfuse.openai import AsyncOpenAI as _T

        _TracedAsyncOpenAI = _T

        # Instantiate singleton — registers global masking config and flushes
        # any buffered traces on process exit.
        Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_HOST,
            mask=_mask_fn,
        )
        logger.info("Langfuse tracing enabled → %s", settings.LANGFUSE_HOST)

    except ImportError:
        _langfuse_enabled = False
        logger.warning(
            "langfuse package not installed — tracing disabled. "
            "Add `langfuse` to requirements.txt and reinstall."
        )
    except Exception:
        _langfuse_enabled = False
        logger.exception(
            "Langfuse initialisation failed — tracing disabled. "
            "Check LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST in .env."
        )
else:
    logger.debug(
        "Langfuse tracing disabled — "
        "set LANGFUSE_SECRET_KEY and LANGFUSE_HOST in api/.env to enable."
    )


# ── Workflow type constants ────────────────────────────────────────────────────

class WorkflowType:
    """
    Canonical names for ForgeBase AI workflows.
    Used as the Langfuse trace name — appears in the Langfuse UI as the top-level
    label for each trace group. Keep these stable; changing them breaks historical
    filtering in the dashboard.
    """

    CHAT               = "chat"
    INTAKE             = "intake"
    AI_RFQ_ANALYZE     = "ai_rfq_analyze"
    AI_RFQ_REPLY       = "ai_rfq_reply"
    AI_RECOMMEND       = "ai_recommend"
    AI_ENGINE          = "ai_engine"
    CONTENT_OPTIMIZE   = "content_optimize"
    RELATION_RECOMMEND = "relation_recommend"
    SEO_OPTIMIZE       = "seo_optimize"


# ── Public API ─────────────────────────────────────────────────────────────────

def get_openai_client(api_key: str | None = None):
    """
    Return an AsyncOpenAI client, traced or plain depending on configuration.

    When Langfuse is running, returns a `langfuse.openai.AsyncOpenAI` instance
    which automatically captures every `.chat.completions.create()` call as a
    Langfuse observation span — no changes needed at call sites.

    When Langfuse is not configured (or the package is missing), returns a
    plain `openai.AsyncOpenAI` with identical interface.

    Migration guide — change each AI service module from:

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    to:

        from app.core.tracing import get_openai_client
        client = get_openai_client()

    Priority order for Phase 1:
        1. chat_service.py
        2. ai_rfq.py
        3. ai_recommend.py
        4. intake_engine.py
        5. ai_engine.py, content_optimizer.py, relation_recommender.py
        6. seo_optimize.py (endpoint-level)
    """
    key = api_key or settings.OPENAI_API_KEY
    if _langfuse_enabled and _TracedAsyncOpenAI is not None:
        return _TracedAsyncOpenAI(api_key=key)
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=key)


def attach_trace_metadata(
    *,
    workflow: str,
    tenant_id: str,
    session_id: str | None = None,
    user_id: str | None = None,
    extra: dict | None = None,
) -> None:
    """
    Enrich the current Langfuse trace with ForgeBase-standard metadata.

    Must be called from *inside* a function decorated with @observe_workflow,
    or from within another @observe()-decorated context. When called outside
    such a context, or when Langfuse is disabled, this is a no-op.

    Args:
        workflow:   One of WorkflowType.* — sets the trace name in Langfuse UI.
        tenant_id:  Tenant UUID as string — used to scope traces per customer.
        session_id: Optional session identifier:
                      chat      → str(chat_session_id)
                      intake    → str(project_id)
                      ai_rfq    → str(rfq_id)
                      recommend → str(visitor_id)
        user_id:    Optional — authenticated user_id or visitor_id.
        extra:      Additional free-form metadata dict.

    Example:
        @observe_workflow(name=WorkflowType.CHAT)
        async def generate_reply(session: ChatSession, tenant_id: uuid.UUID, ...):
            attach_trace_metadata(
                workflow=WorkflowType.CHAT,
                tenant_id=str(tenant_id),
                session_id=str(session.id),
                user_id=str(session.visitor_id) if session.visitor_id else None,
            )
            client = get_openai_client()
            ...
    """
    if not _langfuse_enabled:
        return
    try:
        from langfuse.decorators import langfuse_context
        langfuse_context.update_current_trace(
            name=workflow,
            session_id=session_id,
            user_id=user_id,
            metadata={"tenant_id": tenant_id, **(extra or {})},
            tags=[f"tenant:{tenant_id}", f"workflow:{workflow}"],
        )
    except Exception:
        # Never let observability failure affect the main request path.
        logger.debug("attach_trace_metadata failed — non-critical.", exc_info=True)


def observe_workflow(name: str, **kwargs):
    """
    Decorator factory for workflow-level trace spans.

    When Langfuse is enabled, wraps the decorated async function with a
    Langfuse `@observe(name=...)` span. All nested OpenAI calls made via
    `get_openai_client()` become child spans automatically.

    When Langfuse is not configured, returns the original function unchanged.

    Usage:
        from app.core.tracing import observe_workflow, WorkflowType

        @observe_workflow(name=WorkflowType.AI_RFQ_ANALYZE)
        async def analyze_rfq(rfq_data: dict, products: list, ...) -> dict:
            attach_trace_metadata(
                workflow=WorkflowType.AI_RFQ_ANALYZE,
                tenant_id=str(tenant_id),
                session_id=str(rfq_id),
            )
            client = get_openai_client()
            response = await client.chat.completions.create(...)
            ...
    """
    if _langfuse_enabled:
        try:
            from langfuse.decorators import observe
            return observe(name=name, **kwargs)
        except Exception:
            logger.debug("observe_workflow decorator unavailable.", exc_info=True)

    def _passthrough(fn):
        return fn

    return _passthrough
