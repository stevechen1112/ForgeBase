"""
In-process sliding-window rate limiter.

No external dependencies — uses a plain dict + threading.Lock.
Works correctly for single-worker deployments (Docker uvicorn default).

For multi-worker deployments move to Redis (slowapi + redis backend).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple

# (method, path) -> (max_requests, window_seconds)
RULES: Dict[Tuple[str, str], Tuple[int, int]] = {
    ("POST", "/api/v1/auth/login"):           (10, 60),   # 10 attempts / min
    ("POST", "/api/v1/auth/register"):         (5,  60),   #  5 attempts / min
    ("POST", "/api/v1/forms/contact"):         (20, 60),   # 20 / min
    ("POST", "/api/v1/forms/rfq"):             (20, 60),   # 20 / min
    ("POST", "/api/v1/tracking/events"):       (60, 60),   # 60 / min
    ("POST", "/api/v1/tracking/events/batch"): (20, 60),   # 20 / min
}


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


def check(method: str, path: str, client_ip: str) -> bool:
    """
    Returns True if the request is allowed, False if it should be rejected (429).
    Matched by exact (method, path) — no path parameters.
    """
    rule = RULES.get((method, path))
    if rule is None:
        return True
    limit, window = rule
    key = f"{client_ip}|{method}:{path}"
    return _store.is_allowed(key, limit, window)
