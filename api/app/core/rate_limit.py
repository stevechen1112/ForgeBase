"""
Sliding-window rate limiter.

Production uses a shared PostgreSQL hit table so extra API workers
cannot multiply the effective budget. Tests and a database outage fall
back to the in-process store.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Tuple

from sqlalchemy import delete, func
from sqlmodel import select

logger = logging.getLogger(__name__)

# (method, path) -> (max_requests, window_seconds)
RULES: Dict[Tuple[str, str], Tuple[int, int]] = {
    ("POST", "/api/v1/auth/login"):           (10, 60),   # 10 attempts / min
    ("POST", "/api/v1/auth/register"):         (5,  60),   #  5 attempts / min
    ("POST", "/api/v1/forms/contact"):         (20, 60),   # 20 / min
    ("POST", "/api/v1/forms/rfq"):             (20, 60),   # signed challenge + 20 / min / IP
    ("POST", "/api/v1/forms/adoption"):         (5, 60),   # managed-delivery applications
    ("POST", "/api/v1/tracking/events"):       (60, 60),   # 60 / min
    ("POST", "/api/v1/tracking/events/batch"): (20, 60),   # 20 / min
    ("POST", "/api/v1/chat/sessions"):                     (10, 60),
    ("POST", "/api/v1/chat/sessions/{id}/messages"):       (20, 60),
    ("POST", "/api/v1/chat/sessions/{id}/handoff"):         (5, 60),
}

_CHAT_PATH = re.compile(
    r"^/api/v1/chat/sessions/[0-9a-fA-F-]+/(?P<action>messages|handoff)$"
)


class _SlidingWindowStore:
    """Thread-safe in-process sliding window counter."""

    def __init__(self) -> None:
        self._store: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        cutoff = now - window
        with self._lock:
            ts = self._store[key]
            # Evict expired timestamps
            ts[:] = [t for t in ts if t > cutoff]
            if len(ts) >= limit:
                return False
            ts.append(now)
            return True

    def cleanup(self) -> None:
        """Remove empty buckets (optional, call periodically to prevent memory growth)."""
        now = time.monotonic()
        with self._lock:
            dead = [k for k, v in self._store.items() if not v or v[-1] < now - 300]
            for k in dead:
                del self._store[k]


_store = _SlidingWindowStore()


def bucket_key(method: str, path: str, client_ip: str) -> tuple[str, int, int] | None:
    match = _CHAT_PATH.fullmatch(path)
    normalized_path = f"/api/v1/chat/sessions/{{id}}/{match.group('action')}" if match else path
    rule = RULES.get((method, normalized_path))
    if rule is None:
        return None
    limit, window = rule
    return f"{client_ip}|{method}:{normalized_path}", limit, window


def check(method: str, path: str, client_ip: str) -> bool:
    """
    Returns True if the request is allowed, False if it should be rejected (429).
    Matched by exact (method, path) — no path parameters.
    """
    matched = bucket_key(method, path, client_ip)
    if matched is None:
        return True
    key, limit, window = matched
    return _store.is_allowed(key, limit, window)


async def check_shared(method: str, path: str, client_ip: str) -> bool:
    """Shared limiter used by the HTTP middleware. Falls back in-process."""
    matched = bucket_key(method, path, client_ip)
    if matched is None:
        return True
    key, limit, window = matched
    try:
        from app.core.datetime import utcnow_naive
        from app.db.session import get_session_ctx
        from app.models.knowledge import RateLimitHit

        async with get_session_ctx() as session:
            now = utcnow_naive()
            cutoff = now - timedelta(seconds=window)
            await session.exec(
                delete(RateLimitHit).where(
                    RateLimitHit.bucket_key == key,
                    RateLimitHit.created_at < cutoff,
                )
            )
            session.add(RateLimitHit(bucket_key=key, created_at=now))
            await session.flush()
            count = (
                await session.exec(
                    select(func.count(RateLimitHit.id)).where(
                        RateLimitHit.bucket_key == key,
                        RateLimitHit.created_at >= cutoff,
                    )
                )
            ).one()
            await session.commit()
            return int(count or 0) <= limit
    except Exception:
        logger.warning("shared rate limiter unavailable; using in-process store")
        return _store.is_allowed(key, limit, window)


_workers = os.environ.get("WEB_CONCURRENCY", "1")
if _workers != "1":
    logger.info("Shared database rate limiter is the primary path with %s workers.", _workers)
