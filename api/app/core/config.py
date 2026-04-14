from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # LLM provider
    AI_PROVIDER: str = "gemini"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    AI_MODEL_NAME: str = "gemini-3-flash-preview"

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "forgebase-assets"
    R2_PUBLIC_URL: str = ""

    # Resend
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "ForgeBase"

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

    # PayPal Subscriptions
    PAYPAL_MODE: str = "sandbox"  # "sandbox" | "live"
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""
    PAYPAL_STARTER_PLAN_ID: str = ""
    PAYPAL_PROFESSIONAL_PLAN_ID: str = ""

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

    @property
    def allowed_origins_list(self) -> List[str]:
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


_validate_production_settings()
