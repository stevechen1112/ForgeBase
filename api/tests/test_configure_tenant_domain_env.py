from __future__ import annotations

import importlib.util
import stat
from pathlib import Path


SCRIPT = Path("/deploy/configure-tenant-domain-env.py")
SPEC = importlib.util.spec_from_file_location("configure_tenant_domain_env", SCRIPT)
assert SPEC and SPEC.loader
configure_tenant_domain_env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(configure_tenant_domain_env)


def test_configure_env_is_idempotent_and_preserves_existing_secret(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DOMAIN=pcbrm.tw\n"
        "TENANT_ROUTING_SECRET=stale-duplicate\n"
        "TENANT_ROUTING_SECRET=existing-secret-with-more-than-forty-three-characters-0001\n"
    )

    first = configure_tenant_domain_env.configure_env(
        env_file,
        base_domain="forgebase.com",
        cname_target="edge.forgebase.com",
        resolver_url="https://cloudflare-dns.com/dns-query",
        timeout_seconds=8,
    )
    first_text = env_file.read_text()
    second = configure_tenant_domain_env.configure_env(
        env_file,
        base_domain="forgebase.com",
        cname_target="edge.forgebase.com",
        resolver_url="https://cloudflare-dns.com/dns-query",
        timeout_seconds=8,
    )

    assert first == second
    assert first["TENANT_ROUTING_SECRET"] == "existing-secret-with-more-than-forty-three-characters-0001"
    assert env_file.read_text() == first_text
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert "TENANT_BASE_DOMAIN=forgebase.com" in first_text
    assert "TENANT_CNAME_TARGET=edge.forgebase.com" in first_text
    assert first_text.count("TENANT_ROUTING_SECRET=") == 1


def test_configure_env_replaces_placeholder_with_high_entropy_secret(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("DOMAIN=pcbrm.tw\nTENANT_ROUTING_SECRET=CHANGE_ME\n")

    result = configure_tenant_domain_env.configure_env(
        env_file,
        base_domain="forgebase.com",
        cname_target="edge.forgebase.com",
        resolver_url="https://cloudflare-dns.com/dns-query",
        timeout_seconds=8,
    )

    assert len(result["TENANT_ROUTING_SECRET"]) >= 43
    assert "CHANGE_ME" not in env_file.read_text()
    assert env_file.read_text().count("TENANT_ROUTING_SECRET=") == 1
