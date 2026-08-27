"""Template registry and honest site-delivery readiness checks."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.user import User

SITE_TEMPLATES: dict[str, dict[str, Any]] = {
    "handtool-company": {"name": "Hand Tools Manufacturer", "industry": "Hand tools", "demo_url": "/northforge-tools", "cms_connected": True},
    "industrial-machinery": {"name": "Industrial Machinery", "industry": "Machinery", "demo_url": "/templates/industrial-machinery/", "cms_connected": False},
    "precision-machining": {"name": "Precision Machining", "industry": "CNC machining", "demo_url": "https://axisform.172-233-64-5.sslip.io", "cms_connected": True},
    "electronic-components": {"name": "Electronic Components", "industry": "Electronics", "demo_url": "/templates/electronic-components/", "cms_connected": False},
    "industrial-automation": {"name": "Industrial Automation", "industry": "Automation", "demo_url": "/templates/industrial-automation/", "cms_connected": False},
    "engineering-materials": {"name": "Engineering Materials", "industry": "Materials", "demo_url": "/templates/engineering-materials/", "cms_connected": False},
    "custom-packaging": {"name": "Custom Packaging", "industry": "Packaging", "demo_url": "/templates/custom-packaging/", "cms_connected": False},
}


def template_catalog() -> list[dict[str, Any]]:
    return [
        {"key": key, **item, "publish_supported": item["cms_connected"]}
        for key, item in SITE_TEMPLATES.items()
    ]


async def evaluate_site_readiness(db: AsyncSession, build: SiteBuild) -> dict[str, Any]:
    profile = (
        await db.exec(select(SiteProfile).where(SiteProfile.tenant_id == build.tenant_id))
    ).first()
    owner = (
        await db.exec(select(User).where(User.tenant_id == build.tenant_id, User.role == "owner", User.is_active.is_(True)))
    ).first()
    template = SITE_TEMPLATES.get(build.template_key)
    profile_host = urlparse(profile.site_url).hostname if profile else None
    checks = {
        "active_owner": bool(owner),
        "brand_name": bool(profile and profile.brand_name.strip()),
        "contact_email": bool(profile and profile.contact_email.strip()),
        "site_url": bool(profile and profile.site_url.startswith(("http://", "https://"))),
        "primary_domain": bool(build.primary_domain and "." in build.primary_domain),
        "domain_matches_site_url": bool(build.primary_domain and profile_host == build.primary_domain),
        "supported_locales": bool(json.loads(build.locales_json or "[]")),
        "template_exists": bool(template),
        "cms_adapter_connected": bool(template and template["cms_connected"] and build.cms_connected),
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {"ready": not blockers, "checks": checks, "blockers": blockers}


async def validate_and_store_readiness(db: AsyncSession, build: SiteBuild) -> dict[str, Any]:
    readiness = await evaluate_site_readiness(db, build)
    build.readiness_json = json.dumps(readiness)
    build.status = "ready" if readiness["ready"] else "blocked"
    build.last_error = None if readiness["ready"] else ", ".join(readiness["blockers"])
    build.updated_at = utcnow_naive()
    db.add(build)
    await db.commit()
    await db.refresh(build)
    return readiness
