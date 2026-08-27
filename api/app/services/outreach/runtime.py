from __future__ import annotations

import hashlib
import html
import json
import math
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func
from sqlmodel import col, select

from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt, encrypt
from app.db.session import get_session_ctx
from app.models.company_identification import CompanyIdentification
from app.models.comparison_topic import ComparisonTopic
from app.models.contact_enrichment import ContactCandidate, ContactPersonaPolicy
from app.models.email_delivery import EmailSuppression
from app.models.operational_job import OperationalJob
from app.models.outreach import (
    JourneySnapshot,
    OutreachDraftPolicy,
    OutreachMessage,
    OutreachMessageReview,
)
from app.models.page import Page
from app.models.product import Product
from app.models.site_profile import SiteProfile
from app.models.tracking_event import TrackingEvent
from app.models.visitor import Visitor
from app.services.email_governance import email_hash, normalize_email
from app.services.outreach.content_guard import (
    OutreachDraftBlocked,
    canonical_cta,
    validate_content,
)
from app.services.outreach.jobs import enqueue_outreach_draft_job

_EVENT_WEIGHT = {
    "page_view": 1.0,
    "product_view": 2.0,
    "comparison_view": 3.0,
    "spec_download": 4.0,
    "cta_click": 3.0,
    "form_start": 3.0,
    "rfq_start": 5.0,
    "rfq_submit": 8.0,
    "chat_start": 2.0,
    "chat_rfq_handoff": 6.0,
}


def _time_weight(age_days: float) -> float:
    return math.exp(-max(0.0, age_days) / 21.0)


def _ranked(
    items: dict[uuid.UUID, dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    return sorted(
        items.values(), key=lambda item: (-float(item["score"]), item["title"])
    )[:limit]


def _version_stamp(value) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=None).isoformat()


async def _load_context(db, candidate_id: uuid.UUID):
    candidate = (
        await db.exec(
            select(ContactCandidate)
            .where(ContactCandidate.id == candidate_id)
            .with_for_update()
        )
    ).first()
    if not candidate:
        raise OutreachDraftBlocked("Contact candidate not found")
    policy = await db.get(OutreachDraftPolicy, candidate.tenant_id)
    if not policy or policy.mode != "review_only":
        raise OutreachDraftBlocked("Outreach drafting is off")
    persona = await db.get(ContactPersonaPolicy, candidate.tenant_id)
    company = (
        await db.get(CompanyIdentification, candidate.company_identification_id)
        if candidate.company_identification_id
        else None
    )
    visitor = await db.get(Visitor, company.visitor_id) if company else None
    now = utcnow_naive()
    if (
        candidate.status not in {"approved", "converted"}
        or candidate.verification_status != "verified"
        or candidate.expires_at <= now
    ):
        raise OutreachDraftBlocked("A current approved, verified candidate is required")
    if not persona or candidate.relevance_score < persona.min_relevance_score:
        raise OutreachDraftBlocked("Candidate relevance gate is not met")
    if (
        not company
        or company.status != "confirmed"
        or company.expires_at <= now
        or not company.domain
    ):
        raise OutreachDraftBlocked("Current confirmed company evidence is required")
    if (
        not visitor
        or visitor.tenant_id != candidate.tenant_id
        or visitor.analytics_consent_status != "granted"
    ):
        raise OutreachDraftBlocked("Current analytics consent is required")
    suppressed = (
        await db.exec(
            select(EmailSuppression.id).where(
                EmailSuppression.scope_key == "global",
                EmailSuppression.email_hash == candidate.email_hash,
                EmailSuppression.active.is_(True),
            )
        )
    ).first()
    if suppressed:
        raise OutreachDraftBlocked("Candidate is suppressed")
    return candidate, company, visitor, policy


async def build_journey_snapshot(
    db,
    *,
    candidate: ContactCandidate,
    company: CompanyIdentification,
    visitor: Visitor,
    policy: OutreachDraftPolicy,
    generation_key: str,
) -> JourneySnapshot:
    now = utcnow_naive()
    since = now - timedelta(days=policy.lookback_days)
    events = list(
        (
            await db.exec(
                select(TrackingEvent)
                .where(
                    TrackingEvent.tenant_id == candidate.tenant_id,
                    TrackingEvent.visitor_id == visitor.visitor_id,
                    TrackingEvent.timestamp >= since,
                    TrackingEvent.is_test_data.is_(False),
                    TrackingEvent.event_name.in_(list(_EVENT_WEIGHT)),
                )
                .order_by(col(TrackingEvent.timestamp).desc())
                .limit(policy.max_evidence_events)
            )
        ).all()
    )

    product_ids = {
        event.page_id
        for event in events
        if event.page_id and event.page_type == "product"
    }
    page_ids = {
        event.page_id for event in events if event.page_id and event.page_type == "page"
    }
    comparison_ids = {
        event.page_id
        for event in events
        if event.page_id and event.page_type == "comparison"
    }
    products = (
        list(
            (
                await db.exec(
                    select(Product).where(
                        Product.tenant_id == candidate.tenant_id,
                        Product.status == "published",
                        col(Product.id).in_(product_ids),
                    )
                )
            ).all()
        )
        if product_ids
        else []
    )
    pages = (
        list(
            (
                await db.exec(
                    select(Page).where(
                        Page.tenant_id == candidate.tenant_id,
                        Page.status == "published",
                        Page.noindex.is_(False),
                        col(Page.id).in_(page_ids),
                    )
                )
            ).all()
        )
        if page_ids
        else []
    )
    comparisons = (
        list(
            (
                await db.exec(
                    select(ComparisonTopic).where(
                        ComparisonTopic.tenant_id == candidate.tenant_id,
                        ComparisonTopic.status == "published",
                        col(ComparisonTopic.id).in_(comparison_ids),
                    )
                )
            ).all()
        )
        if comparison_ids
        else []
    )
    product_map, page_map, comparison_map = (
        {row.id: row for row in rows} for rows in (products, pages, comparisons)
    )

    product_scores: dict[uuid.UUID, dict[str, Any]] = {}
    page_scores: dict[uuid.UUID, dict[str, Any]] = {}
    comparison_scores: dict[uuid.UUID, dict[str, Any]] = {}
    downloads: dict[uuid.UUID, dict[str, Any]] = {}
    counts: dict[str, int] = defaultdict(int)
    evidence_ids: list[str] = []
    knowledge_refs: dict[tuple[str, uuid.UUID], dict[str, Any]] = {}
    latest_locale: str | None = None

    for event in events:
        row: Any | None = None
        bucket: dict[uuid.UUID, dict[str, Any]] | None = None
        entity_type = event.page_type or ""
        if event.page_id in product_map and entity_type == "product":
            row, bucket = product_map[event.page_id], product_scores
            title = row.product_name
        elif event.page_id in page_map and entity_type == "page":
            row, bucket = page_map[event.page_id], page_scores
            title = row.title
        elif event.page_id in comparison_map and entity_type == "comparison":
            row, bucket = comparison_map[event.page_id], comparison_scores
            title = row.topic_title
        else:
            title = ""
        valid_signal_without_entity = event.event_name in {
            "cta_click",
            "form_start",
            "rfq_start",
            "rfq_submit",
            "chat_start",
            "chat_rfq_handoff",
        }
        if not row and not valid_signal_without_entity:
            continue
        counts[event.event_name] += 1
        evidence_ids.append(str(event.event_id))
        latest_locale = latest_locale or event.locale
        if row and bucket is not None and event.page_id:
            event_time = (
                event.timestamp.replace(tzinfo=None)
                if event.timestamp.tzinfo
                else event.timestamp
            )
            score = _EVENT_WEIGHT[event.event_name] * _time_weight(
                (now - event_time).total_seconds() / 86400
            )
            item = bucket.setdefault(
                event.page_id,
                {
                    "id": str(event.page_id),
                    "title": title,
                    "locale": row.locale,
                    "score": 0.0,
                    "events": 0,
                },
            )
            item["score"] = round(float(item["score"]) + score, 4)
            item["events"] = int(item["events"]) + 1
            knowledge_refs[(entity_type, event.page_id)] = {
                "entity_type": entity_type,
                "entity_id": str(event.page_id),
                "title": title,
                "locale": row.locale,
                "published_at": _version_stamp(row.published_at),
                "content_version": _version_stamp(row.updated_at),
            }
            if event.event_name == "spec_download" and entity_type == "product":
                downloads[event.page_id] = {
                    "product_id": str(event.page_id),
                    "title": title,
                    "event_id": str(event.event_id),
                }

    top_products = _ranked(product_scores)
    top_pages = _ranked(page_scores)
    top_comparisons = _ranked(comparison_scores)
    if not evidence_ids:
        raise OutreachDraftBlocked(
            "No current published-content journey evidence is available"
        )
    summary_bits = []
    if top_products:
        summary_bits.append(
            "Product interest: " + ", ".join(item["title"] for item in top_products[:3])
        )
    if top_comparisons:
        summary_bits.append(
            "Comparison interest: "
            + ", ".join(item["title"] for item in top_comparisons[:2])
        )
    if downloads:
        summary_bits.append(f"Published product downloads: {len(downloads)}")
    if counts.get("rfq_start") or counts.get("rfq_submit"):
        summary_bits.append("RFQ intent signal present")
    if counts.get("chat_start") or counts.get("chat_rfq_handoff"):
        summary_bits.append("Chat intent signal present")
    summary = (
        "; ".join(summary_bits)
        or "Published content engagement is available for review."
    )
    locale = (
        latest_locale
        if latest_locale in policy.allowed_languages
        else policy.allowed_languages[0]
    )
    snapshot = JourneySnapshot(
        tenant_id=candidate.tenant_id,
        visitor_id=visitor.visitor_id,
        company_identification_id=company.id,
        contact_candidate_id=candidate.id,
        generation_key=generation_key,
        intent_score=max(0, visitor.intent_score),
        intent_stage=visitor.intent_stage,
        intent_facets={
            "product_interest": visitor.facet_product_interest,
            "trust_validation": visitor.facet_trust_validation,
            "procurement_readiness": visitor.facet_procurement_readiness,
            "urgency": visitor.facet_urgency,
        },
        top_products=top_products,
        top_pages=top_pages,
        downloads=list(downloads.values()),
        comparisons=top_comparisons,
        cta_signals=[
            {"event_name": name, "count": counts[name]}
            for name in ("cta_click", "form_start", "rfq_start", "rfq_submit")
            if counts[name]
        ],
        journey_signals={
            "event_counts": dict(counts),
            "suggested_language": locale,
            "lookback_days": policy.lookback_days,
        },
        summary=summary,
        evidence_event_ids=evidence_ids,
        knowledge_references=list(knowledge_refs.values()),
        policy_version=policy.policy_version,
        generated_at=now,
        expires_at=min(
            now + timedelta(days=policy.snapshot_retention_days),
            company.expires_at,
            candidate.expires_at,
        ),
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


def _draft_parts(
    snapshot: JourneySnapshot,
    company: CompanyIdentification,
    candidate: ContactCandidate,
    brand: str,
) -> tuple[str, str, str]:
    language = str(snapshot.journey_signals.get("suggested_language") or "en")
    topic = (
        snapshot.top_products[0]["title"]
        if snapshot.top_products
        else (
            snapshot.comparisons[0]["title"]
            if snapshot.comparisons
            else "our published product information"
        )
    )
    if language.lower().startswith("zh"):
        subject = f"{company.company_name}｜{topic}相關公開資料"
        body = f"{candidate.full_name} 您好：\n\n若貴公司正在評估 {topic}，{brand} 可以提供相關公開資料，並由業務協助確認需求適配性。"
    elif language.lower().startswith("ja"):
        subject = f"{company.company_name}様向け｜{topic}の公開情報"
        body = f"{candidate.full_name}様\n\n貴社で{topic}をご検討中でしたら、{brand}の公開情報をご案内し、担当者が要件確認をお手伝いできます。"
    else:
        subject = f"Published information about {topic} for {company.company_name}"
        body = f"Hello {candidate.full_name},\n\nIf your team is evaluating {topic}, {brand} can share the relevant published information and have a sales specialist help assess fit."
    validate_content(subject=subject, body_without_cta=body)
    text = f"{body}\n\n{canonical_cta(language)}"
    html_body = "".join(
        f"<p>{html.escape(paragraph)}</p>" for paragraph in text.split("\n\n")
    )
    return subject, text, html_body


async def run_journey_summarize_job(candidate_id: uuid.UUID) -> uuid.UUID:
    async with get_session_ctx() as db:
        candidate, company, visitor, policy = await _load_context(db, candidate_id)
        generation_key = (
            f"journey:{candidate.tenant_id}:{candidate.id}:"
            f"{utcnow_naive().date().isoformat()}:{policy.policy_version}"
        )
        snapshot = (
            await db.exec(
                select(JourneySnapshot).where(
                    JourneySnapshot.generation_key == generation_key
                )
            )
        ).first()
        if snapshot is None:
            snapshot = await build_journey_snapshot(
                db,
                candidate=candidate,
                company=company,
                visitor=visitor,
                policy=policy,
                generation_key=generation_key,
            )
        job_key = f"outreach-draft:{candidate.tenant_id}:{snapshot.id}:{candidate.id}"
        existing_job = (
            await db.exec(
                select(OperationalJob.id).where(
                    OperationalJob.idempotency_key == job_key
                )
            )
        ).first()
        if not existing_job:
            enqueue_outreach_draft_job(
                db,
                tenant_id=candidate.tenant_id,
                snapshot_id=snapshot.id,
                candidate_id=candidate.id,
            )
        await db.commit()
        return snapshot.id


async def run_outreach_draft_job(
    snapshot_id: uuid.UUID, candidate_id: uuid.UUID
) -> uuid.UUID:
    async with get_session_ctx() as db:
        candidate, company, visitor, policy = await _load_context(db, candidate_id)
        snapshot = await db.get(JourneySnapshot, snapshot_id)
        now = utcnow_naive()
        if (
            not snapshot
            or snapshot.tenant_id != candidate.tenant_id
            or snapshot.visitor_id != visitor.visitor_id
            or snapshot.company_identification_id != company.id
            or snapshot.expires_at <= now
        ):
            raise OutreachDraftBlocked(
                "Journey snapshot is missing, expired, or outside the candidate scope"
            )
        existing = (
            await db.exec(
                select(OutreachMessage.id).where(
                    OutreachMessage.tenant_id == candidate.tenant_id,
                    OutreachMessage.journey_snapshot_id == snapshot.id,
                    OutreachMessage.contact_candidate_id == candidate.id,
                )
            )
        ).first()
        if existing:
            return existing
        address = normalize_email(decrypt(candidate.email_ciphertext))
        if (
            email_hash(address) != candidate.email_hash
            or address.partition("@")[2] != company.domain.lower()
        ):
            raise OutreachDraftBlocked(
                "Candidate email integrity or company-domain check failed"
            )
        profile = (
            await db.exec(
                select(SiteProfile)
                .where(SiteProfile.tenant_id == candidate.tenant_id)
                .limit(1)
            )
        ).first()
        brand = profile.brand_name if profile else "our team"
        subject, text_body, html_body = _draft_parts(
            snapshot, company, candidate, brand
        )
        revision_no = (
            int(
                (
                    await db.exec(
                        select(func.max(OutreachMessage.revision_no)).where(
                            OutreachMessage.tenant_id == candidate.tenant_id,
                            OutreachMessage.contact_candidate_id == candidate.id,
                        )
                    )
                ).one()
                or 0
            )
            + 1
        )
        content_hash = hashlib.sha256(
            f"{subject}\n{text_body}\n{html_body}".encode()
        ).hexdigest()
        knowledge_version = hashlib.sha256(
            json.dumps(snapshot.knowledge_references, sort_keys=True).encode()
        ).hexdigest()
        message = OutreachMessage(
            tenant_id=candidate.tenant_id,
            visitor_id=visitor.visitor_id,
            company_identification_id=company.id,
            contact_candidate_id=candidate.id,
            contact_id=candidate.converted_contact_id,
            journey_snapshot_id=snapshot.id,
            revision_no=revision_no,
            language=str(snapshot.journey_signals.get("suggested_language") or "en"),
            to_email_ciphertext=encrypt(address),
            to_email_hash=candidate.email_hash,
            to_email_masked=candidate.email_masked,
            subject_snapshot=subject,
            html_snapshot=html_body,
            text_snapshot=text_body,
            personalization_evidence={
                "company": {
                    "id": str(company.id),
                    "name": company.company_name,
                    "domain": company.domain,
                },
                "candidate": {
                    "id": str(candidate.id),
                    "relevance_score": candidate.relevance_score,
                    "relevance_reasons": candidate.relevance_reasons,
                    "identity_notice": "Company-related contact candidate; not identified as the anonymous visitor.",
                },
                "journey_snapshot_id": str(snapshot.id),
                "knowledge_references": snapshot.knowledge_references,
            },
            knowledge_version=f"published-content:{knowledge_version}",
            prompt_version="grounded-template-v1",
            policy_version=policy.policy_version,
            generation_model="forgebase-grounded-template-v1",
            content_hash=content_hash,
            status="pending_review",
            generated_at=now,
            created_at=now,
        )
        db.add(message)
        await db.flush()
        db.add(
            OutreachMessageReview(
                tenant_id=message.tenant_id,
                outreach_message_id=message.id,
                action="generated",
                diff_json={"content_hash": content_hash},
                created_at=now,
            )
        )
        await db.commit()
        return message.id


async def validate_snapshot_current(db, snapshot: JourneySnapshot) -> None:
    """Re-resolve every reference and event before a reviewer can approve."""

    event_ids: list[uuid.UUID] = []
    try:
        event_ids = [uuid.UUID(value) for value in snapshot.evidence_event_ids]
    except (TypeError, ValueError) as exc:
        raise OutreachDraftBlocked(
            "Journey evidence contains an invalid event reference"
        ) from exc
    current_events = list(
        (
            await db.exec(
                select(TrackingEvent.event_id).where(
                    TrackingEvent.tenant_id == snapshot.tenant_id,
                    TrackingEvent.visitor_id == snapshot.visitor_id,
                    col(TrackingEvent.event_id).in_(event_ids),
                )
            )
        ).all()
    )
    if len(set(current_events)) != len(set(event_ids)):
        raise OutreachDraftBlocked(
            "One or more journey evidence events no longer exist"
        )

    for reference in snapshot.knowledge_references:
        try:
            entity_id = uuid.UUID(str(reference["entity_id"]))
            entity_type = str(reference["entity_type"])
        except (KeyError, TypeError, ValueError) as exc:
            raise OutreachDraftBlocked(
                "Knowledge evidence contains an invalid reference"
            ) from exc
        if entity_type == "product":
            current = (
                await db.exec(
                    select(Product).where(
                        Product.id == entity_id,
                        Product.tenant_id == snapshot.tenant_id,
                        Product.status == "published",
                    )
                )
            ).first()
        elif entity_type == "page":
            current = (
                await db.exec(
                    select(Page).where(
                        Page.id == entity_id,
                        Page.tenant_id == snapshot.tenant_id,
                        Page.status == "published",
                        Page.noindex.is_(False),
                    )
                )
            ).first()
        elif entity_type == "comparison":
            current = (
                await db.exec(
                    select(ComparisonTopic).where(
                        ComparisonTopic.id == entity_id,
                        ComparisonTopic.tenant_id == snapshot.tenant_id,
                        ComparisonTopic.status == "published",
                    )
                )
            ).first()
        else:
            current = None
        if not current:
            raise OutreachDraftBlocked(
                "One or more knowledge references are deleted or unpublished"
            )
        if (
            str(reference.get("title"))
            != str(
                getattr(
                    current,
                    "product_name",
                    getattr(current, "title", getattr(current, "topic_title", "")),
                )
            )
            or str(reference.get("locale")) != str(current.locale)
            or reference.get("content_version") != _version_stamp(current.updated_at)
        ):
            raise OutreachDraftBlocked(
                "Published knowledge changed after this draft was generated"
            )


async def validate_message_for_approval(
    db, message: OutreachMessage
) -> JourneySnapshot:
    candidate, company, visitor, policy = await _load_context(
        db, message.contact_candidate_id
    )
    if (
        message.tenant_id != candidate.tenant_id
        or message.company_identification_id != company.id
        or message.visitor_id != visitor.visitor_id
        or message.to_email_hash != candidate.email_hash
    ):
        raise OutreachDraftBlocked("Draft scope no longer matches its evidence")
    snapshot = await db.get(JourneySnapshot, message.journey_snapshot_id)
    now = utcnow_naive()
    if (
        not snapshot
        or snapshot.expires_at <= now
        or snapshot.contact_candidate_id != candidate.id
        or snapshot.company_identification_id != company.id
        or snapshot.visitor_id != visitor.visitor_id
    ):
        raise OutreachDraftBlocked("Draft evidence is no longer current")
    if (
        message.policy_version != policy.policy_version
        or snapshot.policy_version != policy.policy_version
    ):
        raise OutreachDraftBlocked("Draft policy changed; regenerate before approval")
    company_evidence = message.personalization_evidence.get("company", {})
    if (
        company_evidence.get("name") != company.company_name
        or company_evidence.get("domain") != company.domain
    ):
        raise OutreachDraftBlocked("Company evidence changed after draft generation")
    address = normalize_email(decrypt(message.to_email_ciphertext))
    if (
        email_hash(address) != candidate.email_hash
        or address.partition("@")[2] != company.domain.lower()
    ):
        raise OutreachDraftBlocked("Draft recipient integrity check failed")
    cta = canonical_cta(message.language)
    if message.text_snapshot.count(cta) != 1 or not message.text_snapshot.endswith(cta):
        raise OutreachDraftBlocked("Draft must end with exactly one canonical CTA")
    body_without_cta = message.text_snapshot[: -len(cta)].rstrip()
    validate_content(
        subject=message.subject_snapshot,
        body_without_cta=body_without_cta,
    )
    await validate_snapshot_current(db, snapshot)
    return snapshot


async def purge_expired_outreach_evidence(db) -> dict[str, int]:
    result = await db.exec(
        delete(JourneySnapshot).where(JourneySnapshot.expires_at <= utcnow_naive())
    )
    return {"journey_snapshots": int(result.rowcount or 0)}
