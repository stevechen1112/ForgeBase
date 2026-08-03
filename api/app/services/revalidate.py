"""
前台快取 revalidate（CF→FB Publish Contract §8）

發佈／更新／meta 修復／下架後，以 fire-and-forget 方式呼叫 web 前台的
on-demand revalidate API。失敗僅記 log，不阻塞內容寫入流程。
"""
import logging
from typing import Iterable

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(5.0)


def page_paths(slug: str, locale: str = "en") -> list[str]:
    """依契約 §2 推導公開路徑：en 無前綴，其他語系帶 /{locale}。"""
    blog_path = f"/blog/{slug}"
    paths = [blog_path, "/blog"]
    if locale and locale != "en":
        paths.append(f"/{locale}{blog_path}")
        paths.append(f"/{locale}/blog")
    return paths


async def revalidate_paths(paths: Iterable[str]) -> bool:
    """呼叫 web 端 revalidate；未設定 URL 時靜默略過。回傳是否成功送出。"""
    if not settings.WEB_REVALIDATE_URL:
        return False
    payload = {"paths": sorted(set(paths))}
    headers = {"x-revalidate-secret": settings.WEB_REVALIDATE_SECRET}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(settings.WEB_REVALIDATE_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.warning("revalidate failed: %s %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as exc:  # noqa: BLE001 — revalidate 不得中斷主流程
        logger.warning("revalidate error: %s", exc)
        return False


async def revalidate_page(slug: str, locale: str = "en", include_sitemap: bool = False) -> bool:
    paths = page_paths(slug, locale)
    if include_sitemap:
        paths.append("/sitemap.xml")
    return await revalidate_paths(paths)
