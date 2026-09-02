from fastapi import APIRouter, Depends

from app.api.v1.deps import RequireFeature
from app.api.v1.endpoints import (
    adoption_applications,
    analytics,
    assets,
    auth,
    categories,
    capability_access,
    chat,
    chat_admin,
    company_identification,
    contact_enrichment,
    contacts,
    events,
    growth_ops,
    inbound_replies,
    locale_draft,
    locale_quality,
    notifications,
    nurture,
    orphans,
    outreach,
    page_meta,
    platform_admin,
    preview,
    privacy,
    products,
    public_relations,
    publish,
    redirects,
    relations,
    retirement_audit,
    rfqs,
    segments,
    site_profile,
    site_domain_routing,
    tenant_domains_admin,
    visitors,
    webhooks,
)
from app.api.v1.endpoints.ai_intelligence import (
    content_ai_router,
    rfq_ai_router,
    visitor_ai_router,
)
from app.api.v1.endpoints.content_crud import (
    applications_router,
    capabilities_router,
    certifications_router,
    comparisons_router,
    ctas_router,
    faqs_router,
    pages_router,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(capability_access.router)
api_router.include_router(platform_admin.router)  # Platform super-admin
api_router.include_router(retirement_audit.router)  # Safe-retirement evidence gate
api_router.include_router(company_identification.router)  # Platform Shadow Mode
api_router.include_router(
    contact_enrichment.router
)  # Review-only company contact candidates
api_router.include_router(
    outreach.router
)  # Review and human-approved outreach delivery
api_router.include_router(
    outreach.public_router
)  # Signed unsubscribe confirmation/one-click
api_router.include_router(
    inbound_replies.admin_router
)  # Platform review of unlinked replies
api_router.include_router(adoption_applications.admin_router)
api_router.include_router(notifications.router)

# Content CRUD — all under /api/v1/content/
content_router = APIRouter(prefix="/content")
content_router.include_router(categories.router)
content_router.include_router(products.router)
content_router.include_router(applications_router)
content_router.include_router(faqs_router)
content_router.include_router(comparisons_router)
content_router.include_router(certifications_router)
content_router.include_router(capabilities_router)
content_router.include_router(ctas_router)
content_router.include_router(pages_router)
content_router.include_router(page_meta.router)
content_router.include_router(assets.router)
content_router.include_router(relations.router)
content_router.include_router(publish.router)
content_router.include_router(locale_draft.router)
content_router.include_router(orphans.router)
content_router.include_router(public_relations.router)
content_router.include_router(preview.router)
content_router.include_router(
    redirects.router
)  # /content/redirects/* SEO redirect mgmt
content_router.include_router(locale_quality.router)
api_router.include_router(content_router)

# Buyer activity and follow-up — /api/v1/tracking/
tracking_router = APIRouter()
tracking_router.include_router(events.router)  # /tracking/events
tracking_router.include_router(
    visitors.router
)  # /tracking/visitors, /tracking/sessions
tracking_router.include_router(contacts.tracking_router)  # /tracking/contacts
tracking_router.include_router(rfqs.tracking_router)  # /tracking/rfqs
tracking_router.include_router(
    inbound_replies.tracking_router
)  # /tracking/replies, handoffs
tracking_router.include_router(segments.router)  # /tracking/segments
tracking_router.include_router(analytics.router)  # /tracking/analytics/*
tracking_router.include_router(
    nurture.router, dependencies=[Depends(RequireFeature("nurture_email"))]
)  # /tracking/nurture/*
api_router.include_router(tracking_router)
api_router.include_router(growth_ops.ops_router)  # /ops/task-queue

# AI intelligence — RFQ / visitor / dynamic CTA (content factory removed)
api_router.include_router(rfq_ai_router)  # /tracking/rfqs/{id}/analyze, /draft-reply
api_router.include_router(visitor_ai_router)  # /tracking/visitors/{id}/recommend-cta
api_router.include_router(
    content_ai_router
)  # /content/dynamic-cta, /recommend-relations

# Public conversion forms — /api/v1/forms/
forms_router = APIRouter()
forms_router.include_router(contacts.forms_router)  # /forms/contact
forms_router.include_router(rfqs.forms_router)  # /forms/rfq
forms_router.include_router(adoption_applications.forms_router)  # /forms/adoption
api_router.include_router(forms_router)

# Chat MVP — /api/v1/chat/*
api_router.include_router(chat.router)
api_router.include_router(chat_admin.router)

# Site Profile — /api/v1/site-profile
api_router.include_router(site_profile.router)
api_router.include_router(site_domain_routing.router)
api_router.include_router(tenant_domains_admin.router)
api_router.include_router(privacy.router)
api_router.include_router(webhooks.router)
