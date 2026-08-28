#!/usr/bin/env python3
"""Score de-identified company/contact provider POC evidence."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CASE_ID = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,31}$")
PROVIDER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
MARKET = re.compile(r"^[A-Z]{2,8}$")
EVIDENCE_REF = re.compile(r"^[A-Z0-9][A-Z0-9._:/-]{2,127}$")
EXCLUDED_NETWORK_CLASSES = {"bot", "hosting", "isp", "mobile", "vpn"}


class ScorecardError(ValueError):
    """Invalid or unsafe scorecard evidence."""


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ScorecardError(f"{field} must be a boolean")
    return value


def _count(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ScorecardError(f"{field} must be a non-negative integer")
    return value


def _number(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ScorecardError(f"{field} must be a non-negative number")
    return float(value)


def _identity(row: dict[str, Any], *, prefix: str) -> tuple[str, str, str]:
    case_id = row.get("case_id")
    provider = row.get("provider")
    market = row.get("market")
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
        raise ScorecardError(f"{prefix}.case_id must be an opaque uppercase id")
    if not isinstance(provider, str) or not PROVIDER.fullmatch(provider):
        raise ScorecardError(f"{prefix}.provider must be a safe provider slug")
    if not isinstance(market, str) or not MARKET.fullmatch(market):
        raise ScorecardError(f"{prefix}.market must be an uppercase market code")
    return case_id, provider, market


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _money(numerator: float, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _load_rows(payload: dict[str, Any], field: str) -> list[dict[str, Any]]:
    rows = payload.get(field)
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ScorecardError(f"{field} must be an array of objects")
    return rows


def _rights(payload: dict[str, Any]) -> dict[str, bool]:
    rights = payload.get("provider_rights_approved")
    if not isinstance(rights, dict) or not rights:
        raise ScorecardError("provider_rights_approved must be a non-empty object")
    result = {}
    for provider, decision in rights.items():
        if not isinstance(provider, str) or not PROVIDER.fullmatch(provider):
            raise ScorecardError("provider_rights_approved contains an unsafe slug")
        if not isinstance(decision, dict) or set(decision) != {"approved", "evidence_ref"}:
            raise ScorecardError(f"rights.{provider} must contain approved and evidence_ref")
        approved = _boolean(decision.get("approved"), f"rights.{provider}.approved")
        evidence_ref = decision.get("evidence_ref")
        if approved and (
            not isinstance(evidence_ref, str) or not EVIDENCE_REF.fullmatch(evidence_ref)
        ):
            raise ScorecardError(f"rights.{provider}.evidence_ref is required when approved")
        if not approved and evidence_ref is not None:
            raise ScorecardError(f"rights.{provider}.evidence_ref must be null when unapproved")
        result[provider] = approved
    return result


def _company_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    prefix = f"company_cases[{index}]"
    case_id, provider, market = _identity(row, prefix=prefix)
    allowed = {
        "case_id",
        "provider",
        "market",
        "network_class",
        "eligible",
        "matched",
        "high_confidence",
        "review",
        "conflict",
        "estimated_cost",
        "latency_ms",
    }
    if set(row) - allowed:
        raise ScorecardError(f"{prefix} contains unsupported fields")
    network_class = row.get("network_class")
    if network_class not in {"bot", "corporate", "hosting", "isp", "mobile", "vpn"}:
        raise ScorecardError(f"{prefix}.network_class is invalid")
    review = row.get("review")
    if review not in {"correct", "incorrect", "unreviewed"}:
        raise ScorecardError(f"{prefix}.review is invalid")
    normalized = {
        "case_id": case_id,
        "provider": provider,
        "market": market,
        "network_class": network_class,
        "eligible": _boolean(row.get("eligible"), f"{prefix}.eligible"),
        "matched": _boolean(row.get("matched"), f"{prefix}.matched"),
        "high_confidence": _boolean(
            row.get("high_confidence"), f"{prefix}.high_confidence"
        ),
        "review": review,
        "conflict": _boolean(row.get("conflict"), f"{prefix}.conflict"),
        "estimated_cost": _number(row.get("estimated_cost"), f"{prefix}.estimated_cost"),
        "latency_ms": _number(row.get("latency_ms"), f"{prefix}.latency_ms"),
    }
    if review != "unreviewed" and not normalized["matched"]:
        raise ScorecardError(f"{prefix} cannot review an unmatched result")
    return normalized


def _contact_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    prefix = f"contact_cases[{index}]"
    case_id, provider, market = _identity(row, prefix=prefix)
    allowed = {
        "case_id",
        "provider",
        "market",
        "candidate_count",
        "reviewed_count",
        "relevant_count",
        "verified_business_email_count",
        "fresh_count",
        "invalid_or_suppressed_count",
        "estimated_cost",
        "latency_ms",
    }
    if set(row) - allowed:
        raise ScorecardError(f"{prefix} contains unsupported fields")
    counts = {
        key: _count(row.get(key), f"{prefix}.{key}")
        for key in (
            "candidate_count",
            "reviewed_count",
            "relevant_count",
            "verified_business_email_count",
            "fresh_count",
            "invalid_or_suppressed_count",
        )
    }
    candidates = counts["candidate_count"]
    if any(value > candidates for key, value in counts.items() if key != "candidate_count"):
        raise ScorecardError(f"{prefix} counts cannot exceed candidate_count")
    if counts["relevant_count"] > counts["reviewed_count"]:
        raise ScorecardError(f"{prefix}.relevant_count cannot exceed reviewed_count")
    return {
        "case_id": case_id,
        "provider": provider,
        "market": market,
        **counts,
        "estimated_cost": _number(row.get("estimated_cost"), f"{prefix}.estimated_cost"),
        "latency_ms": _number(row.get("latency_ms"), f"{prefix}.latency_ms"),
    }


def _company_metrics(rows: list[dict[str, Any]], rights: dict[str, bool]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["provider"], row["market"])].append(row)
    result = []
    for (provider, market), items in sorted(groups.items()):
        eligible = sum(item["eligible"] for item in items)
        matched = sum(item["eligible"] and item["matched"] for item in items)
        reviewed = [
            item
            for item in items
            if item["high_confidence"] and item["review"] != "unreviewed"
        ]
        correct = sum(item["review"] == "correct" for item in reviewed)
        unsafe = sum(
            item["matched"] and item["network_class"] in EXCLUDED_NETWORK_CLASSES
            for item in items
        )
        cost = sum(item["estimated_cost"] for item in items)
        latency = sum(item["latency_ms"] for item in items) / len(items)
        gates = {
            "rights_approved": rights.get(provider, False),
            "high_confidence_sample_at_least_50": len(reviewed) >= 50,
            "high_confidence_precision_at_least_90pct": bool(reviewed)
            and correct / len(reviewed) >= 0.90,
            "excluded_network_matches_zero": unsafe == 0,
        }
        result.append(
            {
                "provider": provider,
                "market": market,
                "cases": len(items),
                "eligible_cases": eligible,
                "matched_eligible_cases": matched,
                "eligible_coverage": _rate(matched, eligible),
                "high_confidence_reviewed": len(reviewed),
                "high_confidence_correct": correct,
                "high_confidence_precision": _rate(correct, len(reviewed)),
                "conflicts": sum(item["conflict"] for item in items),
                "unsafe_excluded_network_matches": unsafe,
                "estimated_cost_total": round(cost, 6),
                "estimated_cost_per_correct_company": _money(cost, correct),
                "average_latency_ms": round(latency, 2),
                "gates": gates,
                "gate_passed": all(gates.values()),
            }
        )
    return result


def _contact_metrics(rows: list[dict[str, Any]], rights: dict[str, bool]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["provider"], row["market"])].append(row)
    result = []
    for (provider, market), items in sorted(groups.items()):
        candidates = sum(item["candidate_count"] for item in items)
        reviewed = sum(item["reviewed_count"] for item in items)
        relevant = sum(item["relevant_count"] for item in items)
        verified = sum(item["verified_business_email_count"] for item in items)
        fresh = sum(item["fresh_count"] for item in items)
        unsafe = sum(item["invalid_or_suppressed_count"] for item in items)
        cost = sum(item["estimated_cost"] for item in items)
        latency = sum(item["latency_ms"] for item in items) / len(items)
        gates = {
            "rights_approved": rights.get(provider, False),
            "reviewed_sample_at_least_50": reviewed >= 50,
            "persona_relevance_at_least_70pct": bool(reviewed)
            and relevant / reviewed >= 0.70,
            "invalid_or_suppressed_candidates_zero": unsafe == 0,
        }
        result.append(
            {
                "provider": provider,
                "market": market,
                "queries": len(items),
                "queries_with_candidates": sum(item["candidate_count"] > 0 for item in items),
                "query_coverage": _rate(
                    sum(item["candidate_count"] > 0 for item in items), len(items)
                ),
                "candidate_count": candidates,
                "reviewed_count": reviewed,
                "relevant_count": relevant,
                "persona_relevance_rate": _rate(relevant, reviewed),
                "verified_business_email_rate": _rate(verified, candidates),
                "source_fresh_rate": _rate(fresh, candidates),
                "invalid_or_suppressed_count": unsafe,
                "estimated_cost_total": round(cost, 6),
                "estimated_cost_per_relevant_contact": _money(cost, relevant),
                "average_latency_ms": round(latency, 2),
                "gates": gates,
                "gate_passed": all(gates.values()),
            }
        )
    return result


def score(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ScorecardError("unsupported schema_version")
    rights = _rights(payload)
    company_rows = [
        _company_row(row, index)
        for index, row in enumerate(_load_rows(payload, "company_cases"))
    ]
    contact_rows = [
        _contact_row(row, index)
        for index, row in enumerate(_load_rows(payload, "contact_cases"))
    ]
    for label, rows in (("company", company_rows), ("contact", contact_rows)):
        identities = [(row["case_id"], row["provider"]) for row in rows]
        if len(identities) != len(set(identities)):
            raise ScorecardError(f"duplicate {label} case/provider pair")
    used_providers = {row["provider"] for row in company_rows + contact_rows}
    if not used_providers <= set(rights):
        raise ScorecardError("every tested provider must have an explicit rights decision")
    company = _company_metrics(company_rows, rights)
    contacts = _contact_metrics(contact_rows, rights)
    all_rows = company + contacts
    blockers = []
    if not company:
        blockers.append("no_company_evidence")
    if not contacts:
        blockers.append("no_contact_evidence")
    if any(not row["gates"]["rights_approved"] for row in all_rows):
        blockers.append("provider_rights_not_approved")
    if any(not row["gate_passed"] for row in all_rows):
        blockers.append("quality_or_safety_gate_not_passed")
    markets = {row["market"] for row in all_rows}
    if len(markets) < 2:
        blockers.append("fewer_than_two_markets_tested")
    provider_markets: dict[tuple[str, str], set[str]] = defaultdict(set)
    for layer, rows in (("company", company), ("contact", contacts)):
        for row in rows:
            provider_markets[(layer, row["provider"])].add(row["market"])
    if any(len(tested) < 2 for tested in provider_markets.values()):
        blockers.append("provider_market_coverage_incomplete")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company_identification": company,
        "contact_enrichment": contacts,
        "assessment": {
            "status": "decision_ready" if not blockers else "evidence_incomplete",
            "decision_ready": not blockers,
            "markets_tested": sorted(markets),
            "blockers": blockers,
        },
        "privacy": {
            "case_level_rows_in_report": False,
            "raw_ip_in_input_or_report": False,
            "company_names_or_domains_in_input_or_report": False,
            "contact_names_or_addresses_in_input_or_report": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-decision-ready", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScorecardError("input must be a JSON object")
    report = score(payload)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return int(args.require_decision_ready and not report["assessment"]["decision_ready"])


if __name__ == "__main__":
    raise SystemExit(main())
