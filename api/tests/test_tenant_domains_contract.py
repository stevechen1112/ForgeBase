from app.models.tenant_domain import (
    DOMAIN_STATUSES,
    DOMAIN_TYPES,
    TLS_STATUSES,
    TenantDomain,
)
from app.services.tenant_domains import (
    forgebase_hostname_for_slug,
    normalize_hostname,
    validate_custom_hostname,
    valid_hostname,
)
import pytest
from sqlalchemy import Index, UniqueConstraint


def test_hostname_normalization_and_validation_are_canonical() -> None:
    assert normalize_hostname("  AxisForm.ForgeBase.com. ") == "axisform.forgebase.com"
    assert normalize_hostname("例子.公司") == "xn--fsqu00a.xn--55qx5d"
    assert normalize_hostname("bad\ud800.example") is None
    assert valid_hostname("axisform.forgebase.com") is True
    assert valid_hostname("localhost") is False
    assert valid_hostname("192.0.2.10") is False
    assert valid_hostname("-invalid.example") is False
    assert forgebase_hostname_for_slug("axisform", "forgebase.com") == "axisform.forgebase.com"
    with pytest.raises(ValueError):
        forgebase_hostname_for_slug("admin", "forgebase.com")
    assert validate_custom_hostname("WWW.Customer.Example", "forgebase.com") == (
        "www.customer.example"
    )
    with pytest.raises(ValueError):
        validate_custom_hostname("axisform.forgebase.com", "forgebase.com")


def test_tenant_domain_contract_has_one_global_host_and_one_canonical_per_tenant() -> None:
    table = TenantDomain.__table__
    constraints = {
        item.name: item
        for item in table.constraints
        if isinstance(item, UniqueConstraint)
    }
    indexes = {item.name: item for item in table.indexes if isinstance(item, Index)}

    assert "uq_tenant_domains_hostname" in constraints
    canonical = indexes["uq_tenant_domains_canonical_per_tenant"]
    assert canonical.unique is True
    assert str(canonical.dialect_options["postgresql"]["where"]) == "is_canonical"
    assert str(canonical.dialect_options["sqlite"]["where"]) == "is_canonical = 1"
    assert DOMAIN_TYPES == {"forgebase_subdomain", "custom"}
    assert "active" in DOMAIN_STATUSES
    assert "active" in TLS_STATUSES
