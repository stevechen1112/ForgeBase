#!/usr/bin/env python3
"""Verify production recovery evidence through the real Platform Admin UI."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def validate_resource_page(text: str) -> dict[str, object]:
    required = (
        "外部服務與資料",
        "異地備份",
        "備份與還原皆已驗證",
        "最後備份證據",
        "還原演練",
    )
    missing = [label for label in required if label not in text]
    if missing:
        raise ValueError(f"Missing production resource labels: {', '.join(missing)}")
    for label in ("最後備份證據", "還原演練"):
        section = text.split(label, 1)[1].lstrip().splitlines()
        value = section[0].strip() if section else ""
        if not value or value == "尚未記錄":
            raise ValueError(f"{label} does not contain verified evidence")
    return {
        "schema_version": 1,
        "status": "passed",
        "recovery_evidence_visible": True,
    }


def main() -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    base_url = os.environ.get("FORGEBASE_PRODUCTION_URL", "https://pcbrm.tw").rstrip(
        "/"
    )
    email = os.environ.get("FORGEBASE_PLATFORM_EMAIL", "").strip()
    password = os.environ.get("FORGEBASE_PLATFORM_PASSWORD", "")
    output_dir = Path(
        os.environ.get("FORGEBASE_BROWSER_EVIDENCE_DIR", "artifacts/production-admin")
    )
    if not email or len(password) < 20:
        raise SystemExit("Protected platform browser credentials are required")
    output_dir.mkdir(parents=True, exist_ok=True)

    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(locale="zh-TW")
        page = context.new_page()
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.goto(
            f"{base_url}/backend/platform/login",
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        page.get_by_label("Email").fill(email)
        page.get_by_label("密碼").fill(password)
        page.get_by_role("button", name="登入平台管理").click()
        try:
            page.wait_for_url("**/backend/platform/overview", timeout=20_000)
        except PlaywrightTimeoutError as exc:
            page.screenshot(
                path=output_dir / "platform-login-failure.png", full_page=True
            )
            alert = page.get_by_role("alert").last
            detail = (
                alert.inner_text(timeout=2_000) if alert.count() else "unknown error"
            )
            raise RuntimeError(
                f"Platform Admin browser login failed: {detail}"
            ) from exc
        page.goto(
            f"{base_url}/backend/platform/resources",
            wait_until="networkidle",
            timeout=60_000,
        )
        page.get_by_role("heading", name="外部服務與資料").wait_for(timeout=30_000)
        page.get_by_text("備份與還原皆已驗證", exact=True).wait_for(timeout=30_000)
        body_text = page.locator("body").inner_text(timeout=30_000)
        report = validate_resource_page(body_text)
        page.screenshot(path=output_dir / "platform-resources.png", full_page=True)
        if console_errors:
            raise RuntimeError(
                f"Production resource page emitted {len(console_errors)} console errors"
            )
        report.update(
            {
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "url": page.url,
                "console_error_count": 0,
            }
        )
        browser.close()

    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Production Platform Admin recovery evidence verified in Chromium")


if __name__ == "__main__":
    main()
