"""Idempotently provision the connected AxisForm precision-machining demo tenant.

The owner account receives an unrecorded random password. This script creates
test content and a published SiteBuild; it does not send mail or contact leads.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import sys
from pathlib import Path
from typing import Any

from sqlmodel import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.models  # noqa: F401 - register every SQLModel relationship before mapper setup
from app.core.datetime import utcnow_naive
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.cta import CTA
from app.models.faq_item import FAQItem
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.tenant import Tenant
from app.models.user import User
from app.models.associations import ProductApplicationLink, ProductCertificationLink, ProductFAQLink
from app.services.site_provisioning import validate_and_store_readiness


TENANT_SLUG = "axisform-precision"
SITE_HOST = "axisform.172-233-64-5.sslip.io"
SITE_URL = f"https://{SITE_HOST}"
ASSET_BASE = "/demo/precision-machining/assets"


SITE_COPY: dict[str, Any] = {
    "common": {"brandName": "AxisForm Precision", "home": "Home"},
    "header": {
        "rfq": "Send a drawing", "submitRfq": "Send a drawing", "contact": "Contact",
        "partnerTitle": "Precision machining demonstration", "partnerDescription": "A connected ForgeBase test tenant with isolated content and enquiries.",
        "nav": {"products": "Parts", "applications": "Industries", "certifications": "Quality", "about": "About", "contact": "Contact"},
    },
    "footer": {
        "description": "Connected demonstration tenant for precision-machining sourcing journeys. No manufacturing or certification claim is made.",
        "builtWithPrecision": "Structured for drawing-led enquiries", "certifications": ["DEMO QMS", "DEMO FAIR", "DEMO TRACEABILITY"],
        "footerCta": {"title": "Have a part to review?", "description": "Send material, tolerance, volume and target timing for a test RFQ.", "requestQuote": "Send a drawing"},
    },
    "chat": {
        "desktopButton": "Ask Machining Advisor", "mobileButton": "Ask Advisor", "title": "AI Machining Advisor",
        "subtitle": "Ask about the fictional parts, materials, tolerance examples or the RFQ process.",
        "placeholder": "Ask about a part, tolerance, material, or RFQ...",
        "greeting": "I can help you review the published fictional part, material, tolerance, inspection context, or RFQ process.",
        "suggestions": ["What material and tolerance are shown for this part?", "What inspection evidence is described?", "What should I include with a drawing-led RFQ?"],
    },
    "forms": {
        "contact": {
            "successTitle": "Test message recorded",
            "successDescription": "The message is stored in the isolated AxisForm test tenant. No sales reply will be sent.",
            "submit": "Send test message",
            "labels": {"message": "Test question or requirement"},
            "placeholders": {
                "company": "Fictional test company",
                "phone": "Optional; do not enter a real personal number",
                "message": "Ask about a fictional part, machining process, inspection record, or RFQ workflow.",
            },
        },
        "rfq": {
            "successTitle": "Test RFQ recorded",
            "successDescription": "The RFQ is stored for controlled workflow verification. No quotation or sales reply will be sent.",
            "submit": "Submit test RFQ",
            "footerNote": "Use fictional test data only. Submission is retained for ForgeBase workflow verification and will not receive a sales reply.",
            "labels": {
                "quantity": "Prototype / Production Quantity",
                "specifications": "Drawing, Material, Tolerance and Finish",
                "timeline": "Target Test Timeline",
                "message": "Additional Test Context",
                "consent": "I understand this is a functional test and consent to storing this synthetic enquiry data. *",
            },
            "placeholders": {
                "quantity": "e.g. 10 prototypes, then 1,000 demo units/year",
                "specifications": "State a fictional part or drawing revision, material, critical tolerance, finish, inspection need and target process.",
                "message": "Add fictional end-use, lot identification, inspection or delivery context. Do not submit confidential drawings.",
                "annualVolume": "e.g. 1,000 demo units/year",
                "targetPrice": "Test-only target; no quotation will be issued",
            },
        },
    },
    "home": {
        "metadata": {"title": "AxisForm Precision | Connected ForgeBase Demo", "description": "A dynamic precision-machining demonstration tenant powered by ForgeBase."},
        "hero": {"eyebrow": "CNC Machining / Connected Demo", "titleLine1": "Tolerance is a number.", "titleLine2": "Confidence is a system.", "description": "Fictional precision-machining content, structured around the evidence a sourcing team needs before releasing a drawing.", "primaryCta": "Send your drawing", "secondaryCta": "Review parts"},
        "stats": [{"value": "±0.010", "label": "mm demo tolerance"}, {"value": "3–5 axis", "label": "process concepts"}, {"value": "FAIR", "label": "inspection workflow"}, {"value": "100%", "label": "fictional test data"}],
        "featured": {"eyebrow": "Representative parts", "title": "Show the work at engineering resolution", "description": "Structured fictional component records demonstrate how products, specifications and RFQ context stay connected.", "cardCta": "Review part", "sectionCta": "Browse all parts"},
        "catalogue": {"eyebrow": "Part families", "title": "Browse by process", "description": "Separate milled and turned component concepts.", "sectionCta": "Browse catalogue"},
        "why": {"eyebrow": "Manufacturing system", "title": "Evidence before promises", "description": "This connected template puts process, specification and inspection context before unsupported claims.", "items": [{"title": "Drawing and revision review", "desc": "Capture the drawing, revision, material and commercial context in one RFQ record."}, {"title": "Process-linked presentation", "desc": "Connect representative parts to their process, industry and structured specifications."}, {"title": "Documented inspection", "desc": "Explain fictional CMM, FAIR and traceability workflows without claiming certification."}, {"title": "Tenant-isolated enquiries", "desc": "AxisForm visitors, chats and RFQs stay separate from NorthForge records."}, {"title": "Buyer intent signals", "desc": "Product views and RFQ actions feed the same ForgeBase intent model."}, {"title": "Closed-loop handling", "desc": "RFQ quality, tasks and outcomes can be verified without sending sales replies."}]},
        "applications": {"eyebrow": "Industry fit", "title": "Context for technical sourcing", "description": "Fictional applications link parts to automation, mobility and instrumentation buying questions.", "sectionCta": "Review industries"},
        "oem": {"eyebrow": "Drawing-led RFQ", "title": "Move from requirement to review", "description": "The workflow captures the information needed for a structured manufacturing review.", "steps": [{"title": "Share requirements", "desc": "Part, material, tolerance, volume and timing."}, {"title": "Review context", "desc": "ForgeBase stores the enquiry and related behaviour."}, {"title": "Qualify", "desc": "Quality and intent signals support prioritisation."}, {"title": "Track outcome", "desc": "Tasks and outcomes close the measurement loop."}]},
        "certifications": {"eyebrow": "Quality narrative", "title": "Make risk reduction visible", "description": "Every credential shown here is explicitly fictional and exists only to test content and document handling.", "sectionCta": "Review quality records"},
        "finalCta": {"title": "Start with the part, not a generic contact form", "description": "Open a complete test RFQ and verify the connected ForgeBase workflow end to end.", "primaryCta": "Send a drawing", "secondaryCta": "Ask a question", "note": "Functional test only. No quotation or sales reply will be sent."},
    },
    "products": {
        "metadata": {"title": "Precision machined parts", "description": "Fictional connected part catalogue."}, "breadcrumb": "Parts", "heroTitle": "Precision machined parts", "heroDescription": "Fictional milled and turned component concepts with structured specifications.",
        "highlights": [{"label": "Milling", "desc": "multi-face concepts"}, {"label": "Turning", "desc": "thin-wall concepts"}, {"label": "Materials", "desc": "aluminium and stainless"}, {"label": "Evidence", "desc": "structured demo records"}],
        "browseLabel": "Part families", "categoriesTitle": "Browse by process", "contactCta": "Discuss a requirement", "emptyState": "No parts are published.", "emptyCta": "Contact the test team", "viewProducts": "View parts", "customTitle": "Need a different geometry?", "customDescription": "Use the RFQ to test a drawing-led request.", "customCta": "Send a drawing", "talkCta": "Ask a question",
    },
    "productCategory": {"products":"Parts","buyerFocusTitle":"Engineering focus","buyerFocusDescription":"Use this page to narrow the machining process, material and geometry before opening a drawing-led RFQ.","typicalQuestionsTitle":"Typical sourcing questions","typicalQuestionsDescription":"Buyers usually compare critical tolerance, finish, inspection evidence, expected volume and prototype-to-production timing.","fasterAnswerTitle":"Have a drawing ready?","fasterAnswerDescription":"Move directly to RFQ and include the drawing revision, material, critical features and target volume.","searchPlaceholder":"Search","productCount":"part","productCountPlural":"parts","matching":"matching","filteredNotice":"A filtered catalogue view is active.","viewAllProducts":"View all parts","noProducts":"No parts are published in this family.","noProductsFound":"No parts match","prev":"Previous","next":"Next","page":"Page"},
    "productDetail": {"products":"Parts","introBox":"Representative fictional part record for workflow testing.","overview":"Part overview","inspectionTitle":"Inspection context","inspectionDescription":"Critical features, revision and measurement evidence can be attached to the same ForgeBase record. Demonstration only.","packagingTitle":"Delivery context","packagingDescription":"Use the RFQ to capture finish protection, lot identification and destination requirements.","readinessTitle":"Drawing readiness","readinessDescription":"Confirm revision, material, finish, tolerance, volume and target timing before review.","specControlTitle":"Specification control","specControlDescription":"Structured specifications reduce ambiguity between the public page and RFQ record.","contextTitle":"Application context","contextDescription":"Related industries and technical questions remain linked to this part.","specsTitle":"Demonstration specifications","faqTitle":"Questions about this part","appTitle":"Related industries","appLearnMore":"Review industry","certTitle":"Quality records","beforeRfqTitle":"Before sending the drawing","beforeRfqDescription":"Add these inputs so the test RFQ can be qualified consistently.","rfqItems":[{"label":"Drawing and revision","detail":"Use an obvious fictional file or description for testing."},{"label":"Material and finish","detail":"State grade, heat treatment and surface requirement."},{"label":"Critical dimensions","detail":"Identify tolerance, datum and inspection expectation."},{"label":"Volume and timing","detail":"Separate prototype need from recurring demand."}],"submitRfq":"Send a drawing","askFirst":"Ask the advisor"},
    "applications": {"metadata":{"title":"Industry applications","description":"Fictional technical applications connected to AxisForm parts."},"breadcrumb":"Industries","title":"Industry applications","description":"Review how the fictional part records map to automation, mobility and instrumentation sourcing questions.","emptyState":"No applications are published.","fallbackIndustry":"Other"},
    "applicationDetail": {"applications":"Industries","prompts":["Which drawing features drive the process choice?","What inspection evidence reduces sourcing risk?","What changes between prototype and recurring production?"],"challenge":"Sourcing challenge","solution":"Structured response","verificationTitle":"Inspection and traceability","verificationDescription":"Link the application need to a revision-controlled part, measurement plan and fictional evidence record.","packagingTitle":"Handling and delivery","packagingDescription":"Capture surface protection, lot identification and destination context in RFQ.","sourcingTitle":"Before requesting review","sourcingDescription":"Provide the information needed to qualify the request.","sourcingItems":[{"label":"Part context","detail":"Drawing, revision and end use."},{"label":"Critical requirements","detail":"Material, tolerance, finish and inspection."},{"label":"Commercial context","detail":"Prototype quantity, annual volume and target timing."}],"quoteCta":"Send a drawing","planCta":"Ask a question","allApplications":"All industries","relatedProductsTitle":"Related part concepts","relatedProductsDescription":"Fictional parts connected to this application.","viewProduct":"Review part","faqTitle":"Application questions"},
    "certifications": {"metadata":{"title":"Quality records","description":"Explicitly fictional quality and traceability records."},"breadcrumb":"Quality","title":"Quality records and process evidence","description":"Every item on this page is demonstration content. AxisForm claims no real certification, audit or manufacturing approval.","emptyState":"No demonstration records are published.","overviewTitle":"How credentials should be presented","overviewDescription":"A production tenant can publish verified certificates, scope, issuer, number, dates and controlled documents. This test tenant intentionally uses no real credential.","items":[{"type":"Quality framework","detail":"Illustrative QMS narrative only.","note":"DEMO","color":"lime","badge":"QMS"},{"type":"Inspection workflow","detail":"Illustrative FAIR and CMM evidence flow.","note":"DEMO","color":"lime","badge":"FAIR"},{"type":"Traceability","detail":"Illustrative material and lot record flow.","note":"DEMO","color":"lime","badge":"LOT"}],"availabilityNote":"Need to test a credential request?","availabilityCta":"Use the contact form","commitmentTitle":"No unsupported claim","commitmentDescription":"No certificate shown by AxisForm represents a real approval or factory capability.","commitmentCta":"Ask about the demo"},
    "certificationDetail": {"certifications":"Quality","issuedBy":"Demonstration source:","noBadge":"No badge — demonstration record","whyTitle":"Why this record exists","whyDescription":"This record verifies ForgeBase credential fields and buyer navigation without claiming a real certificate.","fallbackDescription":"Demonstration quality record only.","certificateNo":"Certificate number","locale":"Locale","issued":"Issued","expires":"Expires","download":"Open demo document","askHow":"Ask about this workflow"},
    "contactPage": {"metadata":{"title":"Contact AxisForm demo","description":"Functional test contact page; no sales follow-up."},"breadcrumb":"Contact","title":"Contact the AxisForm test tenant","description":"Use fictional information only. Messages are captured to verify the isolated ForgeBase workflow and will not receive a sales reply.","reasonsTitle":"What you can test","reasons":[{"label":"Part question","desc":"Ask about a published fictional part."},{"label":"Process question","desc":"Ask about public demo capability content."},{"label":"RFQ handoff","desc":"Move a structured test requirement into RFQ."}],"officesTitle":"Demonstration location","offices":[{"city":"Test environment","address":"No physical factory or office is represented","phone":"+00 000 000 000","hours":"No sales response service"}],"responseTitle":"No outbound follow-up","responseDescription":"Submissions remain in ForgeBase for controlled product verification only.","formTitle":"Send a test message","formDescription":"Do not submit confidential, personal or real procurement information.","quickLinksPrompt":"Prefer a structured path?","quickLinks":{"products":"Browse parts","certifications":"Review quality","rfq":"Send a drawing"}},
    "rfqPage": {"metadata": {"title": "Send a drawing", "description": "Submit a functional test RFQ to the isolated AxisForm tenant."}, "title": "Send a drawing for manufacturing review", "description": "Provide fictional test requirements only. The record will be captured and qualified, but no sales reply will be sent.", "builtForTitle": "Useful input", "builtForItems": ["Material and finish", "Critical tolerance", "Prototype or annual volume", "Target timing and destination"], "helpTitle": "Not ready to submit?", "helpDescription": "Use the AI advisor to review the public demo content first.", "helpCta": "Ask a question", "responseWindowLabel": "Test environment", "responseWindowTime": "No reply", "responseWindowHours": "Submission is retained only for workflow verification."},
    "about": {
        "metadata": {"title": "About AxisForm Precision Demo", "description": "Fictional connected precision-machining tenant."}, "breadcrumb": "About", "heroTitle": "About AxisForm Precision", "heroDescription": "AxisForm is a fictional company used to verify a second ForgeBase tenant. It is not a registered manufacturer.",
        "stats": [{"value": "DEMO", "label": "Company status"}, {"value": "3", "label": "Part concepts"}, {"value": "3", "label": "Process narratives"}, {"value": "0", "label": "Real credentials claimed"}], "ourStory": "Purpose", "storyTitle": "A realistic test site without a false factory claim", "talkTeam": "Open test contact", "whatWeMake": "Representative scope", "productLinesTitle": "Fictional part families", "ourJourney": "Delivery", "milestones": "Test milestones", "strengthsEyebrow": "System coverage", "strengthsTitle": "What this tenant verifies", "capabilitiesEyebrow": "Process content", "capabilitiesTitle": "Machining capabilities", "certificationsEyebrow": "Quality content", "certificationsTitle": "Demonstration credentials", "ctaTitle": "Test the connected workflow", "ctaDescription": "Browse a part, ask the advisor and submit an obvious test RFQ.", "contactTeam": "Contact", "browseProducts": "Browse parts",
        "productLines": [{"title": "Milled components", "desc": "Multi-face aluminium component concepts."}, {"title": "Turned components", "desc": "Concentric and thin-wall component concepts."}, {"title": "Inspection planning", "desc": "Fictional FAIR, CMM and traceability narratives."}],
        "timeline": [{"year": "01", "event": "Template selected and adapted to the ForgeBase content model."}, {"year": "02", "event": "Tenant-specific content, assets and domain connected."}, {"year": "03", "event": "Visitor, chat, RFQ and outcome isolation verified."}],
        "operationalStrengths": [{"title": "Independent CMS", "desc": "AxisForm content does not use NorthForge records."}, {"title": "Independent identity", "desc": "Brand, host, theme and copy resolve from the tenant profile."}, {"title": "Independent conversion", "desc": "Chats and RFQs are written to the AxisForm tenant."}, {"title": "Honest disclosure", "desc": "All company and capability claims are marked as fictional."}],
        "storyParagraphs": ["AxisForm exists only as a connected product test case. It demonstrates how a precision-machining supplier site can use ForgeBase without representing a real factory.", "The public traffic and behaviour can be real, while the company, products, capacity and credentials remain clearly disclosed test content."]
    },
}


async def _first(session, model, **filters):
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    return (await session.exec(stmt)).first()


async def _upsert(session, model, filters: dict[str, Any], values: dict[str, Any]):
    row = await _first(session, model, **filters)
    if row is None:
        row = model(**filters, **values)
    else:
        for key, value in values.items():
            setattr(row, key, value)
        if hasattr(row, "updated_at"):
            row.updated_at = utcnow_naive()
    session.add(row)
    await session.flush()
    return row


async def provision() -> None:
    async with AsyncSessionLocal() as session:
        tenant = await _first(session, Tenant, slug=TENANT_SLUG)
        if tenant is None:
            tenant = Tenant(name="AxisForm Precision Demo", slug=TENANT_SLUG, is_active=True)
            session.add(tenant)
            await session.flush()
        else:
            tenant.name, tenant.is_active = "AxisForm Precision Demo", True
            session.add(tenant)

        owner = await _first(session, User, email="owner@axisform-precision.test")
        if owner is None:
            owner = User(tenant_id=tenant.id, email="owner@axisform-precision.test", full_name="AxisForm Demo Owner", hashed_password=get_password_hash(secrets.token_urlsafe(48)), role="owner", is_active=True)
        else:
            owner.tenant_id, owner.role, owner.is_active = tenant.id, "owner", True
        session.add(owner)

        profile_values = dict(brand_name="AxisForm Precision", logo_mark="AF", theme_key="precision", layout_key="precision", contact_email="demo@example.com", contact_phone="+00 000 000 000", site_url=SITE_URL, default_locale="en", asset_base=ASSET_BASE, demo_company_folder="precision-machining",
            header_nav_json=json.dumps([{"href":"/products","label":"Parts"},{"href":"/applications","label":"Industries"},{"href":"/certifications","label":"Quality"},{"href":"/about","label":"About"}], ensure_ascii=False),
            header_actions_json=json.dumps([{"href":"/rfq","label":"Send a drawing"}], ensure_ascii=False),
            footer_sections_json=json.dumps([{"heading":"Explore","items":[{"href":"/products","label":"Parts"},{"href":"/applications","label":"Industries"},{"href":"/certifications","label":"Quality"},{"href":"/about","label":"About"}]}]),
            footer_badges_json=json.dumps(["DEMO QMS","DEMO FAIR","DEMO TRACEABILITY"]),
            footer_cta_title="Send a drawing", footer_cta_description="Create a functional test RFQ without a sales reply.", footer_cta_label="Open RFQ", footer_cta_href="/rfq",
            asset_manifest_json=json.dumps({"homeHero":f"{ASSET_BASE}/generated/home-hero-cnc-facility.png","aboutHero":f"{ASSET_BASE}/generated/capability-five-axis-machining.png","productsHero":f"{ASSET_BASE}/generated/parts-precision-components.png","qualityInspection":f"{ASSET_BASE}/generated/quality-cmm-inspection.png","customPackaging":f"{ASSET_BASE}/generated/capability-five-axis-machining.png","categoryBySlug":{"milled-parts":f"{ASSET_BASE}/generated/parts-precision-components.png","turned-parts":f"{ASSET_BASE}/generated/parts-precision-components.png"},"applicationBySlug":{"industrial-automation":f"{ASSET_BASE}/generated/capability-five-axis-machining.png","mobility-systems":f"{ASSET_BASE}/generated/parts-precision-components.png","instrumentation":f"{ASSET_BASE}/generated/quality-cmm-inspection.png"},"productByKey":{"DEMO-M01":f"{ASSET_BASE}/generated/parts-precision-components.png","DEMO-T08":f"{ASSET_BASE}/generated/parts-precision-components.png","DEMO-M14":f"{ASSET_BASE}/generated/parts-precision-components.png"}}, ensure_ascii=False),
            site_copy_json=json.dumps(SITE_COPY, ensure_ascii=False), ops_config_json=json.dumps({"auto_reply_enabled":False,"sla_response_hours":24}))
        await _upsert(session, SiteProfile, {"tenant_id": tenant.id}, profile_values)

        build = await _upsert(session, SiteBuild, {"tenant_id": tenant.id}, {"template_key":"precision-machining","status":"draft","primary_domain":SITE_HOST,"locales_json":json.dumps(["en"]),"customization_json":json.dumps({"adapter":"precision-machining-v1","disclosure":"fictional-test-company"}),"cms_connected":True,"readiness_json":"{}","last_error":None})

        categories = {}
        for order, (slug, name, desc) in enumerate([("milled-parts","Milled Components","Multi-face and position-critical component concepts."),("turned-parts","Turned Components","Concentric and thin-wall component concepts.")]):
            categories[slug] = await _upsert(session, ProductCategory, {"tenant_id":tenant.id,"slug":slug,"locale":"en"}, {"category_name":name,"description":desc,"image_url":f"{ASSET_BASE}/generated/parts-precision-components.png","sort_order":order,"status":"published","seo_title":name,"seo_description":desc})

        products = {}
        product_rows = [
            ("servo-housing","Servo Drive Housing","DEMO-M01","milled-parts","Multi-face aluminium housing concept with sealing and bearing features.",[["Material","Al 6061"],["Tolerance","±0.015 mm"],["Finish","Black anodized"]]),
            ("sensor-sleeve","Sensor Sleeve","DEMO-T08","turned-parts","Thin-wall turned component concept designed for concentricity control.",[["Material","SS 316L"],["Tolerance","±0.010 mm"],["Finish","Passivated"]]),
            ("robot-joint","Robot Joint Interface","DEMO-M14","milled-parts","Five-axis interface part concept with position-critical hole patterns.",[["Material","Al 7075"],["Tolerance","GD&T controlled"],["Finish","Hard anodized"]]),
        ]
        for priority, (slug,name,model,cat,desc,specs) in enumerate(product_rows,1):
            products[slug] = await _upsert(session, Product, {"tenant_id":tenant.id,"slug":slug,"locale":"en"}, {"product_name":name,"model_number":model,"short_description":desc,"full_description":f"<p>{desc}</p><p>Fictional component record for ForgeBase workflow testing.</p>","specifications":json.dumps([{"name":n,"value":v,"unit":""} for n,v in specs]),"category_id":categories[cat].id,"image_url":f"{ASSET_BASE}/generated/parts-precision-components.png","image_alt":f"Fictional {name.lower()} component concept","seo_title":name,"seo_description":desc,"status":"published","is_featured":True,"display_priority":priority,"published_at":utcnow_naive()})

        apps = {}
        for order,(slug,name,industry,desc) in enumerate([("industrial-automation","Industrial automation","Automation","Motion, sensing and machine-interface component concepts."),("mobility-systems","Mobility systems","Mobility","Prototype and production part concepts for electrified platforms."),("instrumentation","Instrumentation","Instrumentation","Compact part concepts where surfaces and concentricity matter.")]):
            apps[slug]=await _upsert(session, Application,{"tenant_id":tenant.id,"slug":slug,"locale":"en"},{"application_name":name,"industry":industry,"description":desc,"challenge":"Technical buyers need material, tolerance and inspection context before releasing a drawing.","solution":"Structured ForgeBase records connect the part, evidence and enquiry.","hero_image_url":f"{ASSET_BASE}/generated/capability-five-axis-machining.png","seo_title":name,"seo_description":desc,"status":"published","sort_order":order,"published_at":utcnow_naive()})

        for order,(slug,name,desc,metrics) in enumerate([("five-axis-milling","5-axis milling","Single-setup machining concepts for complex geometry.",[{"label":"Envelope","value":"Demo 600 × 500 × 450 mm"}]),("precision-turning","Precision turning","Turn-mill concepts for concentric, thin-wall features.",[{"label":"Diameter","value":"Demo Ø3–250 mm"}]),("quality-control","Documented inspection","Illustrative inspection planning, traceability and FAIR workflow.",[{"label":"Reporting","value":"FAIR / CMM / CoC"}])]):
            await _upsert(session,Capability,{"tenant_id":tenant.id,"slug":slug,"locale":"en"},{"capability_name":name,"short_description":desc,"detail":f"<p>{desc}</p><p>Demonstration capability only.</p>","metrics":json.dumps(metrics),"category_tag":"demo","sort_order":order,"status":"published","published_at":utcnow_naive()})

        certs = {}
        for slug,name,desc in [("example-qms","Example QMS framework","Demonstration only — no certification is claimed."),("material-traceability","Material traceability workflow","Illustrative process capability, not a credential.")]:
            certs[slug]=await _upsert(session,Certification,{"tenant_id":tenant.id,"slug":slug,"locale":"en"},{"cert_name":name,"issuer":"ForgeBase demonstration","cert_number":None,"description":desc,"badge_image_url":None,"document_url":None,"status":"published"})

        faqs={}
        for order,(key,q,a) in enumerate([("drawing-upload","Can I send a drawing?","Yes. Use the RFQ form with fictional test information. Attachments are stored with the tenant record; no quotation reply will be sent."),("tolerance","What tolerance can AxisForm hold?","The ±0.010 mm figure is illustrative only. AxisForm is not a real manufacturer and makes no production capability claim."),("certification","Is AxisForm certified?","No. All quality records and badges are clearly demonstration content, not real certificates."),("data-isolation","Will this enquiry appear in NorthForge?","No. AxisForm content, visitor sessions, chats and RFQs are assigned to the AxisForm tenant."),]):
            faqs[key]=await _upsert(session,FAQItem,{"tenant_id":tenant.id,"variant_key":key,"locale":"en"},{"question":q,"answer":a,"category_tag":"demo","sort_order":order,"status":"published"})

        for key,headline,sub,label in [("drawing-rfq","Start with the part, not a generic form","Send material, tolerance, volume and target timing.","Send a drawing"),("advisor-rfq","Need help shaping the requirement?","Ask the advisor before opening an RFQ.","Ask the advisor")]:
            await _upsert(session,CTA,{"tenant_id":tenant.id,"cta_key":key,"locale":"en"},{"cta_type":"banner","headline":headline,"subheadline":sub,"button_label":label,"button_action":"open_rfq","button_url":"/rfq","bg_color":"#b8ef36","target_intent_stage":"any","status":"published"})

        for page_type,slug,title,subtitle in [("home","home","AxisForm Precision","Connected precision-machining demonstration tenant."),("about","about","About AxisForm Precision","Fictional company used for multi-tenant validation."),("contact","contact","Contact the test tenant","Functional testing only; no sales follow-up." )]:
            await _upsert(session,Page,{"tenant_id":tenant.id,"slug":slug,"locale":"en"},{"page_type":page_type,"title":title,"subtitle":subtitle,"body":f"<p>{subtitle}</p>","hero_image_url":f"{ASSET_BASE}/generated/home-hero-cnc-facility.png","seo_title":title,"seo_description":subtitle,"canonical_url":f"{SITE_URL}/{'' if slug=='home' else slug}","status":"published","noindex":False,"published_at":utcnow_naive()})

        links = [(products["servo-housing"],apps["industrial-automation"]),(products["robot-joint"],apps["industrial-automation"]),(products["sensor-sleeve"],apps["instrumentation"])]
        for product, app in links:
            if not await _first(session,ProductApplicationLink,product_id=product.id,application_id=app.id): session.add(ProductApplicationLink(product_id=product.id,application_id=app.id))
        for product in products.values():
            for cert in certs.values():
                if not await _first(session,ProductCertificationLink,product_id=product.id,certification_id=cert.id): session.add(ProductCertificationLink(product_id=product.id,certification_id=cert.id))
            for faq in faqs.values():
                if not await _first(session,ProductFAQLink,product_id=product.id,faq_item_id=faq.id): session.add(ProductFAQLink(product_id=product.id,faq_item_id=faq.id,sort_order=faq.sort_order))

        await session.commit()
        readiness = await validate_and_store_readiness(session, build)
        if not readiness["ready"]:
            raise RuntimeError(f"AxisForm site readiness failed: {readiness['blockers']}")
        build.status, build.published_at, build.updated_at = "published", utcnow_naive(), utcnow_naive()
        session.add(build)
        await session.commit()
        print(json.dumps({"tenant":TENANT_SLUG,"site":SITE_URL,"status":"published","ready":True,"content":{"categories":len(categories),"products":len(products),"applications":len(apps),"certifications":len(certs),"faqs":len(faqs)}}))


if __name__ == "__main__":
    asyncio.run(provision())
