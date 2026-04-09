"""
Subscription API endpoints.

GET  /api/v1/subscription/plans      — Public: list available plans
GET  /api/v1/subscription/current    — Authenticated: current plan + usage
POST /api/v1/subscription/upgrade    — Owner-only: upgrade plan
POST /api/v1/subscription/checkout   — Owner-only: create PayPal checkout URL
POST /api/v1/subscription/activate   — Callback: activate after PayPal approval
POST /api/v1/subscription/webhook    — PayPal webhook handler
POST /api/v1/subscription/cancel     — Owner-only: cancel subscription
"""
import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.models.tenant import Tenant
from app.services.subscription import (
    PLAN_MATRIX,
    get_plan,
    get_quota_status,
)
from app.core.config import settings
from app.core.datetime import utcnow_naive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["subscription"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class PlanInfo(BaseModel):
    name: str
    display_name: str
    price_monthly_usd: int
    max_products: Optional[int]
    max_admins: Optional[int]
    features: Dict[str, bool]


class CurrentPlan(BaseModel):
    plan: str
    display_name: str
    features: Dict[str, bool]
    limits: Dict[str, Optional[int]]
    usage: Dict[str, int]


class UpgradeRequest(BaseModel):
    target_plan: str


class UpgradeResult(BaseModel):
    success: bool
    message: str
    new_plan: str


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.get("/plans", response_model=List[PlanInfo])
async def list_plans():
    """Public: list all subscription plans."""
    plans = []
    for name, config in PLAN_MATRIX.items():
        plans.append(
            PlanInfo(
                name=name,
                display_name=config["display_name"],
                price_monthly_usd=config["price_monthly_usd"],
                max_products=config["max_products"],
                max_admins=config["max_admins"],
                features=config["features"],
            )
        )
    return plans


@router.get("/current", response_model=CurrentPlan)
async def current_plan(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Authenticated: get current tenant plan + usage."""
    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    quota = await get_quota_status(session, current_user.tenant_id)
    if not quota:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return CurrentPlan(**quota)


@router.post("/upgrade", response_model=UpgradeResult)
async def upgrade_plan(
    body: UpgradeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Owner-only: upgrade tenant plan."""
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only owner/admin can change plan")

    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    tenant = await session.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if body.target_plan not in PLAN_MATRIX:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown plan: {body.target_plan}")

    plan_order = {"starter": 0, "professional": 1}
    current_level = plan_order.get(tenant.plan, 0)
    target_level = plan_order.get(body.target_plan, 0)

    if target_level <= current_level:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot downgrade from {tenant.plan} to {body.target_plan}",
        )

    old_plan = tenant.plan
    new_config = get_plan(body.target_plan)

    tenant.plan = body.target_plan
    tenant.max_products = new_config["max_products"]
    tenant.max_admins = new_config["max_admins"]
    tenant.updated_at = utcnow_naive()

    session.add(tenant)
    await session.commit()

    return UpgradeResult(
        success=True,
        message=f"Upgraded: {old_plan} → {body.target_plan}",
        new_plan=body.target_plan,
    )


# ── PayPal checkout ──────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str  # "starter" | "professional"


class CheckoutResult(BaseModel):
    subscription_id: str
    approve_url: str


@router.post("/checkout", response_model=CheckoutResult)
async def create_checkout(
    body: CheckoutRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a PayPal subscription checkout URL. Owner/admin only."""
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only owner/admin can manage billing")

    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    if body.plan not in PLAN_MATRIX:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown plan: {body.plan}")

    from app.services.paypal import create_subscription

    frontend_url = settings.ADMIN_URL
    result = await create_subscription(
        plan_name=body.plan,
        tenant_id=str(current_user.tenant_id),
        return_url=f"{frontend_url}/dashboard/settings/billing?status=success",
        cancel_url=f"{frontend_url}/dashboard/settings/billing?status=cancelled",
    )

    return CheckoutResult(**result)


# ── PayPal activate (after subscriber approves) ─────────────────────────────

class ActivateRequest(BaseModel):
    subscription_id: str


@router.post("/activate")
async def activate_subscription(
    body: ActivateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Activate subscription after PayPal approval redirect."""
    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    from app.services.paypal import get_subscription as pp_get

    pp_data = await pp_get(body.subscription_id)
    pp_status = pp_data.get("status", "")

    if pp_status not in ("ACTIVE", "APPROVED"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Subscription not active: {pp_status}",
        )

    # Find which plan this PayPal plan ID maps to
    pp_plan_id = pp_data.get("plan_id", "")
    target_plan = None
    from app.services.paypal import PLAN_ID_MAP
    for plan_name, pid in PLAN_ID_MAP.items():
        if pid == pp_plan_id:
            target_plan = plan_name
            break

    if not target_plan:
        target_plan = "professional"  # Default if can't resolve

    tenant = await session.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    plan_config = get_plan(target_plan)
    tenant.plan = target_plan
    tenant.max_products = plan_config["max_products"]
    tenant.max_admins = plan_config["max_admins"]
    tenant.paypal_subscription_id = body.subscription_id
    tenant.paypal_payer_email = (
        pp_data.get("subscriber", {}).get("email_address", "")
    )
    tenant.updated_at = utcnow_naive()
    session.add(tenant)
    await session.commit()

    return {"success": True, "plan": target_plan}


# ── PayPal webhook ───────────────────────────────────────────────────────────

@router.post("/webhook")
async def paypal_webhook(request: Request):
    """
    Handle PayPal subscription webhooks.
    Events: BILLING.SUBSCRIPTION.ACTIVATED, CANCELLED, SUSPENDED, PAYMENT.SALE.COMPLETED
    """
    body = await request.body()
    headers = dict(request.headers)

    from app.services.paypal import verify_webhook_signature

    if not await verify_webhook_signature(headers, body):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    event = json.loads(body)
    event_type = event.get("event_type", "")
    resource = event.get("resource", {})

    logger.info("PayPal webhook: %s", event_type)

    # Get tenant ID from custom_id
    custom_id = resource.get("custom_id", "")
    if not custom_id:
        # Try subscriber -> custom_id for different event structures
        custom_id = resource.get("custom", "")

    if not custom_id:
        logger.warning("PayPal webhook missing custom_id: %s", event_type)
        return {"status": "ignored"}

    from app.db.session import async_engine
    from sqlmodel.ext.asyncio.session import AsyncSession as AS
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(async_engine, class_=AS, expire_on_commit=False)
    async with async_session() as db:
        try:
            tenant_uuid = uuid.UUID(custom_id)
        except ValueError:
            logger.warning("PayPal webhook invalid custom_id: %s", custom_id)
            return {"status": "ignored"}

        tenant = await db.get(Tenant, tenant_uuid)
        if not tenant:
            logger.warning("PayPal webhook tenant not found: %s", custom_id)
            return {"status": "ignored"}

        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            sub_id = resource.get("id", "")
            plan_id = resource.get("plan_id", "")

            from app.services.paypal import PLAN_ID_MAP
            target_plan = None
            for pn, pid in PLAN_ID_MAP.items():
                if pid == plan_id:
                    target_plan = pn
                    break

            if target_plan:
                plan_config = get_plan(target_plan)
                tenant.plan = target_plan
                tenant.max_products = plan_config["max_products"]
                tenant.max_admins = plan_config["max_admins"]

            tenant.paypal_subscription_id = sub_id
            tenant.paypal_payer_email = (
                resource.get("subscriber", {}).get("email_address", "")
            )
            tenant.is_active = True
            tenant.updated_at = utcnow_naive()

        elif event_type in (
            "BILLING.SUBSCRIPTION.CANCELLED",
            "BILLING.SUBSCRIPTION.SUSPENDED",
        ):
            # Downgrade to starter limits but keep data
            starter = get_plan("starter")
            tenant.plan = "starter"
            tenant.max_products = starter["max_products"]
            tenant.max_admins = starter["max_admins"]
            tenant.paypal_subscription_id = None
            tenant.updated_at = utcnow_naive()

        elif event_type == "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
            logger.warning("Payment failed for tenant %s", custom_id)
            # Don't downgrade immediately — PayPal retries

        db.add(tenant)
        await db.commit()

    return {"status": "ok"}


# ── Cancel subscription ──────────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_sub(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Owner-only: cancel current PayPal subscription."""
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only owner/admin can cancel")

    if not current_user.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User has no tenant")

    tenant = await session.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if not tenant.paypal_subscription_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No active subscription")

    from app.services.paypal import cancel_subscription

    success = await cancel_subscription(tenant.paypal_subscription_id)
    if not success:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Failed to cancel with PayPal")

    starter = get_plan("starter")
    tenant.plan = "starter"
    tenant.max_products = starter["max_products"]
    tenant.max_admins = starter["max_admins"]
    tenant.paypal_subscription_id = None
    tenant.updated_at = utcnow_naive()
    session.add(tenant)
    await session.commit()

    return {"success": True, "plan": "starter"}
