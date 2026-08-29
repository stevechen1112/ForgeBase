"""Authoritative DNS checks for customer-owned tenant domains."""

from __future__ import annotations

import asyncio
import ipaddress
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.services.tenant_domains import normalize_hostname

_DNS_TYPES = {"A": 1, "CNAME": 5, "TXT": 16, "AAAA": 28}


class DNSLookupError(RuntimeError):
    """The configured resolver could not provide a usable DNS response."""


@dataclass(frozen=True)
class DomainDNSObservation:
    verification_hostname: str
    expected_txt_value: str
    expected_routing_target: str
    txt_values: list[str]
    cname_targets: list[str]
    domain_addresses: list[str]
    target_addresses: list[str]
    ownership_verified: bool
    routing_verified: bool

    @property
    def ready(self) -> bool:
        return self.ownership_verified and self.routing_verified

    def payload(self) -> dict[str, Any]:
        return {**asdict(self), "ready": self.ready}


def verification_hostname(hostname: str) -> str:
    return f"_forgebase-verification.{hostname}"


def verification_txt_value(token: str) -> str:
    return f"forgebase-verification={token}"


def _clean_txt(value: str) -> str:
    # DoH represents long TXT values as adjacent quoted chunks. Joining the
    # quoted content matches the DNS wire value and keeps exact-token checks.
    stripped = value.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        return stripped[1:-1].replace('" "', "")
    return stripped


def _clean_address(value: str) -> str | None:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


async def _query(
    client: httpx.AsyncClient, name: str, record_type: str
) -> list[str]:
    try:
        response = await client.get(
            settings.DOMAIN_DNS_RESOLVER_URL,
            params={"name": name, "type": record_type},
            headers={"Accept": "application/dns-json"},
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise DNSLookupError(f"DNS lookup failed for {name} {record_type}") from exc

    if not isinstance(payload, dict):
        raise DNSLookupError(f"DNS resolver returned an invalid response for {name}")
    status = payload.get("Status")
    if status not in {0, 3}:
        raise DNSLookupError(f"DNS resolver returned status {status} for {name}")
    expected_type = _DNS_TYPES[record_type]
    answers = payload.get("Answer") or []
    if not isinstance(answers, list):
        raise DNSLookupError(f"DNS resolver returned invalid answers for {name}")
    return [
        str(answer.get("data", ""))
        for answer in answers
        if isinstance(answer, dict) and answer.get("type") == expected_type
    ]


async def inspect_custom_domain_dns(
    hostname: str,
    token: str,
    routing_target: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> DomainDNSObservation:
    """Prove both ownership and that traffic is routed to ForgeBase.

    A direct CNAME is preferred. Apex domains are also supported when their
    A/AAAA result overlaps the current A/AAAA result of the ForgeBase edge.
    """
    expected_target = normalize_hostname(routing_target)
    if not expected_target:
        raise ValueError("Invalid ForgeBase routing target")
    proof_host = verification_hostname(hostname)
    expected_txt = verification_txt_value(token)

    async with httpx.AsyncClient(
        timeout=settings.DOMAIN_DNS_TIMEOUT_SECONDS,
        transport=transport,
    ) as client:
        (
            txt_raw,
            cname_raw,
            domain_a,
            domain_aaaa,
            target_a,
            target_aaaa,
        ) = await asyncio.gather(
            _query(client, proof_host, "TXT"),
            _query(client, hostname, "CNAME"),
            _query(client, hostname, "A"),
            _query(client, hostname, "AAAA"),
            _query(client, expected_target, "A"),
            _query(client, expected_target, "AAAA"),
        )

    txt_values = sorted({_clean_txt(value) for value in txt_raw})
    cname_targets = sorted(
        {
            normalized
            for value in cname_raw
            if (normalized := normalize_hostname(value))
        }
    )
    domain_addresses = sorted(
        {
            address
            for value in [*domain_a, *domain_aaaa]
            if (address := _clean_address(value))
        }
    )
    target_addresses = sorted(
        {
            address
            for value in [*target_a, *target_aaaa]
            if (address := _clean_address(value))
        }
    )
    ownership_verified = expected_txt in txt_values
    routing_verified = expected_target in cname_targets or bool(
        set(domain_addresses) & set(target_addresses)
    )
    return DomainDNSObservation(
        verification_hostname=proof_host,
        expected_txt_value=expected_txt,
        expected_routing_target=expected_target,
        txt_values=txt_values,
        cname_targets=cname_targets,
        domain_addresses=domain_addresses,
        target_addresses=target_addresses,
        ownership_verified=ownership_verified,
        routing_verified=routing_verified,
    )
