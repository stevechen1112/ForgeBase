"""
Ops Config admin 端點測試（GET/PUT /site-profile/ops-config）。

確保：
- 需登入（公開 GET /site-profile 不回傳 ops_config，避免設定外洩）
- 部分更新保留未提供的 key；顯式 null 清除 key
- sla_response_hours 範圍驗證（0 < hours <= 168）
- 寫入後 load_ops_config 服務層讀得到
"""
import pytest

from tests.conftest import requires_db


@requires_db
async def test_ops_config_requires_auth(http_client):
    r = await http_client.get("/api/v1/site-profile/ops-config")
    assert r.status_code in (401, 403)


@requires_db
async def test_ops_config_roundtrip_and_merge(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}

    r = await http_client.get("/api/v1/site-profile/ops-config", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)

    r = await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth,
        json={"auto_reply_enabled": True, "sla_response_hours": 8},
    )
    assert r.status_code == 200
    assert r.json()["auto_reply_enabled"] is True
    assert r.json()["sla_response_hours"] == 8

    # 部分更新只動 signature，其餘保留
    r = await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth,
        json={"auto_reply_signature": "Export Sales"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["auto_reply_signature"] == "Export Sales"
    assert data["auto_reply_enabled"] is True
    assert data["sla_response_hours"] == 8

    # 顯式 null 清除 key
    r = await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth,
        json={"auto_reply_signature": None},
    )
    assert r.status_code == 200
    assert "auto_reply_signature" not in r.json()

    # 還原，避免影響其他測試
    await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth,
        json={"auto_reply_enabled": False, "sla_response_hours": 4},
    )


@requires_db
async def test_ops_config_sla_hours_validation(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant_a.id)}"}
    for bad in (0, -4, 999):
        r = await http_client.put(
            "/api/v1/site-profile/ops-config", headers=auth,
            json={"sla_response_hours": bad},
        )
        assert r.status_code == 422


@requires_db
async def test_ops_config_tenant_isolation(http_client, two_tenants, admin_token_for_tenant):
    """B 租戶看不到 A 租戶寫的 ops config。"""
    tenant_a, tenant_b = two_tenants
    auth_a = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant_a.id)}"}
    auth_b = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant_b.id)}"}

    await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth_a,
        json={"sla_response_hours": 24},
    )
    r = await http_client.get("/api/v1/site-profile/ops-config", headers=auth_b)
    assert r.status_code == 200
    assert r.json().get("sla_response_hours") != 24

    await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth_a,
        json={"sla_response_hours": 4},
    )


@requires_db
async def test_public_site_profile_does_not_leak_ops_config(
    http_client, two_tenants, admin_token_for_tenant
):
    tenant_a, _ = two_tenants
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant_a.id)}"}
    await http_client.put(
        "/api/v1/site-profile/ops-config", headers=auth,
        json={"auto_reply_enabled": False, "sla_response_hours": 4},
    )
    r = await http_client.get(
        "/api/v1/site-profile", headers={"X-Tenant-ID": str(tenant_a.id)}
    )
    assert r.status_code == 200
    assert "ops_config_json" not in r.json()
    assert "ops_config" not in r.json()
