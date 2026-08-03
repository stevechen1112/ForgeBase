"""T9/T10: Lead Quality Score（規則式 v1）與貿易條件欄位。

驗收依據：五種典型 RFQ 的分數排序需符合業務直覺，且原因可讀。
"""
import json
import uuid
from types import SimpleNamespace

from app.services.rfq_quality import score_rfq_quality
from tests.conftest import requires_db


def _rfq(**overrides):
    base = dict(
        full_name="Buyer", email="buyer@acme-industrial.com",
        company_name="Acme Industrial", phone=None, country="DE",
        job_title="Procurement Manager", product_ids=[], application_id=None,
        quantity=None, specifications=None, timeline=None, message=None,
        how_did_you_find_us=None, consent=True, visitor_id=None, source_page=None,
        incoterm=None, annual_volume=None, is_trial_order=None,
        required_certs=[], target_price=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_full_procurement_rfq_scores_high():
    score, reasons = score_rfq_quality(_rfq(
        specifications="Material: SUS304, tolerance +/-0.05mm, per DIN EN 10088. Drawing attached.",
        quantity="10,000 pcs/month",
        timeline="1-3 months",
        message="We are sourcing a long-term supplier for stamped brackets used in industrial ovens. Please quote with tooling cost breakdown and lead time.",
        incoterm="FOB",
        annual_volume="120k pcs",
        is_trial_order=False,
        required_certs=["CE", "RoHS"],
        target_price="USD 1.20/pc",
    ))
    assert score >= 80, f"score={score}, reasons={reasons}"
    assert any("貿易條件" in r for r in reasons)
    assert any("認證" in r for r in reasons)


def test_one_liner_free_email_scores_low():
    score, reasons = score_rfq_quality(_rfq(
        email="someone@gmail.com",
        company_name=None, country=None, job_title=None,
        message="pls send catalog",
    ))
    assert score <= 20, f"score={score}, reasons={reasons}"
    assert any("免費信箱" in r for r in reasons)
    assert any("過短" in r for r in reasons)


def test_spam_scores_lowest():
    spam_score, _ = score_rfq_quality(_rfq(
        message="We offer crypto casino SEO services and guest post backlink packages for your website",
    ))
    normal_score, _ = score_rfq_quality(_rfq(message="pls send catalog"))
    assert spam_score < normal_score


def test_trade_terms_are_strong_signal():
    without = score_rfq_quality(_rfq(
        specifications="Material: SUS304, tolerance +/-0.05mm, per DIN EN 10088 standard",
        quantity="10,000 pcs", timeline="1-3 months",
    ))[0]
    with_terms = score_rfq_quality(_rfq(
        specifications="Material: SUS304, tolerance +/-0.05mm, per DIN EN 10088 standard",
        quantity="10,000 pcs", timeline="1-3 months",
        incoterm="CIF", annual_volume="120k pcs", required_certs=["FDA"],
    ))[0]
    assert with_terms - without >= 30


def test_score_clamped_and_reasons_readable():
    score, reasons = score_rfq_quality(_rfq())
    assert 0 <= score <= 100
    for r in reasons:
        assert r[0] in "+-" and r[1].isdigit()


@requires_db
async def test_quality_score_persisted_and_sorted(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    tag = uuid.uuid4().hex[:8]
    headers = {"X-Tenant-ID": str(tenant_a.id)}

    def payload(email_suffix, **kw):
        base = {
            "full_name": "Buyer", "email": f"b-{email_suffix}-{tag}@acme.com",
            "company_name": "Acme", "country": "DE", "consent": True,
            "product_ids": [],
        }
        base.update(kw)
        return base

    # High-quality RFQ
    r = await http_client.post("/api/v1/forms/rfq", headers=headers, json=payload(
        "hi",
        specifications="Material: SUS304, tolerance +/-0.05mm, per DIN EN 10088. Drawing attached.",
        quantity="10,000 pcs/month", timeline="1-3 months", job_title="Procurement Manager",
        message="We are sourcing a long-term supplier for stamped brackets used in industrial ovens. Please quote with tooling cost and lead time.",
        incoterm="FOB", annual_volume="120k pcs", required_certs=["CE"],
    ))
    assert r.status_code == 201, r.text

    # Low-quality RFQ
    r = await http_client.post("/api/v1/forms/rfq", headers=headers, json=payload(
        "lo", message="pls send catalog",
    ))
    assert r.status_code == 201, r.text

    # List sorted by quality — high must come first and expose score
    token = await admin_token_for_tenant(tenant_a.id)
    r = await http_client.get(
        "/api/v1/tracking/rfqs?sort=quality",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) >= 2
    scores = [row["quality_score"] for row in rows]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > scores[-1]

    # Detail exposes reasons + trade terms
    r = await http_client.get(
        f"/api/v1/tracking/rfqs/{rows[0]['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    detail = r.json()
    assert any("貿易條件" in reason for reason in detail["quality_reasons"])
    assert detail["incoterm"] == "FOB"
    assert detail["required_certs"] == ["CE"]
