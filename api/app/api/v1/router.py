from fastapi import APIRouter
from app.api.v1.endpoints import auth, categories, products
from app.api.v1.endpoints.content_crud import (
    applications_router,
    faqs_router,
    comparisons_router,
    certifications_router,
    capabilities_router,
    ctas_router,
    pages_router,
    briefs_router,
)
from app.api.v1.endpoints import (
    strategy, ai_generate, assets, relations, publish, orphans,
    public_relations, preview,
    events, visitors, contacts, rfqs, integrations, segments, accounts, nurture,
    linkedin_audiences, seo_audit, seo_optimize, crm, esp, ab_test, analytics,
    ml_scoring, chat, redirects, intake,
)
from app.api.v1.endpoints.ai_intelligence import (
    rfq_ai_router, content_ai_router, visitor_ai_router, nurture_ai_router,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)

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
content_router.include_router(briefs_router)
content_router.include_router(strategy.router)
content_router.include_router(ai_generate.router)
content_router.include_router(assets.router)
content_router.include_router(relations.router)
content_router.include_router(publish.router)
content_router.include_router(orphans.router)
content_router.include_router(public_relations.router)
content_router.include_router(preview.router)
content_router.include_router(seo_audit.router)    # /content/seo-audit/* (2.3.4)
content_router.include_router(seo_optimize.router)  # /content/seo-audit/optimize (2.3.5)
content_router.include_router(redirects.router)     # /content/redirects/* SEO redirect mgmt
api_router.include_router(content_router)

# Phase 1b: Tracking — /api/v1/tracking/
tracking_router = APIRouter()
tracking_router.include_router(events.router)       # /tracking/events
tracking_router.include_router(visitors.router)     # /tracking/visitors, /tracking/sessions, /tracking/audiences
tracking_router.include_router(accounts.router)     # /tracking/accounts
tracking_router.include_router(contacts.tracking_router)   # /tracking/contacts
tracking_router.include_router(rfqs.tracking_router)       # /tracking/rfqs
tracking_router.include_router(segments.router)            # /tracking/segments
tracking_router.include_router(nurture.router)             # /nurture/sequences, /nurture/enroll
tracking_router.include_router(linkedin_audiences.router)  # /tracking/linkedin-audiences
tracking_router.include_router(crm.router)                 # /tracking/crm/*
tracking_router.include_router(esp.router)                 # /tracking/esp/* (2.4.3)
tracking_router.include_router(ab_test.router)             # /tracking/ab-tests/* (2.5.4)
tracking_router.include_router(analytics.router)           # /tracking/analytics/* (2.5.x)
api_router.include_router(tracking_router)

# Phase 3: AI Intelligence — full paths defined in each router
api_router.include_router(rfq_ai_router)       # /tracking/rfqs/{id}/analyze, /draft-reply
api_router.include_router(visitor_ai_router)   # /tracking/visitors/{id}/recommend-cta, /accounts/{id}/insight
api_router.include_router(content_ai_router)   # /content/intelligence/optimize, /dynamic-cta, /recommend-relations
api_router.include_router(nurture_ai_router)   # /nurture/sequences/{id}/optimize
api_router.include_router(ml_scoring.router)   # /tracking/ml/*

# Phase 1b: Public Forms — /api/v1/forms/
forms_router = APIRouter()
forms_router.include_router(contacts.forms_router)  # /forms/contact
forms_router.include_router(rfqs.forms_router)      # /forms/rfq
api_router.include_router(forms_router)

# Chat MVP — /api/v1/chat/*
api_router.include_router(chat.router)

# Legacy Site Intake — /api/v1/intake/*
api_router.include_router(intake.router)

# Phase 1b: Admin utilities — /api/v1/admin/
api_router.include_router(integrations.router)      # /admin/integrations/status
