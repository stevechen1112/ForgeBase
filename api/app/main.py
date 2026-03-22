import logging
import time
import uuid
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.api.v1.router import api_router
from app.services.score_decay import run_daily_score_decay
from app.services.google_ads import sync_high_intent_to_customer_match
from app.services.scheduled_publishing import run_scheduled_publishing

logger = logging.getLogger("forgebase.api")

_scheduler = AsyncIOScheduler(timezone="UTC")


async def _score_decay_job() -> None:
    """Wrapper so APScheduler can call the async decay function."""
    try:
        stats = await run_daily_score_decay()
        logger.info("Score decay complete: %s", stats)
    except Exception:
        logger.exception("Score decay job failed")


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


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}
