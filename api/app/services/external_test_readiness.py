from __future__ import annotations

from app.core.config import settings


def _configured(*values: str) -> bool:
    return all(bool(value.strip()) for value in values)


def external_test_readiness() -> dict:
    """Fail-closed gate for opening ForgeBase to unknown public traffic."""
    r2_ready = _configured(
        settings.R2_ACCOUNT_ID,
        settings.R2_ACCESS_KEY_ID,
        settings.R2_SECRET_ACCESS_KEY,
        settings.R2_BUCKET_NAME,
        settings.R2_PUBLIC_URL,
    )
    backup_ready = _configured(
        settings.BACKUP_S3_ENDPOINT_URL,
        settings.BACKUP_S3_ACCESS_KEY_ID,
        settings.BACKUP_S3_SECRET_ACCESS_KEY,
        settings.BACKUP_S3_BUCKET_NAME,
        settings.BACKUP_ENCRYPTION_KEY,
    )
    internal_email_alerting_ready = _configured(
        settings.RESEND_API_KEY,
        settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST,
        settings.SALES_NOTIFY_EMAIL,
    ) and not settings.EMAIL_DRY_RUN
    checks = {
        "rfq_signed_challenge": {
            # RFQ submission already forces the signed challenge in every
            # production environment, even when the local development toggle
            # is left at its default value.
            "ok": bool(settings.is_production or settings.RFQ_BOT_CHALLENGE_REQUIRED),
            "label": "RFQ 簽章 challenge",
        },
        "turnstile": {
            "ok": _configured(
                settings.TURNSTILE_SITE_KEY,
                settings.TURNSTILE_SECRET_KEY,
                settings.TURNSTILE_ALLOWED_HOSTNAMES,
            ),
            "label": "Turnstile 公開表單防護",
        },
        "email_external_kill_switch": {
            "ok": not settings.EMAIL_EXTERNAL_DELIVERY_ENABLED,
            "label": "禁止寄信給訪客／leads",
        },
        "email_internal_allowlist": {
            "ok": _configured(
                settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST,
                settings.SALES_NOTIFY_EMAIL,
            ),
            "label": "內部通知 allowlist 與收件匣",
        },
        "resend_webhook": {
            "ok": bool(settings.RESEND_API_KEY and settings.RESEND_WEBHOOK_SECRET),
            "label": "Resend webhook 驗簽與退信治理",
        },
        "asset_object_storage": {
            "ok": r2_ready,
            "label": "R2 素材物件儲存",
        },
        "offsite_backup": {
            "ok": backup_ready,
            "label": "加密 off-site 備份設定",
        },
        "incident_alerting": {
            "ok": bool(settings.OPS_ALERT_WEBHOOK_URL.strip()) or internal_email_alerting_ready,
            "label": "異常告警管道",
        },
        "external_uptime_monitor": {
            "ok": bool(settings.EXTERNAL_MONITOR_NAME.strip()),
            "label": "站外 uptime 監控",
        },
        "synthetic_data_isolation": {
            "ok": bool(settings.SYNTHETIC_TEST_TOKEN.strip()),
            "label": "合成測試資料隔離",
        },
    }
    blockers = [key for key, item in checks.items() if not item["ok"]]
    return {
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
    }
