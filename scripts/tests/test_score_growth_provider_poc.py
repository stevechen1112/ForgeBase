from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "score_growth_provider_poc.py"
SPEC = importlib.util.spec_from_file_location("score_growth_provider_poc", SCRIPT_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def rights(*providers: str, approved: bool = True):
    return {
        provider: {
            "approved": approved,
            "evidence_ref": f"LEGAL-{provider.upper()}-2026-001" if approved else None,
        }
        for provider in providers
    }


def company_case(case_id: str, market: str, *, correct: bool = True):
    return {
        "case_id": case_id,
        "provider": "pdl_ip",
        "market": market,
        "network_class": "corporate",
        "eligible": True,
        "matched": True,
        "high_confidence": True,
        "review": "correct" if correct else "incorrect",
        "conflict": False,
        "estimated_cost": 0.1,
        "latency_ms": 125,
    }


def contact_case(case_id: str, market: str):
    return {
        "case_id": case_id,
        "provider": "hunter_domain",
        "market": market,
        "candidate_count": 2,
        "reviewed_count": 2,
        "relevant_count": 2,
        "verified_business_email_count": 1,
        "fresh_count": 2,
        "invalid_or_suppressed_count": 0,
        "estimated_cost": 0.2,
        "latency_ms": 250,
    }


def test_scores_two_market_deidentified_evidence_and_passes_gates() -> None:
    company = [
        company_case(f"A{market}{index:03}", market)
        for market in ("TW", "JP")
        for index in range(50)
    ]
    contacts = [
        contact_case(f"B{market}{index:03}", market)
        for market in ("TW", "JP")
        for index in range(25)
    ]
    report = module.score(
        {
            "schema_version": 1,
            "provider_rights_approved": rights("pdl_ip", "hunter_domain"),
            "company_cases": company,
            "contact_cases": contacts,
        }
    )

    assert report["assessment"] == {
        "status": "decision_ready",
        "decision_ready": True,
        "markets_tested": ["JP", "TW"],
        "blockers": [],
    }
    assert report["company_identification"][0]["high_confidence_precision"] == 1.0
    assert report["contact_enrichment"][0]["persona_relevance_rate"] == 1.0
    assert report["contact_enrichment"][0]["verified_business_email_rate"] == 0.5
    assert not any(report["privacy"].values())
    assert "AJP000" not in str(report)


def test_keeps_rights_and_sample_gates_fail_closed() -> None:
    report = module.score(
        {
            "schema_version": 1,
            "provider_rights_approved": rights("pdl_ip", approved=False),
            "company_cases": [company_case("A001", "TW")],
            "contact_cases": [],
        }
    )

    assert report["assessment"]["decision_ready"] is False
    assert report["assessment"]["blockers"] == [
        "no_contact_evidence",
        "provider_rights_not_approved",
        "quality_or_safety_gate_not_passed",
        "fewer_than_two_markets_tested",
        "provider_market_coverage_incomplete",
    ]


def test_rejects_unsafe_excluded_network_matches() -> None:
    row = company_case("A001", "TW")
    row.update(network_class="vpn", eligible=False)
    report = module.score(
        {
            "schema_version": 1,
            "provider_rights_approved": rights("pdl_ip"),
            "company_cases": [row],
            "contact_cases": [],
        }
    )

    metrics = report["company_identification"][0]
    assert metrics["unsafe_excluded_network_matches"] == 1
    assert metrics["gates"]["excluded_network_matches_zero"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row.update(case_id="person@example.com"),
        lambda row: row.update(company_domain="example.com"),
        lambda row: row.update(estimated_cost=-1),
        lambda row: row.update(review="correct", matched=False),
    ],
)
def test_rejects_identifying_unsupported_or_inconsistent_company_rows(mutation) -> None:
    row = company_case("A001", "TW")
    mutation(row)
    with pytest.raises(module.ScorecardError):
        module.score(
            {
                "schema_version": 1,
                "provider_rights_approved": rights("pdl_ip"),
                "company_cases": [row],
                "contact_cases": [],
            }
        )


def test_rejects_contact_counts_that_cannot_be_true() -> None:
    row = contact_case("B001", "TW")
    row["relevant_count"] = 3
    with pytest.raises(module.ScorecardError, match="candidate_count"):
        module.score(
            {
                "schema_version": 1,
                "provider_rights_approved": rights("hunter_domain"),
                "company_cases": [],
                "contact_cases": [row],
            }
        )


def test_rejects_duplicate_case_provider_pairs() -> None:
    row = company_case("A001", "TW")
    with pytest.raises(module.ScorecardError, match="duplicate company"):
        module.score(
            {
                "schema_version": 1,
                "provider_rights_approved": rights("pdl_ip"),
                "company_cases": [row, dict(row)],
                "contact_cases": [],
            }
        )


def test_requires_each_layer_and_provider_to_cover_two_markets() -> None:
    report = module.score(
        {
            "schema_version": 1,
            "provider_rights_approved": rights("pdl_ip", "hunter_domain"),
            "company_cases": [company_case(f"A{index:03}", "TW") for index in range(50)],
            "contact_cases": [contact_case(f"B{index:03}", "JP") for index in range(25)],
        }
    )

    assert report["assessment"]["markets_tested"] == ["JP", "TW"]
    assert "provider_market_coverage_incomplete" in report["assessment"]["blockers"]


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_rejects_non_finite_measurements(value) -> None:
    row = company_case("A001", "TW")
    row["latency_ms"] = value
    with pytest.raises(module.ScorecardError, match="non-negative number"):
        module.score(
            {
                "schema_version": 1,
                "provider_rights_approved": rights("pdl_ip"),
                "company_cases": [row],
                "contact_cases": [],
            }
        )


def test_approved_rights_require_an_evidence_reference() -> None:
    with pytest.raises(module.ScorecardError, match="evidence_ref is required"):
        module.score(
            {
                "schema_version": 1,
                "provider_rights_approved": {
                    "pdl_ip": {"approved": True, "evidence_ref": None}
                },
                "company_cases": [company_case("A001", "TW")],
                "contact_cases": [],
            }
        )
