"""
Unit tests for app.core.rate_limit — sliding window rate limiter.

No database or network required.  Runs entirely in-process.
"""
import time

import pytest

from app.core.rate_limit import _SlidingWindowStore, check, RULES


# ── _SlidingWindowStore ──────────────────────────────────────────────────────

class TestSlidingWindowStore:
    def setup_method(self):
        self.store = _SlidingWindowStore()

    def test_allows_requests_within_limit(self):
        for _ in range(5):
            assert self.store.is_allowed("key1", limit=5, window=60) is True

    def test_blocks_request_exceeding_limit(self):
        for _ in range(5):
            self.store.is_allowed("key1", limit=5, window=60)
        # 6th request should be rejected
        assert self.store.is_allowed("key1", limit=5, window=60) is False

    def test_different_keys_are_independent(self):
        for _ in range(5):
            self.store.is_allowed("key_a", limit=5, window=60)
        # key_a is exhausted, key_b is fresh
        assert self.store.is_allowed("key_b", limit=5, window=60) is True

    def test_window_expiry_resets_counter(self):
        # Use a 1-second window
        for _ in range(3):
            self.store.is_allowed("key2", limit=3, window=1)
        assert self.store.is_allowed("key2", limit=3, window=1) is False

        # Simulate window expiry by advancing timestamps manually
        # We patch the internal list directly: set all timestamps to well in the past
        self.store._store["key2"] = [time.monotonic() - 2.0] * 3
        # Now the window has expired — request should be allowed
        assert self.store.is_allowed("key2", limit=3, window=1) is True

    def test_limit_of_one_allows_first_then_blocks(self):
        assert self.store.is_allowed("single", limit=1, window=60) is True
        assert self.store.is_allowed("single", limit=1, window=60) is False

    def test_cleanup_removes_stale_keys(self):
        self.store.is_allowed("stale_key", limit=10, window=1)
        # Age the entry beyond the 5-minute cleanup threshold
        self.store._store["stale_key"] = [time.monotonic() - 400]
        self.store.cleanup()
        assert "stale_key" not in self.store._store


# ── check() public API ───────────────────────────────────────────────────────

class TestCheck:
    def setup_method(self):
        # Patch the module-level store with a fresh one for isolation
        import app.core.rate_limit as rl
        self._orig_store = rl._store
        rl._store = _SlidingWindowStore()

    def teardown_method(self):
        import app.core.rate_limit as rl
        rl._store = self._orig_store

    def test_unrated_path_always_allowed(self):
        for _ in range(200):
            assert check("GET", "/api/v1/products", "1.2.3.4") is True

    def test_login_allows_up_to_limit(self):
        for _ in range(10):
            result = check("POST", "/api/v1/auth/login", "10.0.0.1")
            assert result is True

    def test_login_blocks_after_limit(self):
        for _ in range(10):
            check("POST", "/api/v1/auth/login", "10.0.0.2")
        assert check("POST", "/api/v1/auth/login", "10.0.0.2") is False

    def test_register_limit_is_five(self):
        for _ in range(5):
            assert check("POST", "/api/v1/auth/register", "10.0.0.3") is True
        assert check("POST", "/api/v1/auth/register", "10.0.0.3") is False

    def test_contact_form_limit_is_twenty(self):
        for _ in range(20):
            assert check("POST", "/api/v1/forms/contact", "10.0.0.4") is True
        assert check("POST", "/api/v1/forms/contact", "10.0.0.4") is False

    def test_rfq_form_limit_is_twenty(self):
        for _ in range(20):
            assert check("POST", "/api/v1/forms/rfq", "10.0.0.5") is True
        assert check("POST", "/api/v1/forms/rfq", "10.0.0.5") is False

    def test_different_ips_have_independent_budgets(self):
        # Exhaust IP A
        for _ in range(10):
            check("POST", "/api/v1/auth/login", "192.168.1.1")
        assert check("POST", "/api/v1/auth/login", "192.168.1.1") is False
        # IP B is unaffected
        assert check("POST", "/api/v1/auth/login", "192.168.1.2") is True

    def test_all_rate_limited_paths_are_covered(self):
        """Smoke test: every rule in RULES is exercised by check()."""
        for (method, path), (limit, _) in RULES.items():
            ip = f"99.0.{hash(path) % 256}.1"
            for _ in range(limit):
                check(method, path, ip)
            assert check(method, path, ip) is False, f"Expected block for {method} {path}"
