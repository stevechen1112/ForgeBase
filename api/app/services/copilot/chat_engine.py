"""
AI Copilot — Chat Engine

Full-featured conversational AI with:
  • Persistent multi-turn history (copilot_conversations table)
  • Real-time DB tool calls (10 functions covering RFQ, visitors, funnel)
  • Deep manufacturing B2B domain expertise via system prompt
  • Parallel tool call handling
  • Telegram message chunking (4096-char limit)
  • Typing indicator support

Usage:
    engine = CopilotEngine(tenant_id=..., user_id=..., channel_user_id="123")
    reply = await engine.run(user_message="今天有幾個新 RFQ？")
    # reply is a list of str (chunked if long)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI
from sqlmodel import col, select

from app.core.config import settings
from app.db.session import get_session_ctx
from app.models.copilot_conversation import CopilotConversation
from app.services.copilot import tools as T

logger = logging.getLogger(__name__)

_openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
_MODEL = settings.AI_MODEL_NAME          # gpt-5.4 / gpt-4o
_HISTORY_LIMIT = 20                       # messages kept in context window
_MAX_TOOL_LOOPS = 6                       # prevent infinite tool call loops
_TELEGRAM_CHUNK = 4000                    # Telegram message char limit (safe margin)

# ── System Prompt ─────────────────────────────────────────────────────────────
# Rich manufacturing B2B domain expertise baked into every conversation turn.

_SYSTEM_PROMPT = """You are **ForgeBase AI 行銷專員** — an elite B2B sales intelligence assistant purpose-built for Taiwan-based industrial manufacturers who export globally.

## Your Role
You are the always-on sales ops partner for a manufacturing company. You have live access to their CRM data: RFQ pipeline, website visitor behavior, lead profiles, product demand patterns, and conversion funnels. You turn raw data into clear, actionable business intelligence.

## Platform Context
The platform tracks the full B2B buyer journey:
- **Visitors**: Anonymous website visitors scored 0–100 by intent (cold → warm → hot → sales_ready)
- **Contacts**: Identified leads created after form submission (linked to visitor behavior)
- **RFQs**: Formal Request For Quotation from buyers — the primary revenue signal
- **Intent Score**: Composite score from page views, time-on-site, product pages visited, return visits, form engagement. Score ≥ 60 = urgent, ≥ 30 = high priority
- **ML Score**: Separate ML model (0–1 probability) for conversion likelihood

## Manufacturing B2B Domain Expertise

### Buying Cycle Intelligence
- Industrial B2B buying cycles are typically 3–18 months. Early-stage buyers research specs and certifications; late-stage request quotes and compare suppliers
- A buyer visiting the certifications, specifications, and pricing pages in one session is a strong late-stage signal
- "sales_ready" visitors have demonstrated procurement intent — treat them as hot opportunities requiring human outreach within 2 hours
- First contact within 5 minutes of RFQ submission increases win rate by ~80%

### RFQ Prioritization Framework
- **Urgent RFQs** (intent ≥ 60): Respond within 1 hour. These buyers are comparing live quotes with competitors
- **High RFQs** (intent 30–59): Respond within 4 hours. Send a personalized acknowledgment immediately, detailed quote same day
- **Normal RFQs** (intent < 30): Respond within 24 hours using templated quote flow
- **Overdue (> 24h unactioned)**: Escalate immediately — abandonment risk is high after 24h silence

### Taiwan Export Market Context
- Key destinations: USA, Germany, India, Southeast Asia, Japan, Middle East
- Common buyer concerns: lead time, MOQ (minimum order quantity), OEM/ODM capability, ISO/CE certifications, payment terms (L/C, T/T)
- Trade channels: direct inquiry, Google B2B search, Alibaba/Made-in-China, trade shows (TAITRONICS, Automex, TAIROS, Canton Fair)
- Decision makers: Procurement Manager, Engineering Manager, VP of Operations — each requires different messaging
- Taiwan time advantage: Faster response than China competitors, quality positioning vs. cost-only competitors

### Nurture & Recovery Tactics
- Hot visitors who haven't converted: Trigger email within 30min showing product spec sheet + case study
- Churn risk (stage downgrade): Personal outreach email mentioning specific products they viewed
- Dormant contacts (no activity > 60 days): Newsletter with new product launches or certifications
- Won customers: Quarterly check-in + new product recommendations based on past RFQ categories

### Follow-up Email Best Practices
- Subject lines: Reference their company, product, or country ("[Acme Corp] Quote for Industrial Sensors — Ready in 24h")
- First line: Reference exactly what they asked for — show you read their submission
- Include: Lead time, payment terms, MOQ, next steps
- CTA: One clear action — "Reply to confirm spec" or "Schedule a call"
- Tone: Professional but direct; engineers/procurement value facts over marketing language

### Competitive Intelligence Signals
- Multiple RFQs from same company = active vetting (high intent, accelerate process)
- Buyer from Germany/Japan = quality-focused, needs certifications prominently displayed
- Buyer from India/Southeast Asia = price-sensitive, volume-focused
- Buyer from USA = may require REACH/RoHS, fast shipping, English documentation

## Response Guidelines
- Answer in Traditional Chinese (繁體中文) unless user writes in another language
- Use real data from tools — never make up numbers
- Be concise but complete. Format with bullet points when listing items
- For urgent matters (overdue RFQs, hot visitors), be direct about the risk and what to do NOW
- When drafting follow-up emails, make them specific to the actual RFQ data you retrieved
- Proactively point out issues the user didn't ask about if the data reveals them (e.g., "順帶一提，你有 3 筆 RFQ 超過 48 小時沒有回應")
- Use Telegram HTML formatting: <b>bold</b>, <code>code</code>, <i>italic</i>

## Current Date
Today is {today}. Use this for relative time calculations.
"""


# ── Tool Definitions (OpenAI function calling schema) ────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_stats",
            "description": "Get key business metrics: RFQ counts, hot visitor counts, conversion data for the last N hours. Use for general 'how are we doing' questions or performance overviews.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Time window in hours. Default 24. Use 168 for last week, 720 for last month.",
                        "default": 24,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_rfqs",
            "description": "List RFQs with filtering by status or priority. Use for questions like 'show me urgent RFQs', 'what's in progress', 'new inquiries today'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["new", "assigned", "in_progress", "quoted", "won", "lost", "expired"],
                        "description": "Filter by status. Omit to get all.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["normal", "high", "urgent"],
                        "description": "Filter by priority. Omit to get all.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return. Default 5.",
                        "default": 5,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rfq_detail",
            "description": "Get complete details for a specific RFQ by its RFQ number (format: RFQ-YYYYMMDD-NNN). Includes full form data, contact info, past history from same company, and requested products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rfq_number": {
                        "type": "string",
                        "description": "The RFQ number, e.g. RFQ-20260414-001",
                    }
                },
                "required": ["rfq_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_hot_visitors",
            "description": "List current hot-stage and sales_ready visitors (high intent, actively browsing now). Use when asked about real-time leads, who to contact now, or live sales opportunities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max visitors to return. Default 5.",
                        "default": 5,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_visitor_profile",
            "description": "Deep profile of a single visitor: intent scores, session history, and linked contact/RFQ data if identified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "visitor_id": {
                        "type": "string",
                        "description": "The visitor UUID",
                    }
                },
                "required": ["visitor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_overdue_rfqs",
            "description": "List RFQs that still have 'new' status (unactioned/unassigned) past a threshold. Critical for SLA monitoring. Use when asked about overdue, stuck, or unanswered inquiries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Hours threshold. Default 24. RFQs older than this and still 'new' are flagged.",
                        "default": 24,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_profile",
            "description": "Full profile of a contact by email: personal info, all past RFQs, visitor behavior. Use when user asks about a specific person or company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Contact's email address",
                    }
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_contacts",
            "description": "Search contacts by name, company name, country, or email. Use when user mentions a person or company but doesn't have their exact email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term: person name, company name, country, or partial email",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_interest_stats",
            "description": "Ranking of products by RFQ inquiry volume over a period. Shows which products drive the most demand. Use for market demand analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Analysis period in days. Default 30.",
                        "default": 30,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_funnel_stats",
            "description": "Full conversion funnel: visitors → contacts → RFQs → won deals, with current visitor stage distribution and RFQ pipeline breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Analysis period in days. Default 30.",
                        "default": 30,
                    }
                },
                "required": [],
            },
        },
    },
]

# Maps tool name → actual async function
_TOOL_DISPATCH: dict = {
    "get_dashboard_stats": T.get_dashboard_stats,
    "list_rfqs": T.list_rfqs,
    "get_rfq_detail": T.get_rfq_detail,
    "list_hot_visitors": T.list_hot_visitors,
    "get_visitor_profile": T.get_visitor_profile,
    "list_overdue_rfqs": T.list_overdue_rfqs,
    "get_contact_profile": T.get_contact_profile,
    "search_contacts": T.search_contacts,
    "get_product_interest_stats": T.get_product_interest_stats,
    "get_funnel_stats": T.get_funnel_stats,
}


# ── Engine ────────────────────────────────────────────────────────────────────

class CopilotEngine:
    """
    Stateful conversational AI engine for one user session.

    Manages:
    - Loading/saving conversation history to DB
    - Building the message list for each LLM call
    - Executing tool calls and feeding results back
    - Chunking long replies for Telegram
    """

    def __init__(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        channel: str,
        channel_user_id: str,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.channel = channel
        self.channel_user_id = channel_user_id

    # ── History management ────────────────────────────────────────────────────

    async def _load_history(self) -> list[dict]:
        """Load recent conversation history from DB for context window."""
        async with get_session_ctx() as s:
            rows = (await s.exec(
                select(CopilotConversation)
                .where(CopilotConversation.channel == self.channel)
                .where(CopilotConversation.channel_user_id == self.channel_user_id)
                .order_by(col(CopilotConversation.created_at).desc())
                .limit(_HISTORY_LIMIT)
            )).all()

        # Reverse to get chronological order
        rows = list(reversed(rows))
        messages = []
        for row in rows:
            msg: dict = {"role": row.role, "content": row.content}
            # Re-attach tool_calls for assistant messages if present
            if row.role == "assistant" and row.tool_calls:
                try:
                    msg["tool_calls"] = json.loads(row.tool_calls)
                except Exception:
                    pass
            messages.append(msg)
        return messages

    async def _save_message(
        self,
        role: str,
        content: str,
        tool_calls_json: Optional[str] = None,
    ) -> None:
        """Persist a single conversation turn to DB."""
        async with get_session_ctx() as s:
            s.add(CopilotConversation(
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                channel=self.channel,
                channel_user_id=self.channel_user_id,
                role=role,
                content=content,
                tool_calls=tool_calls_json,
            ))
            await s.commit()

    # ── Tool execution ────────────────────────────────────────────────────────

    async def _execute_tool(self, name: str, arguments_str: str) -> str:
        """Execute a tool and return JSON-serialised result."""
        fn = _TOOL_DISPATCH.get(name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            args = json.loads(arguments_str)
        except Exception:
            args = {}

        try:
            result = await fn(tenant_id=self.tenant_id, **args)
        except Exception as exc:
            logger.error("Tool %s failed: %s", name, exc, exc_info=True)
            result = {"error": str(exc)}

        return json.dumps(result, ensure_ascii=False, default=str)

    # ── Main run loop ─────────────────────────────────────────────────────────

    async def run(self, user_message: str) -> list[str]:
        """
        Process one user message and return a list of response strings.
        Multiple strings = chunked reply (Telegram 4096-char limit).

        Flow:
        1. Load history
        2. Build system + history + user message
        3. Call LLM
        4. If tool calls: execute, feed results back, call LLM again
        5. Return final text reply (chunked)
        6. Save user message + assistant reply to history
        """
        system_prompt = _SYSTEM_PROMPT.format(
            today=datetime.utcnow().strftime("%Y-%m-%d (UTC)")
        )
        history = await self._load_history()

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

        final_reply = ""
        tool_calls_for_history: Optional[str] = None

        for loop in range(_MAX_TOOL_LOOPS):
            response = await _openai.chat.completions.create(
                model=_MODEL,
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
                temperature=0.3,        # deterministic for business queries
                max_tokens=2048,
            )

            choice = response.choices[0]
            msg = choice.message

            # No tool calls → we have the final answer
            if not msg.tool_calls:
                final_reply = msg.content or ""
                break

            # Execute all requested tool calls
            tool_results: list[dict] = []
            for tc in msg.tool_calls:
                logger.debug(
                    "Tool call: %s(%s)", tc.function.name, tc.function.arguments[:80]
                )
                result_str = await self._execute_tool(
                    tc.function.name, tc.function.arguments
                )
                tool_results.append({
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "name": tc.function.name,
                    "content": result_str,
                })

            # Serialize tool_calls for history
            if loop == 0:
                tool_calls_for_history = json.dumps(
                    [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                )

            # Append assistant + tool results to message list and continue
            messages.append(msg.model_dump(exclude_none=True))
            messages.extend(tool_results)

        else:
            # Fallback if loop exhausted (should almost never happen)
            final_reply = "抱歉，資料查詢時間稍長，請稍後再試。"

        # Persist to history
        await self._save_message("user", user_message)
        await self._save_message("assistant", final_reply, tool_calls_for_history)

        # Chunk reply for Telegram (4096-char limit per message)
        return _chunk_message(final_reply)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _chunk_message(text: str, limit: int = _TELEGRAM_CHUNK) -> list[str]:
    """
    Split a long message into Telegram-safe chunks.
    Tries to split on double-newlines to preserve formatting.
    """
    if len(text) <= limit:
        return [text] if text.strip() else ["（無回應內容）"]

    chunks: list[str] = []
    while len(text) > limit:
        # Find a good split point
        split_at = text.rfind("\n\n", 0, limit)
        if split_at < limit // 2:
            split_at = text.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks
