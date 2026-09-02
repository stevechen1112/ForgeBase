"""
Shared pytest fixtures.

Unit tests that don't need a DB run with the raw app.
Integration tests require a live DATABASE_URL and are run in CI
or locally when PostgreSQL is available.
"""

import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Service-layer helpers use the module-level DB session factory instead of the
# FastAPI dependency override. Tests use function-scoped event loops, so that
# shared factory must not retain asyncpg connections from a previous loop.
os.environ.setdefault("DATABASE_NULL_POOL", "true")

# Mark tests that require a running DB so they can be selectively skipped.
requires_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set -- skipping DB integration tests",
)


@pytest.fixture(autouse=True)
def _reset_rate_limit_store():
    """Give every test a fresh rate-limit budget.

    The limiter is an in-process module-level store keyed by client IP;
    ASGI test clients all share one IP, so without a reset the 20/min
    POST /forms/rfq budget is exhausted midway through the full suite
    (observed as flaky 429s in test_rfq_speed_features).
    """
    from app.core.rate_limit import _store

    _store._store.clear()
    yield


@pytest.fixture(scope="session", autouse=True)
def _apply_db_migrations():
    """Bring the test database to Alembic head before any DB test runs.

    Schema changes must come from migrations (app/db/migrations/versions/);
    test-time manual ALTER TABLE patches were removed (2026-08-03, T1).
    """
    if not os.getenv("DATABASE_URL"):
        yield
        return
    import subprocess
    import sys

    api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=api_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "alembic upgrade head failed; test DB schema is not at head.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    yield


def _make_engine():
    """Create a fresh NullPool engine for fixture use.

    NullPool makes no connection reuse; every session gets a brand new
    asyncpg connection that closes immediately on release.  This prevents
    cross-event-loop contamination when pytest-asyncio runs each test in
    its own function-scoped event loop.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.pool import NullPool
    from sqlmodel.ext.asyncio.session import AsyncSession
    from app.core.config import settings

    eng = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    return eng, factory


@pytest_asyncio.fixture(autouse=True)
async def _reset_shared_rate_limit_store():
    """Reset the database-backed limiter using the canonical async driver.

    CI and production dependencies intentionally do not install a second,
    synchronous PostgreSQL driver. Keeping this cleanup async prevents hidden
    local-only behavior and makes the complete suite deterministic.
    """
    if not os.getenv("DATABASE_URL"):
        yield
        return

    from sqlalchemy import text

    eng, factory = _make_engine()
    try:
        async with factory() as session:
            await session.exec(text("DELETE FROM rate_limit_hits"))
            await session.commit()
    finally:
        await eng.dispose()
    yield


@pytest_asyncio.fixture
async def http_client():
    """ASGI test client for the FastAPI app (no real HTTP).

    Overrides get_session with a NullPool-based session so every request
    within the test's function-scoped event loop uses a fresh asyncpg
    connection.  This prevents the module-level pool from ever holding
    connections bound to a different (previous test's) event loop.

    Schema is brought to head once per session by _apply_db_migrations.
    """
    from app.main import app
    from app.db.session import get_session

    eng, factory = _make_engine()

    async def _override_get_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_session, None)
    await eng.dispose()


@pytest_asyncio.fixture
async def two_tenants():
    """Create two isolated tenants; delete them (and all owned rows) after the test.

    Uses a NullPool engine (no cross-loop connection reuse) so that each
    function-scoped event loop starts from a clean state.
    """
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    from app.models.tenant import Tenant

    eng, factory = _make_engine()
    tag = uuid.uuid4().hex[:8]
    tenant_a = Tenant(
        name="Tenant Alpha",
        slug=f"alpha-{tag}",
    )
    tenant_b = Tenant(
        name="Tenant Beta",
        slug=f"beta-{tag}",
    )

    async with factory() as session:
        session.add(tenant_a)
        session.add(tenant_b)
        await session.commit()
        await session.refresh(tenant_a)
        await session.refresh(tenant_b)

    yield tenant_a, tenant_b

    # Teardown: delete all tenant-owned rows in FK-safe order
    from sqlalchemy import text

    async with factory() as session:
        for tid in (str(tenant_a.id), str(tenant_b.id)):
            for table in (
                "privacy_operations",
                "sales_handoff_events",
                "sales_handoffs",
                "inbound_replies",
                "inbound_reply_policies",
                "outreach_message_reviews",
                "outreach_messages",
                "journey_snapshots",
                "outreach_draft_policies",
                "contact_candidate_reviews",
                "contact_candidates",
                "contact_persona_policies",
                "provider_usage",
                "identification_reviews",
                "company_identifications",
                "network_observations",
                "growth_automation_policies",
                "retirement_usage_events",
                "operational_jobs",
                "consent_records",
                "site_builds",
                "platform_audit_logs",
                "idempotency_keys",
                "reply_templates",
                "notification_preferences",
                "notification_log",
                "tracking_events",
                "rfq_notes",
                "rfq_events",
                "rfq_requests",
                "rfq_drafts",
                "contacts",
                "knowledge_chunks",
                "knowledge_sync_jobs",
                "knowledge_sources",
                "content_assets",
                "chat_sessions",
                "tracking_sessions",
                "visitors",
                "pages",
                "redirects",
                "ctas",
                "faq_items",
                "comparison_topics",
                "certifications",
                "capabilities",
                "applications",
                "products",
                "product_categories",
                "site_profiles",
                "users",
            ):
                await session.exec(
                    text(f"DELETE FROM {table} WHERE tenant_id = :tid"),
                    params={"tid": tid},
                )
            await session.exec(
                text("DELETE FROM tenants WHERE id = :tid"), params={"tid": tid}
            )
        await session.commit()

    await eng.dispose()


@pytest_asyncio.fixture
async def admin_token_for_tenant(two_tenants):
    """Factory: call with a tenant_id to get a JWT for a fresh admin user.

    Usage::

        token = await admin_token_for_tenant(tenant_a.id)
    """
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    from app.models.user import User
    from app.core.security import get_password_hash, create_access_token

    eng, factory = _make_engine()

    async def _make(tenant_id: uuid.UUID) -> str:
        async with factory() as session:
            user = User(
                email=f"admin-{uuid.uuid4().hex[:8]}@test.invalid",
                hashed_password=get_password_hash("testpass"),
                full_name="Test Admin",
                role="admin",
                tenant_id=tenant_id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return create_access_token(str(user.id))

    yield _make

    await eng.dispose()
    # Users are cleaned up by the two_tenants teardown (DELETE WHERE tenant_id)
