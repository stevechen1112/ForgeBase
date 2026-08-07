# Import order matters: associations must come before models that reference them.
from app.models.associations import (
    ProductApplicationLink,
    ProductCertificationLink,
    ProductFAQLink,
    ProductComparisonLink,
    AlternativePartLink,
    ApplicationFAQLink,
    ApplicationRelatedLink,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.models.product_category import ProductCategory
from app.models.product import Product
from app.models.application import Application
from app.models.faq_item import FAQItem
from app.models.comparison_topic import ComparisonTopic
from app.models.certification import Certification
from app.models.capability import Capability
from app.models.cta import CTA
from app.models.page import Page
from app.models.page_brief import PageBrief
from app.models.content_asset import ContentAsset
from app.models.content_field_lock import ContentFieldLock
from app.models.content_strategy import ContentStrategy
from app.models.ai_generation_log import AIGenerationLog
from app.models.audience_tag import AudienceTag, VisitorTagLink
from app.models.visitor import Visitor
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.segment import Segment
from app.models.nurture import NurtureSequence, NurtureStep, NurtureEnrollment, NurtureOutbox
from app.models.chat import ChatSession, ChatMessage
from app.models.integration_credential import IntegrationCredential
from app.models.intake import (
    IntakeProject,
    IntakeUrlCandidate,
    IntakeEntityCandidate,
    IntakeRedirectCandidate,
    IntakeBriefCandidate,
)
from app.models.site_profile import SiteProfile
from app.models.rfq_event import RFQEvent
from app.models.copilot_run_log import CopilotRunLog
from app.models.idempotency_key import IdempotencyKey
from app.models.reply_template import ReplyTemplate

__all__ = [
    "ProductApplicationLink",
    "ProductCertificationLink",
    "ProductFAQLink",
    "ProductComparisonLink",
    "AlternativePartLink",
    "ApplicationFAQLink",
    "ApplicationRelatedLink",
    "Tenant",
    "User",
    "ProductCategory",
    "Product",
    "Application",
    "FAQItem",
    "ComparisonTopic",
    "Certification",
    "Capability",
    "CTA",
    "Page",
    "PageBrief",
    "ContentAsset",
    "ContentFieldLock",
    "ContentStrategy",
    "AIGenerationLog",
    "AudienceTag",
    "VisitorTagLink",
    "Visitor",
    "TrackingEvent",
    "TrackingSession",
    "Segment",
    "NurtureSequence",
    "NurtureStep",
    "NurtureEnrollment",
    "NurtureOutbox",
    "ChatSession",
    "ChatMessage",
    "IntakeProject",
    "IntakeUrlCandidate",
    "IntakeEntityCandidate",
    "IntakeRedirectCandidate",
    "IntakeBriefCandidate",
    "SiteProfile",
    "RFQEvent",
    "IdempotencyKey",
    "ReplyTemplate",
]
