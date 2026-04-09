"""
IP resolution service — GeoIP country/city lookup via ip-api.com (free tier).
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,city,org,as,query"


async def resolve_ip_to_company(ip: str) -> Optional[dict]:
    """
    Resolve IP to basic geo/ISP info using ip-api.com free tier.
    Returns dict with country/city/org data, or None if unresolvable.
    """
    if _is_private_ip(ip):
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(IP_API_URL.format(ip=ip))
            data = r.json()
            if data.get("status") != "success":
                return None
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


def _is_private_ip(ip: str) -> bool:
    """Return True for RFC1918 / loopback / link-local addresses."""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return True
