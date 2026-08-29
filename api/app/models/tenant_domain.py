import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive

DOMAIN_TYPES = {"forgebase_subdomain", "custom"}
DOMAIN_STATUSES = {
    "pending",
    "verifying",
    "verified",
    "active",
    "failed",
    "suspended",
}
TLS_STATUSES = {"unknown", "pending", "issuing", "active", "failed"}


class TenantDomain(SQLModel, table=True):
    """A public hostname assigned to exactly one tenant.

    SiteBuild.primary_domain and SiteProfile.site_url remain compatibility
    projections while domain lifecycle management moves to this table.
    """

    __tablename__ = "tenant_domains"
    __table_args__ = (
        UniqueConstraint("hostname", name="uq_tenant_domains_hostname"),
        CheckConstraint(
            "domain_type IN ('forgebase_subdomain', 'custom')",
            name="ck_tenant_domains_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'verifying', 'verified', 'active', 'failed', 'suspended')",
            name="ck_tenant_domains_status",
        ),
        CheckConstraint(
            "tls_status IN ('unknown', 'pending', 'issuing', 'active', 'failed')",
            name="ck_tenant_domains_tls_status",
        ),
        Index(
            "uq_tenant_domains_canonical_per_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_canonical"),
            sqlite_where=text("is_canonical = 1"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    hostname: str = Field(max_length=253)
    domain_type: str = Field(default="custom", max_length=32, index=True)
    status: str = Field(default="pending", max_length=32, index=True)
    is_canonical: bool = Field(default=False)

    verification_method: str | None = Field(default=None, max_length=40)
    verification_token: str | None = Field(default=None, max_length=255)
    dns_target: str | None = Field(default=None, max_length=253)
    dns_observed_json: str = Field(default="{}")
    dns_verified_at: datetime | None = Field(default=None)

    tls_status: str = Field(default="unknown", max_length=20, index=True)
    tls_issued_at: datetime | None = Field(default=None)
    activated_at: datetime | None = Field(default=None)
    last_checked_at: datetime | None = Field(default=None, index=True)
    failure_reason: str | None = Field(default=None, max_length=1000)
    redirect_to_canonical: bool = Field(default=True)

    created_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", index=True
    )
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
