import httpx
import pytest

from app.services.domain_verification import (
    DNSLookupError,
    inspect_custom_domain_dns,
)


def _dns_transport(records: dict[tuple[str, str], list[tuple[int, str]]]):
    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.url.params["name"], request.url.params["type"])
        answers = [
            {"name": key[0], "type": record_type, "TTL": 60, "data": value}
            for record_type, value in records.get(key, [])
        ]
        return httpx.Response(200, json={"Status": 0, "Answer": answers})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_custom_domain_requires_real_ownership_and_route_proofs() -> None:
    hostname = "www.customer.example"
    target = "edge.forgebase.com"
    token = "high-entropy-token"
    transport = _dns_transport(
        {
            (f"_forgebase-verification.{hostname}", "TXT"): [
                (16, f'"forgebase-verification={token}"')
            ],
            (hostname, "CNAME"): [(5, f"{target}.")],
            (target, "A"): [(1, "203.0.113.10")],
        }
    )

    observed = await inspect_custom_domain_dns(
        hostname, token, target, transport=transport
    )

    assert observed.ownership_verified is True
    assert observed.routing_verified is True
    assert observed.ready is True
    assert observed.cname_targets == [target]


@pytest.mark.asyncio
async def test_apex_alias_is_accepted_only_when_addresses_overlap_edge() -> None:
    hostname = "customer.example"
    target = "edge.forgebase.com"
    token = "token"
    transport = _dns_transport(
        {
            (f"_forgebase-verification.{hostname}", "TXT"): [
                (16, '"forgebase-" "verification=token"')
            ],
            (hostname, "A"): [(1, "203.0.113.10")],
            (target, "A"): [(1, "203.0.113.10"), (1, "203.0.113.11")],
        }
    )

    observed = await inspect_custom_domain_dns(
        hostname, token, target, transport=transport
    )

    assert observed.ready is True
    assert observed.domain_addresses == ["203.0.113.10"]
    assert observed.target_addresses == ["203.0.113.10", "203.0.113.11"]


@pytest.mark.asyncio
async def test_partial_dns_never_becomes_ready() -> None:
    hostname = "www.customer.example"
    target = "edge.forgebase.com"
    transport = _dns_transport(
        {
            (f"_forgebase-verification.{hostname}", "TXT"): [
                (16, '"forgebase-verification=wrong-token"')
            ],
            (hostname, "CNAME"): [(5, f"{target}.")],
        }
    )

    observed = await inspect_custom_domain_dns(
        hostname, "expected-token", target, transport=transport
    )

    assert observed.ownership_verified is False
    assert observed.routing_verified is True
    assert observed.ready is False


@pytest.mark.asyncio
async def test_resolver_failure_is_distinct_from_failed_proof() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(502))

    with pytest.raises(DNSLookupError):
        await inspect_custom_domain_dns(
            "customer.example",
            "expected-token",
            "edge.forgebase.com",
            transport=transport,
        )
