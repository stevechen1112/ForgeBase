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


def revalidate_endpoints() -> list[str]:
    raw = (settings.WEB_REVALIDATE_URLS or settings.WEB_REVALIDATE_URL or "").strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


async def revalidate_paths(
    paths: Iterable[str],
    layouts: Iterable[str] | None = None,
) -> bool:
    """呼叫所有已設定的 web 前台 revalidate；未設定時靜默略過。"""
    urls = revalidate_endpoints()
    if not urls:
        return False
    payload = {
        "paths": sorted(set(paths)),
        "layouts": sorted(set(layouts or [])),
    }
    if not payload["paths"] and not payload["layouts"]:
        return False
    headers = {"x-revalidate-secret": settings.WEB_REVALIDATE_SECRET}
    ok = True
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for url in urls:
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                except Exception as exc:  # noqa: BLE001 — 單一前台失敗不得中斷其他站
                    logger.warning("revalidate error %s: %s", url, exc)
                    ok = False
                    continue
                if resp.status_code != 200:
                    logger.warning("revalidate failed: %s %s %s", url, resp.status_code, resp.text[:200])
                    ok = False
    except Exception as exc:  # noqa: BLE001 — revalidate 不得中斷主流程
        logger.warning("revalidate error: %s", exc)
        return False
    return ok


TENANT_COPY_PAGE_PATHS = (
    "/",
    "/about",
    "/news",
    "/products",
    "/zh-TW",
    "/zh-TW/about",
    "/zh-TW/news",
    "/zh-TW/products",
)
TENANT_COPY_LAYOUT_PATHS = (
    "/",
    "/products",
    "/zh-TW",
    "/zh-TW/products",
)


async def revalidate_tenant_copy() -> bool:
    """Invalidate homepage, listing pages, and nested product detail caches."""
    return await revalidate_paths(TENANT_COPY_PAGE_PATHS, TENANT_COPY_LAYOUT_PATHS)


async def revalidate_page(slug: str, locale: str = "en", include_sitemap: bool = False) -> bool:
    paths = page_paths(slug, locale)
    if include_sitemap:
        paths.append("/sitemap.xml")
    return await revalidate_paths(paths)
