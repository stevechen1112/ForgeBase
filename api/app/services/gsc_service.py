"""
2.3.4 SEO 診斷儀表板 — Google Search Console API Service

Uses the Search Analytics API (v3) with a service account JSON key.
Falls back to mock data if credentials are not configured.

Required env vars:
  GSC_SERVICE_ACCOUNT_KEY_JSON  — JSON string of service account credentials
  GSC_SITE_URL                  — e.g. "https://example.com/"
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GSC_API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"


# ---------------------------------------------------------------------------
# OAuth2 token for service account (JWT → access_token)
# ---------------------------------------------------------------------------

async def _get_access_token() -> Optional[str]:
    """Exchange service account JSON for a Bearer token via Google OAuth2."""
    key_json = settings.GSC_SERVICE_ACCOUNT_KEY_JSON
    if not key_json:
        return None

    try:
        import time, base64
        import json as _json

        key_data = _json.loads(key_json)
        client_email = key_data["client_email"]
        private_key = key_data["private_key"]

        # Build JWT
        now = int(time.time())
        header = base64.urlsafe_b64encode(
            _json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        payload = base64.urlsafe_b64encode(
            _json.dumps({
                "iss": client_email,
                "scope": GSC_SCOPE,
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now,
                "exp": now + 3600,
            }).encode()
        ).rstrip(b"=")

        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        pk = serialization.load_pem_private_key(private_key.encode(), password=None)
        signing_input = header + b"." + payload
        sig = pk.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        signature = base64.urlsafe_b64encode(sig).rstrip(b"=")
        jwt_token = (signing_input + b"." + signature).decode()

        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": jwt_token,
                },
            )
            if res.status_code == 200:
                return res.json().get("access_token")
            logger.error("GSC token exchange failed %s: %s", res.status_code, res.text[:200])
    except Exception as exc:  # noqa: BLE001
        logger.error("GSC _get_access_token exception: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Search Analytics query helper
# ---------------------------------------------------------------------------

async def query_search_analytics(
    dimensions: list[str],
    start_date: str,
    end_date: str,
    row_limit: int = 500,
    dimension_filter: Optional[dict] = None,
) -> list[dict]:
    """
    Query GSC Search Analytics API.
    Returns list of rows: [{keys: [...], clicks, impressions, ctr, position}, ...]
    """
    token = await _get_access_token()
    if not token:
        logger.warning("No GSC token — returning empty analytics data")
        return []

    site = settings.GSC_SITE_URL
    if not site:
        return []

    body: dict = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    if dimension_filter:
        body["dimensionFilterGroups"] = [{"filters": [dimension_filter]}]

    url = GSC_API.format(site=site)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            if res.status_code == 200:
                return res.json().get("rows", [])
            logger.error("GSC query failed %s: %s", res.status_code, res.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("GSC query exception: %s", exc)
    return []


# ---------------------------------------------------------------------------
# SEO Audit helpers
# ---------------------------------------------------------------------------

async def get_page_performance(days: int = 28) -> list[dict]:
    """
    Fetch per-page clicks, impressions, CTR, average position for the last N days.
    Returns list sorted by impressions desc.
    """
    end = date.today() - timedelta(days=2)  # GSC has ~2 day delay
    start = end - timedelta(days=days)
    rows = await query_search_analytics(
        dimensions=["page"],
        start_date=str(start),
        end_date=str(end),
        row_limit=1000,
    )
    result = []
    for r in rows:
        result.append({
            "page": r["keys"][0],
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": round(r.get("ctr", 0) * 100, 2),    # as percentage
            "avg_position": round(r.get("position", 0), 1),
        })
    result.sort(key=lambda x: x["impressions"], reverse=True)
    return result


async def get_keyword_opportunities(days: int = 28) -> list[dict]:
    """
    Pages ranking position 6-20 with >100 impressions — high opportunity.
    Returns sorted by impressions desc.
    """
    rows = await get_page_performance(days=days)
    return [
        r for r in rows
        if 6 <= r["avg_position"] <= 20 and r["impressions"] >= 100
    ]


async def detect_keyword_cannibalization(days: int = 28) -> list[dict]:
    """
    Find query+page combinations where the same query ranks for multiple pages.
    Returns list of {query, pages: [{page, clicks, position}, ...]}
    """
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=days)
    rows = await query_search_analytics(
        dimensions=["query", "page"],
        start_date=str(start),
        end_date=str(end),
        row_limit=1000,
    )

    # Group by query
    by_query: dict[str, list] = {}
    for r in rows:
        query, page = r["keys"][0], r["keys"][1]
        by_query.setdefault(query, []).append({
            "page": page,
            "clicks": r.get("clicks", 0),
            "position": round(r.get("position", 0), 1),
        })

    # Only keep queries with 2+ pages
    cannibalized = [
        {"query": q, "pages": sorted(pages, key=lambda x: x["position"])}
        for q, pages in by_query.items()
        if len(pages) >= 2
    ]
    cannibalized.sort(key=lambda x: len(x["pages"]), reverse=True)
    return cannibalized[:50]  # top 50
