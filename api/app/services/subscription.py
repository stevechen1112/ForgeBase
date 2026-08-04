"""
Plan definitions and quota checking for SaaS tiers.

Usage:
    from app.services.subscription import PLAN_MATRIX, get_plan, check_quota
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.product import Product
from app.models.user import User
from app.models.tenant import Tenant


# ── Plan Matrix ──────────────────────────────────────────────────────────────
PLAN_MATRIX: Dict[str, Dict[str, Any]] = {
    "starter": {
        "display_name": "Starter",
        "price_monthly_usd": 149,
        "max_products": 50,
        "max_admins": 2,
        "features": {
            "multilingual": False,
            "ai_content_generation": False,
            "full_tracking": False,
            "intent_scoring": False,
            "dynamic_cta": False,
            "ai_advisor": False,
            "chat_handoff": False,
            "notifications": False,
            "follow_up_reminders": False,
            "nurture_email": False,
            "seo_redirects": False,
        },
    },
    "professional": {
        "display_name": "Professional",
        "price_monthly_usd": 699,
        "max_products": None,   # unlimited
        "max_admins": None,     # unlimited
        "features": {
            "multilingual": True,
            "ai_content_generation": True,
            "full_tracking": True,
            "intent_scoring": True,
            "dynamic_cta": True,
            "ai_advisor": True,
            "chat_handoff": True,
            "notifications": True,
            "follow_up_reminders": True,
            "nurture_email": True,
            "seo_redirects": True,
        },
    },
}

# Feature flag for the Email Nurture Engine (sequence / step / enrollment).
NURTURE_FEATURE = "nurture_email"


def get_plan(plan_name: str) -> Dict[str, Any]:
    return PLAN_MATRIX.get(plan_name, PLAN_MATRIX["starter"])


def get_plan_feature(plan_name: str, feature: str) -> bool:
    plan = get_plan(plan_name)
    return plan["features"].get(feature, False)


# ── Quota checking ───────────────────────────────────────────────────────────
async def check_quota(
    session: AsyncSession,
    tenant_id: UUID,
    resource: str,
) -> Dict[str, Any]:
    """Check whether *resource* quota is still available for *tenant_id*.

    Returns ``{"allowed": True}`` or ``{"allowed": False, "message": ..., "current": N, "limit": N}``.
    """
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        return {"allowed": False, "message": "Tenant not found"}

    if resource == "product":
        limit = tenant.max_products
        if limit is None:
            return {"allowed": True}
        current = (
            await session.exec(
                select(func.count()).select_from(Product)
                .where(Product.tenant_id == tenant_id, Product.locale == "en")
            )
        ).one()
        if current >= limit:
            return {
                "allowed": False,
                "message": f"Product limit reached ({limit}). Upgrade to Professional for unlimited products.",
                "current": current,
                "limit": limit,
            }

    elif resource == "admin":
        limit = tenant.max_admins
        if limit is None:
            return {"allowed": True}
        current = (
            await session.exec(
                select(func.count())
                .select_from(User)
                .where(User.tenant_id == tenant_id, User.is_active == True, User.role.in_(["admin", "owner"]))  # noqa: E712
            )
        ).one()
        if current >= limit:
            return {
                "allowed": False,
                "message": f"Admin account limit reached ({limit}). Upgrade to Professional for unlimited.",
                "current": current,
                "limit": limit,
            }

    return {"allowed": True}


async def get_quota_status(
    session: AsyncSession,
    tenant_id: UUID,
) -> Dict[str, Any]:
    """Full quota status for display in admin dashboard."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        return {}

    plan_config = get_plan(tenant.plan)

    product_count = (
        await session.exec(
            select(func.count()).select_from(Product)
            .where(Product.tenant_id == tenant_id, Product.locale == "en")
        )
    ).one()

    admin_count = (
        await session.exec(
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.is_active == True, User.role.in_(["admin", "owner"]))  # noqa: E712
        )
    ).one()

    return {
        "plan": tenant.plan,
        "display_name": plan_config["display_name"],
        "features": plan_config["features"],
        "limits": {
            "max_products": tenant.max_products,
            "max_admins": tenant.max_admins,
        },
        "usage": {
            "products": product_count,
            "admins": admin_count,
        },
    }
