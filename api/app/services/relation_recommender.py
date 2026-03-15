"""
AI Entity Relation Recommender  (3.3.3)

Analyzes behavioral co-occurrence patterns in tracking_events to discover
latent relationships between Products and Applications.

Logic:
- Find visitors who viewed both entity A and entity B in the same session or across sessions
- Score co-occurrence strength
- Filter out already-linked entities
- Use AI to validate and explain why an entity relation makes domain sense
"""
import json
import logging
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

RELATION_SYSTEM = """You are a B2B industrial product expert.
Given co-occurrence data from website visitor behavior, identify which product-application
relationships make genuine domain sense and should be officially linked.
Filter out coincidental co-occurrences. Output valid JSON."""


# ── Co-occurrence Query ───────────────────────────────────────────────────────

async def _fetch_cooccurrence(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Find entities frequently viewed together with the given entity
    by the same visitors within a 30-day window.
    """
    if entity_type == "product":
        # Find applications viewed by visitors who also viewed this product
        sql = text("""
            SELECT
                e2.properties->>'application_id' AS related_id,
                'application' AS related_type,
                COUNT(DISTINCT e.visitor_id) AS co_visitor_count
            FROM tracking_events e
            JOIN tracking_events e2
                ON e.visitor_id = e2.visitor_id
               AND e2.event_name = 'application_view'
               AND e2.created_at > NOW() - INTERVAL '90 days'
            WHERE e.event_name = 'product_view'
              AND e.properties->>'product_id' = :entity_id
              AND e.created_at > NOW() - INTERVAL '90 days'
            GROUP BY related_id
            HAVING COUNT(DISTINCT e.visitor_id) >= 2
            ORDER BY co_visitor_count DESC
            LIMIT :limit
        """)
    else:
        # Find products viewed by visitors who also viewed this application
        sql = text("""
            SELECT
                e2.properties->>'product_id' AS related_id,
                'product' AS related_type,
                COUNT(DISTINCT e.visitor_id) AS co_visitor_count
            FROM tracking_events e
            JOIN tracking_events e2
                ON e.visitor_id = e2.visitor_id
               AND e2.event_name = 'product_view'
               AND e2.created_at > NOW() - INTERVAL '90 days'
            WHERE e.event_name = 'application_view'
              AND e.properties->>'application_id' = :entity_id
              AND e.created_at > NOW() - INTERVAL '90 days'
            GROUP BY related_id
            HAVING COUNT(DISTINCT e.visitor_id) >= 2
            ORDER BY co_visitor_count DESC
            LIMIT :limit
        """)

    result = await session.execute(sql, {"entity_id": entity_id, "limit": limit})
    return [dict(r) for r in result.mappings().all()]


# ── Public API ────────────────────────────────────────────────────────────────

async def recommend_relations(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    entity_description: str,
    existing_relations: list[dict[str, Any]],
    candidate_info: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Recommend new entity relationships based on behavioral co-occurrence + AI validation.

    Args:
        entity_type: "product" or "application"
        entity_id: UUID string
        entity_name: display name
        entity_description: brief description
        existing_relations: already-linked entities [{id, name, type}]
        candidate_info: [{id, name, description}] for the related entity candidates

    Returns:
        {
            source_entity: {id, name, type},
            recommendations: [
                {
                    candidate_id, candidate_name, candidate_type,
                    co_visitor_count, confidence_score, reason,
                    is_already_linked
                }
            ],
            ai_summary: str
        }
    """
    cooccurrences = await _fetch_cooccurrence(session, entity_type, entity_id)
    if not cooccurrences:
        return {
            "source_entity": {"id": entity_id, "name": entity_name, "type": entity_type},
            "recommendations": [],
            "ai_summary": "No significant co-occurrence patterns found yet. This may be due to limited traffic data.",
        }

    # Enrich with candidate info
    existing_ids = {r["id"] for r in existing_relations}
    candidate_map = {c["id"]: c for c in candidate_info}

    enriched = []
    for cooc in cooccurrences:
        related_id = cooc.get("related_id")
        if not related_id:
            continue
        cand = candidate_map.get(related_id, {})
        enriched.append({
            "id": related_id,
            "name": cand.get("name", "Unknown"),
            "description": (cand.get("description") or "")[:200],
            "co_visitor_count": int(cooc.get("co_visitor_count", 0)),
            "is_already_linked": related_id in existing_ids,
        })

    # Use AI to validate and score
    related_type = "application" if entity_type == "product" else "product"
    candidates_ctx = json.dumps(enriched, ensure_ascii=False)
    existing_ctx = json.dumps(
        [{"id": r["id"], "name": r.get("name", "")} for r in existing_relations],
        ensure_ascii=False,
    )

    prompt = f"""
A B2B manufacturer website recorded these co-occurrence patterns.

── Source Entity ──
Type: {entity_type}
Name: {entity_name}
Description: {entity_description[:300]}

── Already Linked {related_type}s ──
{existing_ctx}

── Co-occurrence Candidates (frequently viewed together by site visitors) ──
{candidates_ctx}

For each candidate NOT already linked, assess if the pairing makes genuine industrial/technical sense.
Return JSON:
{{
  "recommendations": [
    {{
      "candidate_id": "<id>",
      "candidate_name": "<name>",
      "candidate_type": "{related_type}",
      "co_visitor_count": <int>,
      "confidence_score": <integer 0-100>,
      "reason": "<1-sentence domain rationale>",
      "is_already_linked": <bool>
    }}
  ],
  "ai_summary": "<2-sentence overall pattern analysis>"
}}
Only include candidates with confidence_score >= 60 or co_visitor_count >= 3."""

    try:
        resp = await client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": RELATION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=800,
        )
        ai_result = json.loads(resp.choices[0].message.content)
        return {
            "source_entity": {"id": entity_id, "name": entity_name, "type": entity_type},
            **ai_result,
        }
    except Exception as e:
        logger.error(f"Relation recommender failed: {e}")
        # Fallback: return raw co-occurrence data without AI scoring
        recs = [
            {
                "candidate_id": e["id"],
                "candidate_name": e["name"],
                "candidate_type": related_type,
                "co_visitor_count": e["co_visitor_count"],
                "confidence_score": min(90, e["co_visitor_count"] * 20),
                "reason": f"Frequently viewed together by {e['co_visitor_count']} visitors",
                "is_already_linked": e["is_already_linked"],
            }
            for e in enriched
            if not e["is_already_linked"]
        ]
        return {
            "source_entity": {"id": entity_id, "name": entity_name, "type": entity_type},
            "recommendations": recs,
            "ai_summary": "AI validation unavailable — showing raw co-occurrence data.",
        }
