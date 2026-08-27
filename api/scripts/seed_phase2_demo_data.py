"""Seed safe, clearly synthetic records for the second-stage tenant demo.

This script never enables email delivery and never approves nurture sequences.
It is idempotent and intentionally targets an existing, isolated demo tenant.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlmodel import select

from app.core.datetime import utcnow_naive
from app.db.session import AsyncSessionLocal
from app.models.comparison_topic import ComparisonTopic
from app.models.contact import Contact
from app.models.cta import CTA
from app.models.nurture import NurtureEnrollment, NurtureOutbox, NurtureSequence, NurtureStep
from app.models.segment import Segment
from app.models.site_profile import SiteProfile
from app.models.tenant import Tenant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default="axisform-precision", help="Existing demo tenant slug")
    return parser.parse_args()


async def _first(session, model, *conditions):
    return (await session.exec(select(model).where(*conditions))).first()


async def seed(tenant_slug: str) -> dict[str, int | str]:
    async with AsyncSessionLocal() as session:
        tenant = await _first(session, Tenant, Tenant.slug == tenant_slug)
        if not tenant:
            raise RuntimeError(f"Tenant not found: {tenant_slug}")

        segments = [
            (
                "High-intent engineering buyers",
                "Synthetic visitors with strong buying signals for the Phase 2 demo.",
                [{"type": "intent_score", "op": "gte", "value": 40}],
            ),
            (
                "Returning specification researchers",
                "Synthetic repeat visitors researching product and quality pages.",
                [
                    {"type": "event_count", "op": "gte", "value": 2, "event_name": "product_view", "within_days": 30},
                    {"type": "event_count", "op": "gte", "value": 1, "event_name": "certification_view", "within_days": 30},
                ],
            ),
        ]
        segment_rows: list[Segment] = []
        for name, description, conditions in segments:
            row = await _first(session, Segment, Segment.tenant_id == tenant.id, Segment.name == name)
            if not row:
                row = Segment(tenant_id=tenant.id, name=name)
            row.description = description
            row.conditions = json.dumps(conditions)
            row.combinator = "AND"
            row.updated_at = utcnow_naive()
            session.add(row)
            await session.flush()
            segment_rows.append(row)

        sequence = await _first(
            session,
            NurtureSequence,
            NurtureSequence.tenant_id == tenant.id,
            NurtureSequence.name == "Drawing follow-up — demo approval required",
        )
        if not sequence:
            sequence = NurtureSequence(
                tenant_id=tenant.id,
                name="Drawing follow-up — demo approval required",
                trigger_type="segment",
            )
        sequence.description = "Synthetic workflow for demonstrating review, approval and outbox controls."
        sequence.trigger_value = str(segment_rows[0].id)
        sequence.is_active = True
        sequence.is_approved = False
        sequence.approved_at = None
        sequence.approved_by = None
        sequence.updated_at = utcnow_naive()
        session.add(sequence)
        await session.flush()

        step_specs = [
            (0, 0, "Demo: confirm drawing and tolerance requirements", "This is a synthetic draft. Confirm material, tolerance, volume and target date before any real reply."),
            (1, 3, "Demo: share inspection and traceability checklist", "This is a synthetic draft. Attach only verified evidence before sending."),
        ]
        step_rows: list[NurtureStep] = []
        for order, delay, subject, body in step_specs:
            step = await _first(
                session,
                NurtureStep,
                NurtureStep.sequence_id == sequence.id,
                NurtureStep.step_order == order,
            )
            if not step:
                step = NurtureStep(tenant_id=tenant.id, sequence_id=sequence.id, step_order=order)
            step.delay_days = delay
            step.subject = subject
            step.text_body = body
            step.html_body = f"<p>{body}</p><p><strong>Demo only — manual approval required.</strong></p>"
            step.from_name = "AxisForm Demo Team"
            step.updated_at = utcnow_naive()
            session.add(step)
            await session.flush()
            step_rows.append(step)

        contact = await _first(session, Contact, Contact.tenant_id == tenant.id)
        enrollment_count = 0
        outbox_count = 0
        if contact:
            enrollment = await _first(
                session,
                NurtureEnrollment,
                NurtureEnrollment.sequence_id == sequence.id,
                NurtureEnrollment.contact_id == contact.id,
            )
            if not enrollment:
                enrollment = NurtureEnrollment(
                    tenant_id=tenant.id,
                    sequence_id=sequence.id,
                    contact_id=contact.id,
                    trigger_type="demo",
                    trigger_value="synthetic",
                )
                session.add(enrollment)
                await session.flush()
            enrollment_count = 1
            outbox = await _first(
                session,
                NurtureOutbox,
                NurtureOutbox.enrollment_id == enrollment.id,
                NurtureOutbox.step_id == step_rows[0].id,
            )
            if not outbox:
                outbox = NurtureOutbox(
                    tenant_id=tenant.id,
                    enrollment_id=enrollment.id,
                    sequence_id=sequence.id,
                    step_id=step_rows[0].id,
                    contact_id=contact.id,
                    status="pending",
                    subject=step_rows[0].subject,
                )
                session.add(outbox)
            outbox_count = 1

        comparison = await _first(
            session,
            ComparisonTopic,
            ComparisonTopic.tenant_id == tenant.id,
            ComparisonTopic.slug == "milled-vs-turned-demo",
            ComparisonTopic.locale == "en",
        )
        if not comparison:
            comparison = ComparisonTopic(
                tenant_id=tenant.id,
                slug="milled-vs-turned-demo",
                locale="en",
                topic_title="Milled vs. turned component route — demo",
            )
        comparison.summary = "A synthetic decision guide showing how structured comparison content supports technical buyers."
        comparison.dimensions = json.dumps([
            {"dimension": "Best fit", "our_value": "Multi-face geometry", "competitor_value": "Rotational geometry", "winner": "neutral"},
            {"dimension": "Drawing review", "our_value": "Feature-based", "competitor_value": "Axis-based", "winner": "neutral"},
        ])
        comparison.conclusion = "<p>Demonstration content only. Manufacturing-route selection requires drawing review.</p>"
        comparison.status = "published"
        comparison.published_at = comparison.published_at or utcnow_naive()
        comparison.updated_at = utcnow_naive()
        session.add(comparison)

        cta = await _first(
            session,
            CTA,
            CTA.tenant_id == tenant.id,
            CTA.cta_key == "sales-ready-drawing-review",
            CTA.locale == "en",
        )
        if not cta:
            cta = CTA(
                tenant_id=tenant.id,
                cta_key="sales-ready-drawing-review",
                locale="en",
                cta_type="sticky_bar",
                headline="Ready for a drawing review?",
                button_label="Open RFQ",
                button_action="open_rfq",
            )
        cta.subheadline = "Show high-intent visitors a direct route to structured requirements."
        cta.button_url = "/rfq"
        cta.target_intent_stage = "sales_ready"
        cta.status = "published"
        cta.updated_at = utcnow_naive()
        session.add(cta)

        profile = await _first(session, SiteProfile, SiteProfile.tenant_id == tenant.id)
        if profile:
            profile.intent_scoring_config_json = json.dumps({
                "base_scores": {
                    "product_view": 3, "spec_download": 12, "certification_view": 5,
                    "rfq_start": 15, "rfq_submit": 35, "return_visit": 4,
                },
                "stage_thresholds": [
                    {"stage": "sales_ready", "min_score": 70},
                    {"stage": "hot", "min_score": 45},
                    {"stage": "warm", "min_score": 20},
                    {"stage": "cold", "min_score": 0},
                ],
            })
            profile.updated_at = utcnow_naive()
            session.add(profile)

        await session.commit()
        return {
            "tenant": tenant.slug,
            "segments": len(segment_rows),
            "sequences": 1,
            "steps": len(step_rows),
            "enrollments": enrollment_count,
            "outbox": outbox_count,
            "comparisons": 1,
            "dynamic_ctas": 1,
        }


async def main() -> None:
    result = await seed(parse_args().tenant)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
