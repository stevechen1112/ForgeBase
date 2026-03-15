"""
Shared pytest fixtures.

Unit tests that don't need a DB run with the raw app.
Integration tests (marked with @pytest.mark.integration) require a live
DATABASE_URL and are run in CI only (or locally when Docker is up).
"""
import os
import pytest

# Mark tests that require a running DB so they can be selectively skipped.
requires_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping DB integration tests",
)
