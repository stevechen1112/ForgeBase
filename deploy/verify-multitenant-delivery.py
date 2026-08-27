"""Verify public delivery, isolation, load and optional synthetic conversion.

The default mode is read-only. ``--exercise-conversions`` creates an
unambiguously synthetic visitor, chat and RFQ for the AxisForm test tenant.
This script never sends mail.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid

import httpx


API = "https://pcbrm.tw"
AXIS_SITE = "https://axisform.172-233-64-5.sslip.io"
AXIS = {"X-Tenant-ID": "axisform-precision"}
NORTH = {"X-Tenant-ID": "default-tenant"}


async def require_json(
    client: httpx.AsyncClient, path: str, headers: dict[str, str]
) -> dict:
    response = await client.get(f"{API}{path}", headers=headers)
    response.raise_for_status()
    return response.json()


async def main(exercise_conversions: bool, concurrency: int) -> None:
    limits = httpx.Limits(
        max_connections=max(concurrency, 20),
        max_keepalive_connections=max(concurrency, 20),
    )
    async with httpx.AsyncClient(
        timeout=30, follow_redirects=True, limits=limits
    ) as client:
        axis_profile, north_profile = await asyncio.gather(
            require_json(client, "/api/v1/site-profile", AXIS),
            require_json(client, "/api/v1/site-profile", NORTH),
        )
        assert axis_profile["brand_name"] == "AxisForm Precision", axis_profile
        assert north_profile["brand_name"] != "AxisForm Precision", north_profile
        assert axis_profile["theme_key"] == "precision"
        assert axis_profile.get("site_copy_json")
        axis_copy = json.loads(axis_profile["site_copy_json"])
        assert axis_copy["common"]["brandName"] == "AxisForm Precision"
        assert "NorthForge" not in json.dumps(axis_copy["header"])
        assert "NorthForge" not in json.dumps(axis_copy["home"]["hero"])

        axis_products, north_products = await asyncio.gather(
            require_json(
                client, "/api/v1/content/products?locale=en&page_size=100", AXIS
            ),
            require_json(
                client, "/api/v1/content/products?locale=en&page_size=100", NORTH
            ),
        )
        axis_models = {item["model_number"] for item in axis_products["data"]}
        north_models = {item["model_number"] for item in north_products["data"]}
        assert axis_models == {"DEMO-M01", "DEMO-T08", "DEMO-M14"}, axis_models
        assert not axis_models & north_models

        site_response, health_response = await asyncio.gather(
            client.get(AXIS_SITE), client.get(f"{AXIS_SITE}/api/health/assets")
        )
        site_response.raise_for_status()
        health_response.raise_for_status()
        assert "AxisForm Precision" in site_response.text
        asset_health = health_response.json()
        assert asset_health["status"] in {"ok", "ok-with-warnings"}, asset_health
        asset_urls = [
            f"{AXIS_SITE}/demo/precision-machining/assets/generated/home-hero-cnc-facility.png",
            f"{AXIS_SITE}/demo/precision-machining/assets/generated/parts-precision-components.png",
            f"{AXIS_SITE}/demo/precision-machining/assets/generated/quality-cmm-inspection.png",
        ]
        asset_responses = await asyncio.gather(
            *(client.get(url) for url in asset_urls)
        )
        assert all(
            response.status_code == 200
            and response.headers.get("content-type", "").startswith("image/")
            for response in asset_responses
        )

        load_paths = [
            AXIS_SITE,
            f"{AXIS_SITE}/products",
            f"{AXIS_SITE}/applications",
            f"{AXIS_SITE}/rfq",
            f"{AXIS_SITE}/api/health/assets",
        ]
        started = time.perf_counter()
        responses = await asyncio.gather(
            *(
                client.get(load_paths[index % len(load_paths)])
                for index in range(concurrency)
            )
        )
        elapsed = time.perf_counter() - started
        failures = [
            (response.request.url.path, response.status_code)
            for response in responses
            if response.status_code != 200
        ]
        assert not failures, failures

        result: dict = {
            "profiles_isolated": True,
            "product_models_isolated": True,
            "asset_health": asset_health["status"],
            "load": {
                "requests": concurrency,
                "failures": 0,
                "elapsed_seconds": round(elapsed, 3),
                "requests_per_second": round(concurrency / elapsed, 1),
            },
        }

        if exercise_conversions:
            visitor_id, session_id = str(uuid.uuid4()), str(uuid.uuid4())
            event = await client.post(
                f"{API}/api/v1/tracking/events",
                headers=AXIS,
                json={
                    "event_name": "page_view",
                    "visitor_id": visitor_id,
                    "session_id": session_id,
                    "page_url": AXIS_SITE,
                    "page_type": "home",
                    "locale": "en",
                    "analytics_consent": True,
                },
            )
            event.raise_for_status()
            chat = await client.post(
                f"{API}/api/v1/chat/sessions",
                headers=AXIS,
                json={
                    "visitor_id": visitor_id,
                    "session_id": session_id,
                    "context_page": "/",
                    "context_entity_type": "home",
                    "locale": "en",
                },
            )
            chat.raise_for_status()
            chat_id = chat.json()["data"]["chat_session_id"]
            cross_tenant = await client.post(
                f"{API}/api/v1/chat/sessions/{chat_id}/messages",
                headers=NORTH,
                json={
                    "visitor_id": visitor_id,
                    "content": "Cross-tenant isolation probe",
                },
            )
            assert cross_tenant.status_code == 404, cross_tenant.text

            challenge = await require_json(
                client, "/api/v1/forms/rfq/challenge", AXIS
            )
            await asyncio.sleep(2.2)
            email = f"forgebase-axisform-e2e+{int(time.time())}@example.com"
            rfq = await client.post(
                f"{API}/api/v1/forms/rfq",
                headers=AXIS,
                json={
                    "full_name": "ForgeBase E2E Verification",
                    "email": email,
                    "company_name": "Synthetic Test Company",
                    "country": "Taiwan",
                    "job_title": "Automated QA",
                    "quantity": "250 demo units",
                    "specifications": (
                        "DEMO-M01; Al 6061; plus/minus 0.015 mm; "
                        "black anodized. Synthetic test only."
                    ),
                    "timeline": "evaluating",
                    "message": (
                        "AUTOMATED FORGEBASE TEST -- DO NOT REPLY. Verify tenant "
                        "isolation, RFQ quality, task and outcome flow."
                    ),
                    "how_did_you_find_us": "direct",
                    "consent": True,
                    "visitor_id": visitor_id,
                    "source_page": "/rfq?e2e=1",
                    "bot_challenge": challenge["challenge"],
                    "website": "",
                    "incoterm": "EXW",
                    "annual_volume": "1000 demo units",
                    "is_trial_order": True,
                    "required_certs": [],
                    "target_price": "test-only",
                },
            )
            rfq.raise_for_status()
            result["conversion"] = {
                "visitor_id": visitor_id,
                "chat_session_id": chat_id,
                "rfq_number": rfq.json()["rfq_number"],
                "email": email,
                "cross_tenant_chat_blocked": True,
            }

        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise-conversions", action="store_true")
    parser.add_argument("--concurrency", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(main(args.exercise_conversions, max(1, min(args.concurrency, 500))))
