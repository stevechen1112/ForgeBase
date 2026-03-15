"""
AI Nurture Path Optimizer  (3.3.2)

Analyzes the performance of nurture sequence steps
(open rate proxy from click events, engagement) and
generates AI suggestions to reorder, condense, or rewrite steps.
"""
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

NURTURE_SYSTEM = """You are an email marketing expert specializing in B2B industrial nurture campaigns.
Analyze nurture sequence performance data and suggest concrete improvements.
Focus on: step ordering, subject line quality, timing, personalization signals.
Output valid JSON only."""


async def optimize_nurture_sequence(
    sequence: dict[str, Any],
    steps_with_metrics: list[dict[str, Any]],
    enrollments_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate AI optimization suggestions for a nurture sequence.

    Args:
        sequence: { id, name, trigger_stage, trigger_event, description }
        steps_with_metrics: list of {
            step_number, subject, delay_days,
            sent_count, click_count, click_rate (%)
        }
        enrollments_summary: {
            total_enrolled, active, completed, dropped,
            avg_completion_rate (%)
        }

    Returns:
        {
            overall_assessment, health_score (0-100),
            step_issues: [{step_number, issue, severity}],
            reorder_suggestion: [[new step order]],
            step_rewrites: [{step_number, new_subject, improvement_reason}],
            timing_adjustments: [{step_number, current_delay, suggested_delay, reason}],
            drop_off_analysis: str,
            top_performing_step: int | null,
            summary_recommendations: [str]
        }
    """
    steps_ctx = json.dumps(steps_with_metrics, ensure_ascii=False, indent=2)
    enrollment_ctx = json.dumps(enrollments_summary, ensure_ascii=False)

    prompt = f"""
Analyze this B2B email nurture sequence and provide optimization suggestions.

── Sequence ──
Name: {sequence.get("name")}
Trigger: {sequence.get("trigger_stage", "warm")} stage / {sequence.get("trigger_event", "N/A")} event
Description: {sequence.get("description", "N/A")}

── Steps with Performance ──
{steps_ctx}

── Enrollment Summary ──
{enrollment_ctx}

── B2B Email Benchmarks ──
Good click-through rate: > 3% | Good completion rate: > 40%
Optimal step delay: 3-7 days for warm prospects, shorter for hot

Return JSON:
{{
  "overall_assessment": "<2-sentence assessment>",
  "health_score": <integer 0-100>,
  "step_issues": [
    {{"step_number": <int>, "issue": "<description>", "severity": "high|medium|low"}}
  ],
  "reorder_suggestion": [<new ordered list of step numbers, null if no reorder needed>],
  "step_rewrites": [
    {{"step_number": <int>, "new_subject": "<better subject line>", "improvement_reason": "<why>"}}
  ],
  "timing_adjustments": [
    {{"step_number": <int>, "current_delay": <days>, "suggested_delay": <days>, "reason": "<why>"}}
  ],
  "drop_off_analysis": "<where do people drop off and likely why>",
  "top_performing_step": <step_number or null>,
  "summary_recommendations": [<top 3 actionable recommendations as strings>]
}}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": NURTURE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1200,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"Nurture optimizer failed: {e}")
        return {
            "overall_assessment": "AI analysis unavailable.",
            "health_score": 0,
            "step_issues": [],
            "reorder_suggestion": None,
            "step_rewrites": [],
            "timing_adjustments": [],
            "drop_off_analysis": "Analysis unavailable.",
            "top_performing_step": None,
            "summary_recommendations": ["Retry AI analysis after checking API connectivity"],
        }
