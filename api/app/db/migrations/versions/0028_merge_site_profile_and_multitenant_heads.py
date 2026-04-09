"""0028_merge_site_profile_and_multitenant_heads

Merge the site-profile/intake branch with the multi-tenant SaaS branch so the
migration graph has a single head for production deploys.
"""

revision = "0028_merge_site_profile_and_multitenant_heads"
down_revision = (
    "0026_site_profile",
    "0027_add_tenant_id_to_core_models",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass