#!/usr/bin/env python3
"""Exercise every public-site locale in a real production Next.js build."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

from playwright.sync_api import ConsoleMessage, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
SERVER = WEB_DIR / ".next" / "standalone" / "server.js"
ARTIFACT_DIR = ROOT / "artifacts" / "public-locale-lab"
LOCALES = ("en", "zh-TW", "ja", "fr", "ru")
ROUTES = ("", "/products", "/rfq", "/privacy")
PORT = 3105


@dataclass
class Check:
    name: str
    status: str
    duration_ms: int
    detail: str = ""


def wait_for_server(process: subprocess.Popen[bytes], timeout: int = 90) -> None:
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Public website exited before it became ready")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/en", timeout=3) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    raise RuntimeError("Timed out waiting for the public website")


def record(checks: list[Check], name: str, operation) -> None:
    started = time.monotonic()
    try:
        detail = operation() or ""
        checks.append(Check(name, "passed", round((time.monotonic() - started) * 1000), detail))
    except Exception as exc:  # noqa: BLE001 - the lab must report every failed assertion
        checks.append(Check(name, "failed", round((time.monotonic() - started) * 1000), str(exc)))


def write_evidence(checks: list[Check], console_errors: list[str]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locales": list(LOCALES),
        "checks": [asdict(check) for check in checks],
        "console_errors": console_errors,
        "summary": {
            "passed": sum(check.status == "passed" for check in checks),
            "failed": sum(check.status == "failed" for check in checks),
        },
    }
    (ARTIFACT_DIR / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    suite = ElementTree.Element(
        "testsuite",
        name="public-locale-lab",
        tests=str(len(checks)),
        failures=str(payload["summary"]["failed"]),
    )
    for check in checks:
        case = ElementTree.SubElement(suite, "testcase", name=check.name, time=f"{check.duration_ms / 1000:.3f}")
        if check.status == "failed":
            ElementTree.SubElement(case, "failure", message=check.detail).text = check.detail
    ElementTree.ElementTree(suite).write(ARTIFACT_DIR / "junit.xml", encoding="utf-8", xml_declaration=True)


def main() -> int:
    if not SERVER.exists():
        raise SystemExit("Standalone website build is missing; run 'npm run build' in web first")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with socket.socket() as port_probe:
        if port_probe.connect_ex(("127.0.0.1", PORT)) == 0:
            raise SystemExit(f"Port {PORT} is already in use")

    server_log = (ARTIFACT_DIR / "server.log").open("wb")
    env = os.environ.copy()
    env.update({"HOSTNAME": "127.0.0.1", "PORT": str(PORT), "NODE_ENV": "production"})
    process = subprocess.Popen(
        ["node", str(SERVER)], cwd=SERVER.parent, env=env, stdout=server_log, stderr=subprocess.STDOUT
    )
    checks: list[Check] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    external_origins: set[str] = set()
    try:
        wait_for_server(process)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            challenge_requests: list[str] = []

            def fulfill_rfq_challenge(route) -> None:
                challenge_requests.append(route.request.url)
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body='{"challenge":"public-locale-lab"}',
                )

            page.route(
                "http://127.0.0.1:8000/api/v1/forms/rfq/challenge",
                fulfill_rfq_challenge,
            )

            def on_console(message: ConsoleMessage) -> None:
                if message.type == "error":
                    console_errors.append(f"{page.url}: {message.text}")

            page.on("console", on_console)
            page.on("pageerror", lambda error: page_errors.append(f"{page.url}: {error}"))

            def on_request(request) -> None:
                parsed = urlsplit(request.url)
                if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost"}:
                    external_origins.add(f"{parsed.scheme}://{parsed.netloc}")

            page.on("request", on_request)
            for locale in LOCALES:
                for route in ROUTES:
                    def verify(locale: str = locale, route: str = route) -> str:
                        response = page.goto(f"http://127.0.0.1:{PORT}/{locale}{route}", wait_until="domcontentloaded")
                        assert response and response.ok, f"HTTP failure: {response.status if response else 'no response'}"
                        assert page.locator("html").get_attribute("lang") == locale
                        assert page.locator("h1").first.inner_text().strip()
                        assert page.locator("select[aria-label] option:checked").get_attribute("value") == locale
                        metrics = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
                        assert metrics["scroll"] <= metrics["client"], f"horizontal overflow: {metrics}"
                        return page.title()

                    record(checks, f"desktop:{locale}:{route or '/'}", verify)

            def verify_sitemap() -> str:
                response = page.goto(f"http://127.0.0.1:{PORT}/sitemap.xml", wait_until="domcontentloaded")
                assert response and response.ok, f"HTTP failure: {response.status if response else 'no response'}"
                body = response.body().decode("utf-8")
                for locale in LOCALES:
                    assert f'hreflang="{locale}"' in body, f"missing hreflang for {locale}"
                assert 'hreflang="x-default"' in body
                return f"{len(body)} bytes"

            record(checks, "sitemap-five-locale-alternates", verify_sitemap)

            page.set_viewport_size({"width": 390, "height": 844})
            for locale in LOCALES:
                for route in ("", "/rfq"):
                    def verify_mobile(locale: str = locale, route: str = route) -> str:
                        page.goto(f"http://127.0.0.1:{PORT}/{locale}{route}", wait_until="domcontentloaded")
                        metrics = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
                        assert metrics["scroll"] <= metrics["client"], f"horizontal overflow: {metrics}"
                        assert page.get_by_role("button", name={
                            "en": "Open menu", "zh-TW": "開啟選單", "ja": "メニューを開く",
                            "fr": "Ouvrir le menu", "ru": "Открыть меню",
                        }[locale]).is_visible()
                        return json.dumps(metrics)

                    record(checks, f"mobile:{locale}:{route or '/'}", verify_mobile)

            page.set_viewport_size({"width": 1280, "height": 900})

            def verify_switcher() -> str:
                page.goto(f"http://127.0.0.1:{PORT}/ru/privacy", wait_until="domcontentloaded")
                page.locator("select[aria-label]").select_option("fr")
                page.wait_for_url(f"http://127.0.0.1:{PORT}/fr/privacy")
                assert page.locator("html").get_attribute("lang") == "fr"
                return page.url

            record(checks, "language-switcher-preserves-route", verify_switcher)

            def verify_rfq_challenge_stub() -> str:
                expected = len(LOCALES) * 2
                assert len(challenge_requests) == expected, (
                    f"expected {expected} RFQ challenge requests, "
                    f"received {len(challenge_requests)}"
                )
                return f"{len(challenge_requests)} requests"

            record(checks, "rfq-challenge-api-stub", verify_rfq_challenge_stub)
            page.set_viewport_size({"width": 390, "height": 844})
            for locale in ("ja", "fr", "ru"):
                page.goto(f"http://127.0.0.1:{PORT}/{locale}", wait_until="domcontentloaded")
                page.screenshot(path=ARTIFACT_DIR / f"mobile-{locale}.png", full_page=False)
            browser.close()
    except Exception as exc:  # noqa: BLE001 - preserve machine-readable failure evidence
        checks.append(Check("lab-infrastructure", "failed", 0, str(exc)))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        server_log.close()

    runtime_errors = [*console_errors, *page_errors]
    if runtime_errors:
        checks.append(Check("browser-console-errors", "failed", 0, "\n".join(runtime_errors)))
    else:
        checks.append(Check("browser-console-errors", "passed", 0))
    if external_origins:
        checks.append(Check("browser-external-requests", "failed", 0, ", ".join(sorted(external_origins))))
    else:
        checks.append(Check("browser-external-requests", "passed", 0))
    write_evidence(checks, runtime_errors)
    failed = [check for check in checks if check.status == "failed"]
    print(f"Public locale lab: {len(checks) - len(failed)}/{len(checks)} checks passed")
    for check in failed:
        print(f"FAIL {check.name}: {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
