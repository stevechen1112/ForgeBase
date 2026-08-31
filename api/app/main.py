import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.api.internal import router as internal_router
from app.core import rate_limit
from app.core.config import settings
from app.services.google_ads import sync_high_intent_to_customer_match
from app.services.daily_summary import run_daily_summary
from app.services.scheduled_publishing import run_scheduled_publishing
from app.services.score_decay import run_daily_score_decay

logger = logging.getLogger("forgebase.api")

# Only start APScheduler in the primary worker to prevent duplicate job execution
# in multi-worker deployments. Set FORGEBASE_SCHEDULER_ENABLED=0 on non-primary workers.
_SCHEDULER_ENABLED = os.environ.get("FORGEBASE_SCHEDULER_ENABLED", "1") == "1"
_scheduler = AsyncIOScheduler(timezone="UTC")


async def _score_decay_job() -> None:
    """Wrapper so APScheduler can call the async decay function."""
    try:
        stats = await run_daily_score_decay()
        logger.info("Score decay complete: %s", stats)
    except Exception:
        logger.exception("Score decay job failed")


async def _daily_summary_job() -> None:
    """Send the rule-based sales operations summary each morning."""
    try:
        stats = await run_daily_summary()
        logger.info("Daily operations summary complete: %s", stats)
    except Exception:
        logger.exception("Daily operations summary job failed")


async def _google_ads_sync_job() -> None:
    """Daily Google Ads Customer Match sync job."""
    try:
        stats = await sync_high_intent_to_customer_match()
        logger.info("Google Ads Customer Match sync complete: %s", stats)
    except Exception:
        logger.exception("Google Ads sync job failed")


async def _scheduled_publishing_job() -> None:
    """Every-minute job: auto-publish products whose scheduled time has arrived."""
    try:
        stats = await run_scheduled_publishing()
        if stats["published"]:
            logger.info("Scheduled publishing: %d product(s) published", stats["published"])
    except Exception:
        logger.exception("Scheduled publishing job failed")


async def _sla_scan_job() -> None:
    """Every 15 min: first-response SLA reminders & escalations (T7)."""
    from app.services.sla import scan_sla_breaches
    try:
        stats = await scan_sla_breaches()
        if stats["reminded"] or stats["breached"]:
            logger.info("SLA scan: %s", stats)
    except Exception:
        logger.exception("SLA scan job failed")


async def _nurture_process_job() -> None:
    """Periodic: send due nurture sequence steps."""
    from app.api.v1.endpoints.nurture import process_all_due_enrollments
    try:
        stats = await process_all_due_enrollments()
        if stats.get("sent") or stats.get("completed"):
            logger.info("Nurture process: %s", stats)
    except Exception:
        logger.exception("Nurture process job failed")


async def _operational_outbox_job() -> None:
    from app.services.operational_outbox import process_operational_jobs
    try:
        stats = await process_operational_jobs()
        if stats["completed"] or stats["retried"] or stats["failed"]:
            logger.info("Operational outbox: %s", stats)
    except Exception:
        logger.exception("Operational outbox job failed")


async def _analytics_retention_job() -> None:
    from app.db.session import get_session_ctx
    from app.services.privacy_operations import run_scheduled_retention
    try:
        async with get_session_ctx() as db:
            result = await run_scheduled_retention(db)
        if any(result["processed"].values()):
            logger.info("Privacy retention cleanup: %s", result)
    except Exception:
        logger.exception("Analytics retention cleanup failed")


async def _ops_monitor_job() -> None:
    from app.services.ops_monitor import check_operational_health
    try:
        stats = await check_operational_health()
        if not stats["healthy"]:
            logger.error("Operational job health degraded: %s", stats)
    except Exception:
        logger.exception("Operational health monitor failed")


async def _knowledge_sync_job() -> None:
    from app.services.knowledge_sync import process_knowledge_sync_jobs
    try:
        stats = await process_knowledge_sync_jobs()
        if (
            stats["completed"]
            or stats["retried"]
            or stats["failed"]
            or stats["backfill_failed"]
        ):
            logger.info("Knowledge sync: %s", stats)
    except Exception:
        logger.exception("Knowledge sync job failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not _SCHEDULER_ENABLED:
        logger.info("APScheduler disabled on this worker (FORGEBASE_SCHEDULER_ENABLED=0)")
        yield
        return
    # startup — register scheduled jobs
    _scheduler.add_job(
        _score_decay_job,
        trigger="cron",
        hour=2,
        minute=0,
        id="daily_score_decay",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _daily_summary_job,
        trigger="cron",
        hour=0,
        minute=0,
        id="daily_operations_summary",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _google_ads_sync_job,
        trigger="cron",
        hour=3,
        minute=0,
        id="daily_google_ads_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _scheduled_publishing_job,
        trigger="interval",
        minutes=1,
        id="scheduled_publishing",
        replace_existing=True,
        misfire_grace_time=60,
    )
    # First-response SLA scan — every 15 min (T7)
    _scheduler.add_job(
        _sla_scan_job,
        trigger="interval",
        minutes=15,
        id="rfq_sla_scan",
        replace_existing=True,
        misfire_grace_time=300,
    )
    # Nurture: process due sequence steps — every hour
    _scheduler.add_job(
        _nurture_process_job,
        trigger="interval",
        minutes=60,
        id="nurture_process",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.add_job(
        _operational_outbox_job,
        trigger="interval",
        seconds=30,
        id="operational_outbox",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=30,
    )
    _scheduler.add_job(
        _analytics_retention_job,
        trigger="cron",
        hour=4,
        minute=15,
        id="analytics_retention",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _ops_monitor_job,
        trigger="interval",
        minutes=5,
        id="operational_health_monitor",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120,
    )
    _scheduler.add_job(
        _knowledge_sync_job,
        trigger="interval",
        minutes=1,
        id="knowledge_sync",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=30,
    )
    _scheduler.start()
    logger.info("APScheduler started — score decay 02:00 UTC, Google Ads sync 03:00 UTC, scheduled publishing every 1 min")
    yield
    # shutdown
    _scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")


app = FastAPI(
    title="ForgeBase API",
    description="外銷製造商官網成長系統 API",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def enforce_rate_limit(request: Request, call_next):
    # Use the LAST entry in X-Forwarded-For (set by our trusted nginx proxy)
    # to prevent client-side IP spoofing via a forged X-Forwarded-For header.
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        client_ip = xff.split(",")[-1].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    if not await rate_limit.check_shared(request.method, request.url.path, client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Too many requests", "status_code": 429},
            headers={"Retry-After": "60"},
        )
    return await call_next(request)


# ── Request logging middleware ───────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %d %.1fms [%s]",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Global exception handlers ────────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "detail": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )

app.include_router(api_router)
app.include_router(internal_router)

# Local asset uploads (dev / no R2)
from fastapi.staticfiles import StaticFiles

_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}


@app.get("/health/ready", tags=["system"])
@app.head("/health/ready", tags=["system"], include_in_schema=False)
async def readiness_check():
    """Deep readiness probe used by production deployment.

    Verifies the database connection, migration revision, writable upload
    storage, and the single in-process scheduler.
    """
    checks: dict[str, str] = {}

    try:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.exec(text("SELECT 1"))
            revision = (
                await session.exec(text("SELECT version_num FROM alembic_version"))
            ).scalar_one_or_none()
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        expected_revision = ScriptDirectory.from_config(alembic_config).get_current_head()
        checks["database"] = "ok"
        checks["migration"] = "ok" if revision == expected_revision else "error"
    except Exception:
        logger.exception("Readiness database check failed")
        checks["database"] = "error"
        checks["migration"] = "error"

    try:
        upload_dir = Path(__file__).resolve().parent.parent / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        probe = upload_dir / ".readiness-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks["storage"] = "ok"
    except Exception:
        logger.exception("Readiness storage check failed")
        checks["storage"] = "error"

    checks["scheduler"] = (
        "ok" if _SCHEDULER_ENABLED and _scheduler.running else "error"
    )
    ready = all(
        checks.get(name) not in {None, "error", "missing"}
        for name in ("database", "migration", "storage", "scheduler")
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if ready else "degraded", "checks": checks},
    )


@app.get("/health/external-test", tags=["system"])
async def external_test_readiness_check():
    """Separate launch gate; does not make an otherwise healthy API restart-loop."""
    from app.services.external_test_readiness import external_test_readiness

    result = external_test_readiness()
    return JSONResponse(
        status_code=status.HTTP_200_OK if result["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=result,
    )
