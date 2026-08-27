"""Trusted-proxy-aware client IP extraction.

Forwarding headers are ignored unless the direct peer belongs to an explicitly
configured trusted proxy network.  This prevents public callers from forging
the value later used for company identification.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable

from fastapi import Request

from app.core.config import settings

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_trusted_proxy_cidrs(raw: str) -> tuple[IPNetwork, ...]:
    networks: list[IPNetwork] = []
    for item in raw.split(","):
        value = item.strip()
        if value:
            networks.append(ipaddress.ip_network(value, strict=False))
    return tuple(networks)


def resolve_client_ip(
    peer_ip: str | None,
    forwarded_for: str | None,
    trusted_networks: Iterable[IPNetwork],
) -> str | None:
    if not peer_ip:
        return None
    try:
        peer = ipaddress.ip_address(peer_ip)
    except ValueError:
        return None

    networks = tuple(trusted_networks)
    peer_is_trusted = any(peer in network for network in networks)
    if not forwarded_for or not peer_is_trusted:
        return str(peer)

    forwarded: list[IPAddress] = []
    try:
        for item in forwarded_for.split(","):
            forwarded.append(ipaddress.ip_address(item.strip()))
    except ValueError:
        # Reject the complete untrusted chain instead of accepting a partial,
        # attacker-controlled prefix.
        return str(peer)

    for address in reversed(forwarded):
        if not any(address in network for network in networks):
            return str(address)
    return str(forwarded[0]) if forwarded else str(peer)


def get_request_client_ip(request: Request) -> str | None:
    peer_ip = getattr(request.client, "host", None)
    trusted = parse_trusted_proxy_cidrs(settings.TRUSTED_PROXY_CIDRS)
    return resolve_client_ip(peer_ip, request.headers.get("x-forwarded-for"), trusted)
