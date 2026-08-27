from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeSource

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    text: str
    score: float
    source_type: str
    source_id: uuid.UUID
    title: str
    url: str | None
    page_number: int | None
    filename: str | None
    metadata: dict[str, Any]


def tokenize(query: str) -> list[str]:
    return [item.lower() for item in _TOKEN_RE.findall(query or "")]


def score_chunk(query: str, chunk_text: str, metadata: dict[str, Any], *, page_boost: bool) -> float:
    tokens = tokenize(query)
    haystack = f"{chunk_text} {json.dumps(metadata, ensure_ascii=False)}".lower()
    if not tokens:
        return 0.15 if page_boost else 0.0
    overlap = sum(1 for token in tokens if token in haystack)
    score = overlap / max(len(tokens), 1)
    model_number = str(metadata.get("model_number") or "").lower()
    if model_number and model_number in query.lower():
        score += 1.5
    cert_name = str(metadata.get("cert_name") or "").lower()
    if cert_name and cert_name in query.lower():
        score += 1.2
    if page_boost:
        score += 0.85
    return score


def buyer_source(chunk: RetrievedChunk) -> dict[str, str]:
    """Visitor-visible source: answer link only if they can actually open it."""
    payload = {
        "type": chunk.source_type,
        "id": str(chunk.source_id),
        "name": chunk.title,
        "url": chunk.url or "",
    }
    return payload


def admin_source(chunk: RetrievedChunk) -> dict[str, str]:
    payload = buyer_source(chunk)
    if chunk.filename:
        payload["filename"] = chunk.filename
    if chunk.page_number:
        payload["page_number"] = str(chunk.page_number)
    return payload


async def retrieve_public_chunks(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    query: str,
    locale: str,
    current_source_type: str | None = None,
    current_source_id: uuid.UUID | None = None,
    limit: int = 8,
) -> list[RetrievedChunk]:
    if tenant_id is None:
        return []

    fts_ids: set[uuid.UUID] = set()
    if (query or "").strip():
        try:
            async with session.begin_nested():
                fts_rows = (
                    await session.exec(
                        text(
                            """
                            SELECT c.id
                            FROM knowledge_chunks c
                            JOIN knowledge_sources s ON s.id = c.source_id
                            WHERE c.tenant_id = :tenant_id
                              AND s.status = 'indexed'
                              AND s.visibility = 'public'
                              AND (s.locale = :locale OR s.locale = 'en')
                              AND c.tsv @@ plainto_tsquery('simple', :query)
                            ORDER BY ts_rank(c.tsv, plainto_tsquery('simple', :query)) DESC
                            LIMIT 40
                            """
                        ),
                        params={"tenant_id": tenant_id, "locale": locale, "query": query},
                    )
                ).all()
                fts_ids = {row[0] for row in fts_rows}
        except Exception:
            fts_ids = set()

    statement = (
        select(KnowledgeChunk, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(
            KnowledgeChunk.tenant_id == tenant_id,
            KnowledgeSource.status == "indexed",
            KnowledgeSource.visibility == "public",
        )
    )
    tokens = tokenize(query)[:6]
    token_filters = [
        KnowledgeChunk.text.ilike(f"%{token}%")
        for token in tokens
        if token.replace("%", "").replace("_", "")
    ]
    page_filter = None
    if current_source_type and current_source_id:
        page_filter = (KnowledgeSource.source_type == current_source_type) & (
            KnowledgeSource.source_id == current_source_id
        )
    fts_filter = KnowledgeChunk.id.in_(fts_ids) if fts_ids else None
    narrowing = [
        item
        for item in (
            or_(*token_filters) if token_filters else None,
            page_filter,
            fts_filter,
        )
        if item is not None
    ]
    if narrowing:
        statement = statement.where(or_(*narrowing))
    rows = list((await session.exec(statement)).all())
    scored: list[RetrievedChunk] = []
    for chunk, source in rows:
        metadata = {}
        if chunk.metadata_json:
            try:
                metadata = json.loads(chunk.metadata_json)
            except json.JSONDecodeError:
                metadata = {}
        page_boost = (
            current_source_type == source.source_type and current_source_id == source.source_id
        )
        lexical = score_chunk(query, chunk.text, metadata, page_boost=page_boost)
        fts_bonus = 0.6 if chunk.id in fts_ids else 0.0
        score = lexical + fts_bonus
        if score <= 0 and not page_boost:
            continue
        scored.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                text=chunk.text,
                score=score,
                source_type=source.source_type,
                source_id=source.source_id,
                title=source.title,
                url=source.canonical_url,
                page_number=chunk.page_number,
                filename=(metadata.get("filename") if isinstance(metadata, dict) else None),
                metadata=metadata if isinstance(metadata, dict) else {},
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    # Always keep current-page chunks even if the question is short.
    if current_source_id and current_source_type:
        current = [
            item
            for item in scored
            if item.source_type == current_source_type and item.source_id == current_source_id
        ]
        others = [
            item
            for item in scored
            if not (item.source_type == current_source_type and item.source_id == current_source_id)
        ]
        merged = current[:3] + others
        # de-dupe by chunk id
        seen: set[uuid.UUID] = set()
        unique: list[RetrievedChunk] = []
        for item in merged:
            if item.chunk_id in seen:
                continue
            seen.add(item.chunk_id)
            unique.append(item)
        scored = unique
    return scored[:limit]
