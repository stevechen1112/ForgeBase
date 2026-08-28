"""Emit a read-only, privacy-minimised platform data-quality report as JSON."""

from __future__ import annotations

import asyncio
import json

from app.db.session import AsyncSessionLocal
from app.services.platform_data_quality import build_platform_data_quality_report


async def main() -> None:
    async with AsyncSessionLocal() as session:
        report = await build_platform_data_quality_report(session)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
