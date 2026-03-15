"""
Integration Status API — 1b.5.6

GET /api/v1/admin/integrations/status  — returns config status of all integrations
                                          (reads env vars, no writes)
"""
import os

from fastapi import APIRouter, Depends

from app.api.v1.deps import require_content_editor
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/integrations/status")
async def get_integrations_status(
    _: User = Depends(require_content_editor),
):
    """
    Returns which integrations are configured (env vars present).
    Does not expose secret values — only whether they are set.
    """

    def _configured(*keys: str) -> bool:
        return all(bool(os.getenv(k)) for k in keys)

    def _masked(val: str, keep: int = 8) -> str | None:
        if not val:
            return None
        return val[:keep] + "..." if len(val) > keep else val

    measurement_id = os.getenv("NEXT_PUBLIC_GA_MEASUREMENT_ID", "")
    pixel_id       = os.getenv("META_PIXEL_ID", "")
    customer_id    = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    webhook_urls   = [
        u.strip()
        for u in os.getenv("WEBHOOK_ENDPOINT_URLS", "").split(",")
        if u.strip()
    ]

    return {
        "ga4": {
            "configured":    bool(measurement_id),
            "measurement_id": _masked(measurement_id, 4),
        },
        "hubspot": {
            "configured": _configured("HUBSPOT_API_KEY"),
        },
        "google_ads": {
            "configured": _configured(
                "GOOGLE_ADS_DEVELOPER_TOKEN",
                "GOOGLE_ADS_CUSTOMER_ID",
                "GOOGLE_ADS_CLIENT_ID",
                "GOOGLE_ADS_CLIENT_SECRET",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_ADS_CUSTOMER_LIST_ID",
            ),
            "customer_id": customer_id or None,
        },
        "meta": {
            "configured": _configured("META_PIXEL_ID", "META_ACCESS_TOKEN"),
            "pixel_id":   pixel_id or None,
        },
        "webhook": {
            "configured":     bool(webhook_urls),
            "endpoint_count": len(webhook_urls),
            "endpoints": [
                (u[:40] + "...") if len(u) > 40 else u
                for u in webhook_urls
            ],
            "signing_enabled": _configured("WEBHOOK_SECRET"),
        },
        "smtp": {
            "configured": _configured("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"),
            "host":       os.getenv("SMTP_HOST") or None,
        },
    }
