"""
IP-to-Company resolution service (2.1.2).

Supports multiple providers in priority order:
  1. ip-api.com (free, no key required — basic company/ISP info)
  2. Clearbit Reveal (requires CLEARBIT_API_KEY)
  3. Manual override (via Admin UI)

Only enriches each visitor_id once (idempotent via ip_resolved_at check).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── ip-api.com (free tier) ───────────────────────────────────────────────────
IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,city,org,as,query"


async def _resolve_via_ip_api(ip: str) -> Optional[dict]:
    """
    Resolve IP using ip-api.com free tier.
    Returns partial company info: org name, country, city.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(IP_API_URL.format(ip=ip))
            data = r.json()
            if data.get("status") != "success":
                return None
            # org is usually "AS12345 Company Name" — strip AS prefix
            org = data.get("org", "") or ""
            company_name = org.split(" ", 1)[1] if " " in org else org
            if not company_name:
                return None
            return {
                "company_name": company_name,
                "country": data.get("countryCode"),
                "city": data.get("city"),
                "enrichment_source": "ip_api",
            }
    except Exception as e:
        logger.warning("ip-api.com resolve failed for %s: %s", ip, e)
        return None


async def _resolve_via_clearbit(ip: str) -> Optional[dict]:
    """
    Resolve IP using Clearbit Reveal API (requires CLEARBIT_API_KEY).
    Returns richer company info if available.
    """
    api_key = getattr(settings, "CLEARBIT_API_KEY", None)
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=8.0,
            auth=(api_key, ""),
        ) as client:
            r = await client.get(f"https://reveal.clearbit.com/v1/companies/find?ip={ip}")
            if r.status_code != 200:
                return None
            data = r.json()
            company = data.get("company") or {}
            if not company.get("name"):
                return None
            geo = company.get("geo") or {}
            metrics = company.get("metrics") or {}
            return {
                "company_name": company["name"],
                "domain": company.get("domain"),
                "industry": company.get("category", {}).get("industry"),
                "employee_count_range": _clearbit_employee_range(metrics.get("employees")),
                "country": geo.get("countryCode"),
                "city": geo.get("city"),
                "linkedin_url": company.get("linkedin", {}).get("handle"),
                "logo_url": company.get("logo"),
                "description": company.get("description"),
                "enrichment_source": "clearbit",
            }
    except Exception as e:
        logger.warning("Clearbit resolve failed for %s: %s", ip, e)
        return None


def _clearbit_employee_range(count: Optional[int]) -> Optional[str]:
    if count is None:
        return None
    if count <= 10:
        return "1-10"
    if count <= 50:
        return "11-50"
    if count <= 200:
        return "51-200"
    if count <= 500:
        return "201-500"
    if count <= 1000:
        return "501-1000"
    return "1001+"


async def resolve_ip_to_company(ip: str) -> Optional[dict]:
    """
    Try providers in order, return first successful result.
    Returns dict with company data or None if unresolvable.
    """
    # Skip private/reserved IP ranges
    if _is_private_ip(ip):
        return None

    # Try Clearbit first (richer data) then fall back to ip-api
    result = await _resolve_via_clearbit(ip)
    if result:
        return result
    return await _resolve_via_ip_api(ip)


def _is_private_ip(ip: str) -> bool:
    """Return True for RFC1918 / loopback / link-local addresses."""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return True
