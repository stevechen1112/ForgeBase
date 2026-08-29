from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_NULL_POOL: bool = False

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # LLM provider — OpenAI only
    OPENAI_API_KEY: str = ""
    AI_MODEL_NAME: str = "gpt-5.6-luna"
    CHAT_ENABLED: bool = True
    CHAT_SESSION_MESSAGE_LIMIT: int = 20
    CHAT_DAILY_TENANT_MESSAGE_LIMIT: int = 500
    CHAT_LLM_TIMEOUT_SECONDS: float = 20.0
    PUBLIC_TENANT_SLUG: str = ""
    # Transitional compatibility for the build-time tenant header. Public
    # host routing takes precedence and rejects host/header disagreement.
    # Disable after the shared host-aware frontend is deployed.
    PUBLIC_TENANT_HEADER_COMPATIBILITY_ENABLED: bool = True
    # Shared Next.js SSR requests reach the API over the private container
    # network, so their public Host is carried in a separate authenticated
    # header. Never expose this value through NEXT_PUBLIC_* variables.
    TENANT_ROUTING_SECRET: str = ""
    TENANT_BASE_DOMAIN: str = "forgebase.com"
    TENANT_CNAME_TARGET: str = "edge.forgebase.com"
    DOMAIN_DNS_RESOLVER_URL: str = "https://cloudflare-dns.com/dns-query"
    DOMAIN_DNS_TIMEOUT_SECONDS: float = 8.0

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "forgebase-assets"
    R2_PUBLIC_URL: str = ""
    ASSET_TENANT_QUOTA_BYTES: int = 2_147_483_648  # 2 GiB per tenant

    # Public form abuse prevention and privacy lifecycle
    RFQ_BOT_CHALLENGE_REQUIRED: bool = False
    RFQ_CHALLENGE_MIN_AGE_SECONDS: int = 2
    RFQ_CHALLENGE_MAX_AGE_SECONDS: int = 7200
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_SITE_KEY: str = ""
    TURNSTILE_ALLOWED_HOSTNAMES: str = ""
    TURNSTILE_EXPECTED_ACTION: str = "rfq_submit"
    ANALYTICS_RETENTION_DAYS: int = 180
    CONSENT_POLICY_VERSION: str = "2026-08-15"
    # Only direct peers in these CIDRs may supply X-Forwarded-For. Keep empty
    # unless the deployment's reverse-proxy networks are known explicitly.
    TRUSTED_PROXY_CIDRS: str = ""

    # Company-identification POC. PDL is registered only when both the API key
    # and the deployment's contracted per-match cost are configured.
    PDL_API_KEY: str = ""
    PDL_DATA_USE_APPROVED: bool = False
    PDL_IP_ENRICH_URL: str = "https://api.peopledatalabs.com/v5/ip/enrich"
    PDL_IP_ENRICH_ESTIMATED_COST: float = 0.0
    PDL_CONTACT_DATA_USE_APPROVED: bool = False
    PDL_PERSON_SEARCH_URL: str = "https://api.peopledatalabs.com/v5/person/search"
    PDL_CONTACT_ESTIMATED_COST: float = 0.0
    COMPANY_PROVIDER_TIMEOUT_SECONDS: float = 8.0
    COMPANY_PROVIDER_CIRCUIT_FAILURES: int = 5
    COMPANY_PROVIDER_CIRCUIT_COOLDOWN_SECONDS: int = 300

    # Contact-window POC providers. Registration requires the matching data-use
    # approval flag, credential and non-zero contracted unit cost.
    APOLLO_API_KEY: str = ""
    APOLLO_DATA_USE_APPROVED: bool = False
    APOLLO_PEOPLE_SEARCH_URL: str = "https://api.apollo.io/api/v1/mixed_people/api_search"
    APOLLO_PEOPLE_MATCH_URL: str = "https://api.apollo.io/api/v1/people/match"
    APOLLO_CONTACT_ESTIMATED_COST: float = 0.0
    HUNTER_API_KEY: str = ""
    HUNTER_DATA_USE_APPROVED: bool = False
    HUNTER_DOMAIN_SEARCH_URL: str = "https://api.hunter.io/v2/domain-search"
    HUNTER_CONTACT_ESTIMATED_COST: float = 0.0
    HUNTER_EMAIL_VERIFIER_URL: str = "https://api.hunter.io/v2/email-verifier"
    HUNTER_VERIFY_ESTIMATED_COST: float = 0.0
    CONTACT_PROVIDER_TIMEOUT_SECONDS: float = 10.0
    CONTACT_PROVIDER_CIRCUIT_FAILURES: int = 5
    CONTACT_PROVIDER_CIRCUIT_COOLDOWN_SECONDS: int = 300

    # Operational monitoring (webhook optional; structured logs are always emitted)
    OPS_ALERT_WEBHOOK_URL: str = ""
    OPS_FAILED_JOB_ALERT_THRESHOLD: int = 1
    OPS_STALE_JOB_MINUTES: int = 15
    OPS_ALERT_COOLDOWN_MINUTES: int = 60
    EXTERNAL_MONITOR_NAME: str = ""

    # Resend
    RESEND_API_KEY: str = ""
    RESEND_WEBHOOK_SECRET: str = ""
    RESEND_WEBHOOK_TOLERANCE_SECONDS: int = 300
    EMAIL_FROM: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "ForgeBase"
    # When true, exercise the application path without contacting the ESP.
    # A dry run must never be recorded as an actual delivery.
    EMAIL_DRY_RUN: bool = False
    # Platform-level kill switch. Tenant settings can never override this.
    # Keep false throughout public testing when leads must not be contacted.
    EMAIL_EXTERNAL_DELIVERY_ENABLED: bool = False
    # Independent North Star outreach kill switch. Both switches must be on.
    OUTREACH_SEND_ENABLED: bool = False
    # Public API origin used for signed unsubscribe links, e.g. https://api.example.com.
    OUTREACH_PUBLIC_BASE_URL: str = ""
    # Separate signing secret; never reuse provider webhook credentials.
    OUTREACH_UNSUBSCRIBE_SECRET: str = ""
    OUTREACH_UNSUBSCRIBE_TOKEN_DAYS: int = 365
    INBOUND_REPLY_ENABLED: bool = False
    OUTREACH_INBOUND_DOMAIN: str = ""
    OUTREACH_INBOUND_SECRET: str = ""
    INBOUND_REPLY_MAX_WEBHOOK_BYTES: int = 262144
    INBOUND_REPLY_MAX_FETCH_BYTES: int = 1048576
    INBOUND_REPLY_MAX_BODY_CHARS: int = 50000
    INBOUND_REPLY_MAX_ATTACHMENTS: int = 20
    INBOUND_REPLY_MAX_ATTACHMENT_BYTES: int = 26214400
    # Internal notifications are delivered only to exact addresses or domains
    # listed here. This prevents an RFQ assignee field from becoming an
    # accidental external-recipient path.
    EMAIL_INTERNAL_RECIPIENT_ALLOWLIST: str = ""
    # Comma-separated addresses or domains permitted by the admin test-email
    # endpoint while live delivery is enabled.
    EMAIL_TEST_RECIPIENT_ALLOWLIST: str = ""
    SALES_NOTIFY_EMAIL: str = ""
    MANAGER_EMAIL: str = ""

    # Synthetic smoke tests may mark their data without allowing an arbitrary
    # public visitor to hide real activity from reporting.
    SYNTHETIC_TEST_TOKEN: str = ""

    # Off-site backup readiness. Assets and backups may use separate buckets.
    BACKUP_S3_ENDPOINT_URL: str = ""
    BACKUP_S3_ACCESS_KEY_ID: str = ""
    BACKUP_S3_SECRET_ACCESS_KEY: str = ""
    BACKUP_S3_BUCKET_NAME: str = ""
    BACKUP_ENCRYPTION_KEY: str = ""
    RECOVERY_EVIDENCE_FILE: str = "/recovery-evidence/status.json"

    # Google Search Console
    GSC_SERVICE_ACCOUNT_KEY_JSON: str = ""   # JSON string of service account credentials
    GSC_SITE_URL: str = ""                   # e.g. "https://example.com/"

    # ESP — Email Service Provider (2.4.3)
    # Active transactional provider: "resend" | "sendgrid"
    ESP_PROVIDER: str = "resend"
    # SendGrid
    SENDGRID_API_KEY: str = ""
    SENDGRID_LIST_ID: str = ""               # SendGrid Marketing contact list ID
    # Mailchimp (list management + tags)
    MAILCHIMP_API_KEY: str = ""              # Format: "<key>-<dc>" e.g. "abc123-us1"
    MAILCHIMP_AUDIENCE_ID: str = ""          # Mailchimp Audience / List ID

    # Encryption — used for storing integration credentials in DB
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_MASTER_KEY: str = ""

    # App
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    ADMIN_URL: str = "http://localhost:3001"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Registration
    REGISTRATION_KEY: str = ""  # If empty, public registration is disabled

    # Service account tokens for machine-to-machine auth (e.g. ContentFlow)
    # Format: comma-separated "<token>:<user_id>" pairs
    # Example: "cftoken123:550e8400-e29b-41d4-a716-446655440000"
    SERVICE_ACCOUNT_TOKENS: str = ""

    # Web 前台 on-demand revalidate（CF→FB Publish Contract §8）
    WEB_REVALIDATE_URL: str = ""        # e.g. https://www.client.com/api/revalidate
    WEB_REVALIDATE_URLS: str = ""       # comma-separated; overrides URL when set
    WEB_REVALIDATE_SECRET: str = ""     # 與 web 端 REVALIDATE_SECRET 相同

    # Admin seed
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = ""

    # Langfuse observability (optional — all three must be set to enable tracing)
    # Values come from the project created by LANGFUSE_INIT_PROJECT_* on first boot.
    # LANGFUSE_HOST example: http://localhost:3030 (local) or https://langfuse.your-domain.com
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_HOST: str = ""

    # AI Copilot — Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # AgentOS integration (Condition 1: auto-trigger RFQ workflows)
    AGENTOSS_URL: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def _validate_production_settings() -> None:
    if not settings.is_production:
        return

    localhost_prefixes = ("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1")
    production_urls = {
        "APP_URL": settings.APP_URL,
        "FRONTEND_URL": settings.FRONTEND_URL,
        "ADMIN_URL": settings.ADMIN_URL,
    }
    invalid_urls = [name for name, value in production_urls.items() if value.startswith(localhost_prefixes)]
    invalid_origins = [origin for origin in settings.allowed_origins_list if origin.startswith(localhost_prefixes)]

    if invalid_urls or invalid_origins:
        details = []
        if invalid_urls:
            details.append(f"dev URLs in production: {', '.join(invalid_urls)}")
        if invalid_origins:
            details.append(f"dev CORS origins in production: {', '.join(invalid_origins)}")
        raise RuntimeError("Invalid production settings — " + "; ".join(details))

    # Ensure ENCRYPTION_MASTER_KEY is usable — fail before the first encrypted write.
    if not settings.ENCRYPTION_MASTER_KEY:
        raise RuntimeError(
            "ENCRYPTION_MASTER_KEY must be set in production. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    from app.core.encryption import normalize_fernet_key

    try:
        normalize_fernet_key(settings.ENCRYPTION_MASTER_KEY)
    except ValueError as exc:
        raise RuntimeError(
            "ENCRYPTION_MASTER_KEY must be a URL-safe base64-encoded 32-byte key. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        ) from exc

    # Ensure Telegram webhook secret is set when bot token is configured
    if settings.TELEGRAM_BOT_TOKEN and not settings.TELEGRAM_WEBHOOK_SECRET:
        raise RuntimeError(
            "TELEGRAM_WEBHOOK_SECRET must be set in production when TELEGRAM_BOT_TOKEN is configured. "
            "This prevents unauthenticated webhook injection."
        )

    if settings.CHAT_ENABLED and not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY must be set in production when CHAT_ENABLED is true.")
    if (
        settings.CHAT_ENABLED
        and not settings.PUBLIC_TENANT_SLUG
        and settings.PUBLIC_TENANT_HEADER_COMPATIBILITY_ENABLED
    ):
        raise RuntimeError(
            "PUBLIC_TENANT_SLUG must be set in production while public tenant header compatibility is enabled."
        )

    if not settings.PUBLIC_TENANT_HEADER_COMPATIBILITY_ENABLED and len(settings.TENANT_ROUTING_SECRET) < 32:
        raise RuntimeError(
            "TENANT_ROUTING_SECRET must contain at least 32 characters in production "
            "when public tenant header compatibility is disabled."
        )


_validate_production_settings()
