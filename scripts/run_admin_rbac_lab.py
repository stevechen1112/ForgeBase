#!/usr/bin/env python3
"""Run an isolated browser and API RBAC acceptance lab.

The runner starts a test-only API and Admin dev server, creates one temporary
tenant with every supported tenant role plus a platform superuser, exercises
the real login UI and route guards in Chromium, checks the matching API
boundaries, emits JSON/JUnit evidence, then removes the temporary identities.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
ADMIN_DIR = ROOT / "admin"
sys.path.insert(0, str(API_DIR))


@dataclass
class CheckResult:
    name: str
    status: str
    duration_ms: int
    detail: str = ""
    screenshot: str | None = None


class LabFailure(AssertionError):
    pass


def _database_name(url: str) -> str:
    normalized = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return urlsplit(normalized).path.lstrip("/")


def _assert_safe_environment() -> str:
    if os.getenv("APP_ENV", "").strip().lower() != "test":
        raise SystemExit("Refusing to run: APP_ENV must be exactly 'test'.")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("Refusing to run: DATABASE_URL is required.")
    database = _database_name(database_url).lower()
    if not database or not any(
        marker in database for marker in ("test", "lab", "batch", "ci")
    ):
        raise SystemExit(
            "Refusing to run: database name must contain test, lab, batch, or ci."
        )
    return database_url


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _wait_http(url: str, process: subprocess.Popen, timeout: int = 120) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LabFailure(f"Service exited before becoming ready: {url}")
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise LabFailure(f"Timed out waiting for {url}: {last_error}")


def _api_json(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, object | None]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            decoded = json.loads(payload) if payload else None
        except json.JSONDecodeError:
            decoded = None
        return exc.code, decoded


def _assert_status(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise LabFailure(f"{label}: expected HTTP {expected}, got {actual}")


async def _seed_lab(database_url: str) -> dict:
    from app.core.security import create_access_token, get_password_hash
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.services.capability_access import FEATURE_CATALOG
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlmodel.ext.asyncio.session import AsyncSession

    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    tag = uuid.uuid4().hex[:10]
    password = f"RbacLab-{secrets.token_urlsafe(18)}"
    configurable = {
        key: True
        for key, meta in FEATURE_CATALOG.items()
        if meta.get("configurable", True)
    }
    configurable["outcomes_dashboard"] = False
    tenant = Tenant(
        name="ForgeBase RBAC Lab",
        slug=f"rbac-lab-{tag}",
        feature_overrides=configurable,
    )
    accounts: dict[str, dict[str, str]] = {}
    tokens: dict[str, str] = {}
    user_ids: list[uuid.UUID] = []
    async with factory() as db:
        db.add(tenant)
        await db.flush()
        for role in ("owner", "admin", "marketing_manager", "sales"):
            user = User(
                tenant_id=tenant.id,
                email=f"rbac-{role.replace('_', '-')}-{tag}@example.com",
                hashed_password=get_password_hash(password),
                full_name=f"RBAC {role}",
                role=role,
            )
            db.add(user)
            user_ids.append(user.id)
            accounts[role] = {"email": user.email, "password": password}
            tokens[role] = create_access_token(str(user.id))
        platform = User(
            email=f"rbac-platform-{tag}@example.com",
            hashed_password=get_password_hash(password),
            full_name="RBAC Platform",
            role="admin",
            is_superuser=True,
        )
        db.add(platform)
        user_ids.append(platform.id)
        accounts["platform"] = {"email": platform.email, "password": password}
        tokens["platform"] = create_access_token(str(platform.id))
        await db.commit()
    await engine.dispose()
    return {
        "tenant_id": tenant.id,
        "user_ids": user_ids,
        "accounts": accounts,
        "tokens": tokens,
    }


async def _cleanup_lab(database_url: str, seed: dict) -> None:
    from app.models.knowledge import RateLimitHit
    from app.models.site_profile import SiteProfile
    from app.models.tenant import Tenant
    from app.models.user import User
    from sqlalchemy import delete, func
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        await db.exec(
            delete(SiteProfile).where(SiteProfile.tenant_id == seed["tenant_id"])
        )
        await db.exec(delete(User).where(User.id.in_(seed["user_ids"])))
        await db.exec(delete(Tenant).where(Tenant.id == seed["tenant_id"]))
        await db.exec(
            delete(RateLimitHit).where(
                RateLimitHit.bucket_key == "127.0.0.1|POST:/api/v1/auth/login"
            )
        )
        # Commit deletion before verification so even an unexpected residue
        # failure cannot roll back the cleanup that did succeed.
        await db.commit()
        residue = {
            "site_profiles": (
                await db.exec(
                    select(func.count(SiteProfile.id)).where(
                        SiteProfile.tenant_id == seed["tenant_id"]
                    )
                )
            ).one(),
            "users": (
                await db.exec(
                    select(func.count(User.id)).where(User.id.in_(seed["user_ids"]))
                )
            ).one(),
            "tenants": (
                await db.exec(
                    select(func.count(Tenant.id)).where(
                        Tenant.id == seed["tenant_id"]
                    )
                )
            ).one(),
        }
        remaining = {key: int(value or 0) for key, value in residue.items() if value}
        if remaining:
            raise LabFailure(f"RBAC lab cleanup left database residue: {remaining}")
    await engine.dispose()


async def _cleanup_stale_labs(database_url: str) -> None:
    """Remove only identities created by interrupted runs of this lab."""
    from app.models.knowledge import RateLimitHit
    from app.models.site_profile import SiteProfile
    from app.models.tenant import Tenant
    from app.models.user import User
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        tenants = (
            await db.exec(select(Tenant.id).where(Tenant.slug.like("rbac-lab-%")))
        ).all()
        await db.exec(delete(User).where(User.email.like("rbac-%@example.com")))
        if tenants:
            await db.exec(delete(SiteProfile).where(SiteProfile.tenant_id.in_(tenants)))
            await db.exec(delete(User).where(User.tenant_id.in_(tenants)))
            await db.exec(delete(Tenant).where(Tenant.id.in_(tenants)))
        # The lab owns this localhost login bucket inside its mandatory isolated
        # test database. Clearing it makes rapid local/CI reruns deterministic.
        await db.exec(
            delete(RateLimitHit).where(
                RateLimitHit.bucket_key == "127.0.0.1|POST:/api/v1/auth/login"
            )
        )
        await db.commit()
    await engine.dispose()


def _write_junit(results: list[CheckResult], path: Path) -> None:
    failures = sum(result.status == "failed" for result in results)
    suite = ElementTree.Element(
        "testsuite",
        {
            "name": "admin-rbac-browser-lab",
            "tests": str(len(results)),
            "failures": str(failures),
            "errors": "0",
            "time": f"{sum(row.duration_ms for row in results) / 1000:.3f}",
        },
    )
    for result in results:
        case = ElementTree.SubElement(
            suite,
            "testcase",
            {
                "classname": "admin.rbac",
                "name": result.name,
                "time": f"{result.duration_ms / 1000:.3f}",
            },
        )
        if result.status == "failed":
            failure = ElementTree.SubElement(
                case, "failure", {"message": result.detail[:500]}
            )
            failure.text = result.detail
    ElementTree.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def _run_browser_and_api_matrix(
    *,
    admin_base: str,
    api_base: str,
    accounts: dict[str, dict[str, str]],
    tokens: dict[str, str],
    artifacts: Path,
) -> tuple[list[CheckResult], list[str]]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required. Install scripts/requirements-ui-scan.txt "
            "and run 'playwright install chromium'."
        ) from exc

    results: list[CheckResult] = []
    external_origins: set[str] = set()

    def record(name: str, action, page=None) -> None:
        started = time.monotonic()
        screenshot: str | None = None
        try:
            action()
            results.append(
                CheckResult(
                    name=name,
                    status="passed",
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            )
        except Exception as exc:  # noqa: BLE001 - evidence must include all cases
            if page is not None:
                screenshot_path = artifacts / f"failure-{len(results) + 1:02d}.png"
                try:
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    screenshot = str(screenshot_path)
                except (OSError, PlaywrightError):
                    screenshot = None
            results.append(
                CheckResult(
                    name=name,
                    status="failed",
                    duration_ms=int((time.monotonic() - started) * 1000),
                    detail="".join(
                        traceback.format_exception_only(type(exc), exc)
                    ).strip(),
                    screenshot=screenshot,
                )
            )

    def body_text(page) -> str:
        page.locator("body").wait_for(state="visible", timeout=30_000)
        return page.locator("body").inner_text(timeout=30_000)

    def login(page, role: str) -> None:
        account = accounts[role]
        page.goto(f"{admin_base}/login", wait_until="domcontentloaded")
        # A fast cache hit can expose server-rendered controlled inputs before
        # React hydration; filling then may lose the first field value.
        page.wait_for_timeout(300)
        page.locator("#login-email").fill(account["email"])
        page.locator("#login-password").fill(account["password"])
        page.get_by_role("button", name="登入管理後台").click()
        expected = (
            f"{admin_base}/platform/overview"
            if role == "platform"
            else f"{admin_base}/dashboard"
        )
        page.wait_for_url(expected, timeout=60_000)
        page.wait_for_timeout(700)

    def route(page, path: str, expectation: str) -> None:
        page.goto(f"{admin_base}{path}", wait_until="domcontentloaded")
        page.wait_for_timeout(700)
        text = body_text(page)
        if expectation == "allowed":
            if "您沒有權限使用這項功能" in text:
                raise LabFailure(f"{path} unexpectedly rendered RBAC 403")
            if "此租戶尚未開通這項功能" in text:
                raise LabFailure(f"{path} unexpectedly rendered capability lock")
            if page.url.endswith("/login"):
                raise LabFailure(f"{path} unexpectedly redirected to login")
        elif expectation == "denied":
            if "您沒有權限使用這項功能" not in text:
                raise LabFailure(f"{path} did not render the RBAC 403 state")
        elif expectation == "locked":
            if "此租戶尚未開通這項功能" not in text:
                raise LabFailure(f"{path} did not render the capability lock state")
        else:
            raise LabFailure(f"Unknown route expectation: {expectation}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        def new_context(**kwargs):
            context = browser.new_context(**kwargs)

            def capture_request(request) -> None:
                parsed = urlsplit(request.url)
                if parsed.scheme in {"http", "https"} and parsed.hostname not in {
                    "127.0.0.1",
                    "localhost",
                    "::1",
                }:
                    external_origins.add(f"{parsed.scheme}://{parsed.netloc}")

            context.on("request", capture_request)
            return context

        unauthenticated = new_context(locale="zh-TW")
        unauth_page = unauthenticated.new_page()

        def unauthenticated_redirect() -> None:
            unauth_page.goto(f"{admin_base}/dashboard", wait_until="domcontentloaded")
            unauth_page.wait_for_url(f"{admin_base}/login", timeout=30_000)

        record(
            "ui.unauthenticated.redirects_to_login",
            unauthenticated_redirect,
            unauth_page,
        )
        unauthenticated.close()

        route_matrix = {
            "owner": {
                "/dashboard": "allowed",
                "/dashboard/content": "allowed",
                "/dashboard/growth": "allowed",
                "/dashboard/pages": "allowed",
                "/dashboard/users": "allowed",
                "/dashboard/settings/site-profile": "allowed",
                "/dashboard/rfqs": "allowed",
                "/dashboard/visitors": "allowed",
                "/dashboard/outcomes": "locked",
            },
            "admin": {
                "/dashboard": "allowed",
                "/dashboard/content": "allowed",
                "/dashboard/growth": "allowed",
                "/dashboard/pages": "allowed",
                "/dashboard/users": "allowed",
                "/dashboard/settings/site-profile": "allowed",
                "/dashboard/rfqs": "allowed",
                "/dashboard/visitors": "allowed",
            },
            "marketing_manager": {
                "/dashboard": "allowed",
                "/dashboard/content": "allowed",
                "/dashboard/growth": "allowed",
                "/dashboard/content/locales": "allowed",
                "/dashboard/pages": "denied",
                "/dashboard/users": "denied",
                "/dashboard/settings/site-profile": "denied",
                "/dashboard/rfqs": "allowed",
                "/dashboard/visitors": "allowed",
            },
            "sales": {
                "/dashboard": "allowed",
                "/dashboard/rfqs": "allowed",
                "/dashboard/replies": "allowed",
                "/dashboard/visitors": "allowed",
                # The content hub is intentionally read-only for Sales and
                # exposes only product lookup; editor tools remain hidden.
                "/dashboard/content": "allowed",
                "/dashboard/growth": "denied",
                "/dashboard/content/locales": "denied",
                "/dashboard/users": "denied",
                "/dashboard/settings/site-profile": "denied",
            },
        }
        role_labels = {
            "owner": "帳號擁有者",
            "admin": "管理員",
            "marketing_manager": "行銷經理",
            "sales": "業務人員",
        }
        for role, paths in route_matrix.items():
            context = new_context(
                locale="zh-TW", viewport={"width": 1440, "height": 960}
            )
            page = context.new_page()
            console_errors: list[str] = []
            page.on(
                "console",
                lambda message, errors=console_errors: (
                    errors.append(message.text) if message.type == "error" else None
                ),
            )
            record(
                f"ui.{role}.login_and_role_label",
                lambda page=page, role=role: (
                    login(page, role),
                    page.get_by_text(role_labels[role], exact=True).wait_for(
                        state="visible", timeout=30_000
                    ),
                ),
                page,
            )
            for path, expectation in (
                (path, expectation)
                for path, expectation in paths.items()
                if expectation != "denied"
            ):
                record(
                    f"ui.{role}.{expectation}.{path}",
                    lambda page=page, path=path, expectation=expectation: route(
                        page, path, expectation
                    ),
                    page,
                )

            def no_console_errors(errors=console_errors) -> None:
                if errors:
                    raise LabFailure("; ".join(errors[:5]))

            record(f"ui.{role}.no_console_errors", no_console_errors, page)
            console_errors.clear()
            # Direct denied-route probes can legitimately produce browser
            # resource 403 messages while the UI renders its explicit guard.
            for path, expectation in (
                (path, expectation)
                for path, expectation in paths.items()
                if expectation == "denied"
            ):
                record(
                    f"ui.{role}.{expectation}.{path}",
                    lambda page=page, path=path, expectation=expectation: route(
                        page, path, expectation
                    ),
                    page,
                )
            context.close()

        platform_context = new_context(locale="zh-TW")
        platform_page = platform_context.new_page()

        def platform_login() -> None:
            login(platform_page, "platform")
            text = body_text(platform_page)
            if "403" in text or platform_page.url.endswith("/platform/login"):
                raise LabFailure("Platform superuser did not reach platform overview")

        record("ui.platform.login_separation", platform_login, platform_page)
        platform_context.close()

        for role, path in (("owner", "/dashboard"), ("sales", "/dashboard/rfqs")):
            context = new_context(
                locale="zh-TW", viewport={"width": 390, "height": 844}
            )
            page = context.new_page()

            def mobile_check(page=page, role=role, path=path) -> None:
                login(page, role)
                route(page, path, "allowed")
                overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth - window.innerWidth"
                )
                if overflow > 1:
                    raise LabFailure(f"Horizontal overflow is {overflow}px")

            record(f"ui.{role}.mobile_no_horizontal_overflow", mobile_check, page)
            context.close()

        def no_external_network_calls() -> None:
            if external_origins:
                raise LabFailure(
                    "Unexpected external browser origins: "
                    + ", ".join(sorted(external_origins))
                )

        record("ui.external_network_calls.zero", no_external_network_calls)
        browser.close()

    for role, expected in {
        "owner": 200,
        "admin": 200,
        "marketing_manager": 403,
        "sales": 403,
    }.items():
        record(
            f"api.{role}.team_boundary",
            lambda role=role, expected=expected: _assert_status(
                _api_json(f"{api_base}/auth/team", token=tokens[role])[0],
                expected,
                f"api.{role}.team_boundary",
            ),
        )

    for role, expected in {
        "owner": 200,
        "admin": 200,
        "marketing_manager": 200,
        "sales": 403,
    }.items():
        record(
            f"api.{role}.locale_editor_boundary",
            lambda role=role, expected=expected: _assert_status(
                _api_json(f"{api_base}/content/locale-settings", token=tokens[role])[0],
                expected,
                f"api.{role}.locale_editor_boundary",
            ),
        )

    for role in ("owner", "admin", "marketing_manager", "sales"):
        record(
            f"api.{role}.reply_viewer_boundary",
            lambda role=role: _assert_status(
                _api_json(f"{api_base}/tracking/replies", token=tokens[role])[0],
                200,
                f"api.{role}.reply_viewer_boundary",
            ),
        )
        record(
            f"api.{role}.platform_boundary",
            lambda role=role: _assert_status(
                _api_json(f"{api_base}/admin/dashboard", token=tokens[role])[0],
                403,
                f"api.{role}.platform_boundary",
            ),
        )

    record(
        "api.platform.superuser_boundary",
        lambda: _assert_status(
            _api_json(f"{api_base}/admin/dashboard", token=tokens["platform"])[0],
            200,
            "api.platform.superuser_boundary",
        ),
    )
    return results, sorted(external_origins)


def _terminate(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if os.name == "nt":
        if process.poll() is not None:
            return
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated ForgeBase Admin browser/RBAC lab."
    )
    parser.add_argument("--api-port", type=int, default=18000)
    parser.add_argument("--admin-port", type=int, default=13001)
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/admin-rbac-lab",
        help="Directory for logs, JSON, JUnit and failure screenshots.",
    )
    args = parser.parse_args()
    database_url = _assert_safe_environment()
    host = "127.0.0.1"
    for label, port in (("API", args.api_port), ("Admin", args.admin_port)):
        if not _port_is_available(host, port):
            raise SystemExit(f"Refusing to run: {label} port {port} is already in use.")

    artifacts = Path(args.artifacts_dir).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "admin-rbac-lab.json"
    junit_path = artifacts / "admin-rbac-lab.junit.xml"
    for stale_report in (report_path, junit_path):
        stale_report.unlink(missing_ok=True)
    for stale_screenshot in artifacts.glob("failure-*.png"):
        stale_screenshot.unlink()
    api_log_path = artifacts / "api.log"
    admin_log_path = artifacts / "admin.log"
    api_process: subprocess.Popen | None = None
    admin_process: subprocess.Popen | None = None
    seed: dict | None = None
    results: list[CheckResult] = []
    external_origins: list[str] = []
    cleanup_error = ""

    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if migration.returncode:
        print(migration.stdout)
        print(migration.stderr, file=sys.stderr)
        raise SystemExit("Alembic migration failed before RBAC lab startup.")

    api_env = os.environ.copy()
    api_env.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": database_url,
            "DATABASE_NULL_POOL": "true",
            "ALLOWED_ORIGINS": f"http://{host}:{args.admin_port}",
            "ADMIN_URL": f"http://{host}:{args.admin_port}",
        }
    )
    admin_env = os.environ.copy()
    admin_env.update(
        {
            "NEXT_TELEMETRY_DISABLED": "1",
            "NEXT_PUBLIC_API_URL": f"http://{host}:{args.api_port}/api/v1",
            "NEXT_PUBLIC_AGENTOS_URL": f"http://{host}:{args.api_port}",
        }
    )
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm is required to start the Admin acceptance server.")

    try:
        asyncio.run(_cleanup_stale_labs(database_url))
        seed = asyncio.run(_seed_lab(database_url))
        with (
            api_log_path.open("w", encoding="utf-8") as api_log,
            admin_log_path.open("w", encoding="utf-8") as admin_log,
        ):
            api_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    host,
                    "--port",
                    str(args.api_port),
                ],
                cwd=API_DIR,
                env=api_env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=os.name != "nt",
            )
            admin_process = subprocess.Popen(
                [
                    npm,
                    "exec",
                    "next",
                    "--",
                    "dev",
                    "--hostname",
                    host,
                    "--port",
                    str(args.admin_port),
                ],
                cwd=ADMIN_DIR,
                env=admin_env,
                stdout=admin_log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=os.name != "nt",
            )
            _wait_http(f"http://{host}:{args.api_port}/health", api_process, 90)
            _wait_http(
                f"http://{host}:{args.admin_port}/backend/login",
                admin_process,
                180,
            )
            results, external_origins = _run_browser_and_api_matrix(
                admin_base=f"http://{host}:{args.admin_port}/backend",
                api_base=f"http://{host}:{args.api_port}/api/v1",
                accounts=seed["accounts"],
                tokens=seed["tokens"],
                artifacts=artifacts,
            )
    except Exception as exc:  # noqa: BLE001 - always emit lab evidence
        results.append(
            CheckResult(
                name="lab.infrastructure",
                status="failed",
                duration_ms=0,
                detail="".join(traceback.format_exception_only(type(exc), exc)).strip(),
            )
        )
    finally:
        _terminate(admin_process)
        _terminate(api_process)
        if seed is not None:
            try:
                asyncio.run(_cleanup_lab(database_url, seed))
            except Exception as exc:  # noqa: BLE001
                cleanup_error = "".join(
                    traceback.format_exception_only(type(exc), exc)
                ).strip()
                results.append(
                    CheckResult(
                        name="lab.cleanup",
                        status="failed",
                        duration_ms=0,
                        detail=cleanup_error,
                    )
                )

    failures = [result for result in results if result.status == "failed"]
    report = {
        "schema_version": 1,
        "lab": "admin-rbac-browser-lab",
        "status": "failed" if failures else "passed",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "supported_tenant_roles": [
            "owner",
            "admin",
            "marketing_manager",
            "sales",
        ],
        "synthetic_viewer_role_created": False,
        "external_network_calls": len(external_origins),
        "external_network_origins": external_origins,
        "cleanup": "failed" if cleanup_error else "passed",
        "summary": {
            "total": len(results),
            "passed": len(results) - len(failures),
            "failed": len(failures),
        },
        "results": [asdict(result) for result in results],
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_junit(results, junit_path)
    print(
        f"Admin RBAC lab: {report['summary']['passed']} passed, "
        f"{report['summary']['failed']} failed"
    )
    print(f"Artifacts: {artifacts}")
    for failure in failures:
        print(f"FAILED {failure.name}: {failure.detail}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
