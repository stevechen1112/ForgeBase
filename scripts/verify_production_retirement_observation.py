#!/usr/bin/env python3
"""Verify the production retirement state through the real Platform Admin UI."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def validate_retirement_page(text: str) -> dict[str, object]:
    required = (
        "功能退場稽核",
        "AgentOS／automation runtime",
        "ML scoring 線上 runtime／UI",
        "AI relation 推薦介面",
        "Telegram 通知渠道",
        "LINE 通知渠道",
        "重複 Copilot floating widget",
        "不安全且未接線的舊 IP resolver",
    )
    missing = [label for label in required if label not in text]
    if missing:
        raise ValueError(f"Missing retirement labels: {', '.join(missing)}")

    def candidate_segment(label: str) -> str:
        remainder = text.split(label, 1)[1]
        stops = [
            position
            for other in required
            if other != label and (position := remainder.find(other)) >= 0
        ]
        return remainder[: min(stops)] if stops else remainder

    for label in (
        "AgentOS／automation runtime",
        "ML scoring 線上 runtime／UI",
        "AI relation 推薦介面",
        "Telegram 通知渠道",
        "LINE 通知渠道",
    ):
        segment = candidate_segment(label)
        if "觀察中" not in segment or "disabled" not in segment:
            raise ValueError(f"{label} is not visibly disabled and observing")

    for label in ("Telegram 通知渠道", "LINE 通知渠道"):
        segment = candidate_segment(label)
        if "／60 天" not in segment or "觀察期尚未完成" not in segment:
            raise ValueError(f"{label} does not show the mandatory 60-day window")

    return {
        "schema_version": 1,
        "status": "passed",
        "disabled_candidates_visible": 5,
        "notification_channels_observing": True,
        "new_removals_authorized": [],
    }


def main() -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    base_url = os.environ.get("FORGEBASE_PRODUCTION_URL", "https://pcbrm.tw").rstrip("/")
    email = os.environ.get("FORGEBASE_PLATFORM_EMAIL", "").strip()
    password = os.environ.get("FORGEBASE_PLATFORM_PASSWORD", "")
    output_dir = Path(
        os.environ.get(
            "FORGEBASE_BROWSER_EVIDENCE_DIR",
            "artifacts/production-retirement",
        )
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
        page.goto(f"{base_url}/backend/platform/login", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(1_000)
        page.get_by_label("Email").fill(email)
        page.get_by_label("密碼").fill(password)
        page.get_by_role("button", name="登入平台管理").click()
        try:
            page.wait_for_url("**/backend/platform/overview", timeout=20_000)
        except PlaywrightTimeoutError as exc:
            page.screenshot(path=output_dir / "platform-login-failure.png", full_page=True)
            raise RuntimeError("Platform Admin browser login failed") from exc

        page.goto(
            f"{base_url}/backend/platform/retirement",
            wait_until="networkidle",
            timeout=60_000,
        )
        page.get_by_role("heading", name="功能退場稽核").wait_for(timeout=30_000)
        page.get_by_text("Telegram 通知渠道", exact=True).wait_for(timeout=30_000)
        page.get_by_text("LINE 通知渠道", exact=True).wait_for(timeout=30_000)
        body_text = page.locator("body").inner_text(timeout=30_000)
        report = validate_retirement_page(body_text)
        page.screenshot(path=output_dir / "platform-retirement.png", full_page=True)
        if console_errors:
            raise RuntimeError(
                f"Production retirement page emitted {len(console_errors)} console errors"
            )
        report.update(
            {
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "url": page.url,
                "console_error_count": 0,
            }
        )
        browser.close()

    (output_dir / "browser-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Production retirement observation verified in Chromium")


if __name__ == "__main__":
    main()
