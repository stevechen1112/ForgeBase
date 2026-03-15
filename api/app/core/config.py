from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OpenAI
    OPENAI_API_KEY: str
    AI_MODEL_NAME: str = "gpt-5.4"

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

    # IP-to-Company enrichment (2.1.2, 2.1.3)
    CLEARBIT_API_KEY: str = ""  # Clearbit Reveal API key (optional)

    # LinkedIn Marketing API (2.1.6)
    LINKEDIN_ACCESS_TOKEN: str = ""
    LINKEDIN_AD_ACCOUNT_ID: str = ""

    # Google Search Console (2.3.4)
    GSC_SERVICE_ACCOUNT_KEY_JSON: str = ""   # JSON string of service account credentials
    GSC_SITE_URL: str = ""                   # e.g. "https://example.com/"

    # Salesforce CRM (2.4.1)
    SF_CLIENT_ID: str = ""
    SF_CLIENT_SECRET: str = ""
    SF_USERNAME: str = ""
    SF_PASSWORD: str = ""
    SF_SECURITY_TOKEN: str = ""
    SF_INSTANCE_URL: str = ""                # e.g. "https://yourorg.my.salesforce.com"

    # ESP — Email Service Provider (2.4.3)
    # Active transactional provider: "resend" | "sendgrid"
    ESP_PROVIDER: str = "resend"
    # SendGrid
    SENDGRID_API_KEY: str = ""
    SENDGRID_LIST_ID: str = ""               # SendGrid Marketing contact list ID
    # Mailchimp (list management + tags)
    MAILCHIMP_API_KEY: str = ""              # Format: "<key>-<dc>" e.g. "abc123-us1"
    MAILCHIMP_AUDIENCE_ID: str = ""          # Mailchimp Audience / List ID

    # App
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    ADMIN_URL: str = "http://localhost:3001"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Admin seed
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = ""

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
