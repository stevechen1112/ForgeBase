"""
Legacy Site Intake — Site Discovery & Content Extraction service.

Responsibilities:
  1. Crawl a legacy website: fetch sitemap, follow navigation links.
  2. Classify each URL into a page_type using AI.
  3. Extract structured entities (product, category, FAQ, etc.) from HTML.
  4. Extract content from PDF catalogues and spec sheets.
  5. Generate redirect candidates and PageBrief drafts.
"""
import io
import json
import logging
import re
import tempfile
import uuid
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.tracing import get_openai_client, WorkflowType, observe_workflow, attach_trace_metadata
from app.models.intake import (
    IntakeProject,
    IntakeUrlCandidate,
    IntakeEntityCandidate,
    IntakeRedirectCandidate,
    IntakeBriefCandidate,
)
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

ai_client = get_openai_client()

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_PAGES = 200  # safety limit per project
REQUEST_TIMEOUT = 20.0
USER_AGENT = "ForgeBase-Intake/1.0 (+https://forgebase.io)"

PAGE_TYPES = [
    "company", "category", "product", "application",
    "faq", "contact", "resource", "blog", "unknown",
]

# PDF extensions / content types we recognize
PDF_CONTENT_TYPES = {"application/pdf"}
PDF_EXTENSIONS = {".pdf"}


# ── Site Discovery ────────────────────────────────────────────────────────────

async def discover_site(
    project: IntakeProject,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Phase 1: Crawl the target site, discover all internal URLs,
    classify each URL into a page type using AI.
    Returns summary stats.
    """
    base_url = project.source_url
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc

    discovered_urls: set[str] = set()
    to_visit: list[str] = [base_url]
    visited: set[str] = set()

    # Update project status
    project.status = "crawling"
    project.updated_at = utcnow_naive()
    db.add(project)
    await db.commit()

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        while to_visit and len(discovered_urls) < MAX_PAGES:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                resp = await client.get(current_url)
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", current_url, exc)
                continue

            if resp.status_code >= 400:
                continue

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            discovered_urls.add(current_url)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract title & meta description
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else None
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta_desc_tag.get("content", "") if meta_desc_tag else None

            # Save URL candidate
            url_candidate = IntakeUrlCandidate(
                project_id=project.id,
                url=current_url,
                title=title[:500] if title else None,
                meta_description=meta_desc[:500] if meta_desc else None,
                http_status=resp.status_code,
                content_length=len(html),
                raw_text=_extract_visible_text(soup)[:10000],
            )
            db.add(url_candidate)

            # Find internal links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(current_url, href)
                parsed = urlparse(full_url)
                # Only follow same-domain, HTTP(S), non-anchor links
                if (
                    parsed.netloc == domain
                    and parsed.scheme in ("http", "https")
                    and full_url not in visited
                    and "#" not in full_url
                ):
                    clean_url = full_url.split("?")[0]  # strip query params
                    # Check if it's a PDF — index as resource
                    if any(clean_url.lower().endswith(ext) for ext in PDF_EXTENSIONS):
                        if clean_url not in discovered_urls:
                            discovered_urls.add(clean_url)
                            link_text = link.get_text(strip=True) or "PDF Document"
                            pdf_candidate = IntakeUrlCandidate(
                                project_id=project.id,
                                url=clean_url,
                                title=link_text,
                                page_type="resource",
                                confidence=0.9,
                                raw_text=f"[PDF] {link_text}",
                            )
                            db.add(pdf_candidate)
                    elif clean_url not in visited:
                        to_visit.append(clean_url)

        await db.commit()

    # Extract text from discovered PDFs
    await _extract_pdf_contents(project.id, db)

    # Classify URLs using AI
    await _classify_urls(project.id, db)

    # Update project stats
    result = await db.exec(
        select(IntakeUrlCandidate).where(
            IntakeUrlCandidate.project_id == project.id
        )
    )
    all_urls = result.all()

    project.total_urls_found = len(all_urls)
    project.status = "discovered"
    project.updated_at = utcnow_naive()
    db.add(project)
    await db.commit()

    # Build stats
    type_counts: dict[str, int] = {}
    for u in all_urls:
        type_counts[u.page_type] = type_counts.get(u.page_type, 0) + 1

    return {
        "total_urls": len(all_urls),
        "urls_by_type": type_counts,
    }


def _extract_visible_text(soup: BeautifulSoup) -> str:
    """Extract visible text from HTML, removing scripts and styles."""
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


async def _classify_urls(project_id: uuid.UUID, db: AsyncSession) -> None:
    """Use AI to classify each discovered URL into a page_type."""
    result = await db.exec(
        select(IntakeUrlCandidate).where(
            IntakeUrlCandidate.project_id == project_id,
            IntakeUrlCandidate.page_type == "unknown",
        )
    )


# ── PDF Extraction ────────────────────────────────────────────────────────────

async def _extract_pdf_contents(project_id: uuid.UUID, db: AsyncSession) -> None:
    """Download and extract text from PDF resources discovered during crawl."""
    result = await db.exec(
        select(IntakeUrlCandidate).where(
            IntakeUrlCandidate.project_id == project_id,
            IntakeUrlCandidate.page_type == "resource",
            getattr(IntakeUrlCandidate, "raw_text").startswith("[PDF]"),
        )
    )
    pdf_candidates = result.all()
    if not pdf_candidates:
        return

    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed — skipping PDF extraction")
        return

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for candidate in pdf_candidates:
            try:
                resp = await client.get(candidate.url)
                if resp.status_code != 200:
                    continue

                content_type = resp.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not candidate.url.lower().endswith(".pdf"):
                    continue

                # Extract text from PDF
                pdf_bytes = resp.content
                import io
                pdf_file = io.BytesIO(pdf_bytes)
                pdf = pdfplumber.open(pdf_file)
                pages_text = []
                for page in pdf.pages[:20]:  # limit to 20 pages
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                pdf.close()

                full_text = "\n\n".join(pages_text)
                if full_text.strip():
                    candidate.raw_text = full_text[:10000]
                    candidate.content_length = len(full_text)
                    candidate.http_status = resp.status_code
                    db.add(candidate)
                    logger.info("Extracted %d chars from PDF: %s", len(full_text), candidate.url)

            except Exception as exc:
                logger.warning("PDF extraction failed for %s: %s", candidate.url, exc)

    await db.commit()
    candidates = result.all()
    if not candidates:
        return

    # Batch classify in groups of 20
    batch_size = 20
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]
        urls_info = [
            {
                "id": str(c.id),
                "url": c.url,
                "title": c.title or "",
                "text_preview": (c.raw_text or "")[:500],
            }
            for c in batch
        ]

        prompt = f"""Classify each URL into one of these page types: {', '.join(PAGE_TYPES)}.

URLs to classify:
{json.dumps(urls_info, ensure_ascii=False, indent=2)}

Return a JSON array of objects with "id" and "page_type" and "confidence" (0.0-1.0).
Only return the JSON array, no other text."""

        try:
            response = await ai_client.chat.completions.create(
                model=settings.AI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a website structure analyst. Classify web pages by their purpose."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "[]"
            parsed = json.loads(raw)
            classifications = parsed if isinstance(parsed, list) else parsed.get("classifications", parsed.get("results", []))
        except Exception as exc:
            logger.error("AI classification failed: %s", exc)
            continue

        # Apply classifications
        id_map = {str(c.id): c for c in batch}
        for cls_item in classifications:
            cid = cls_item.get("id")
            if cid and cid in id_map:
                candidate = id_map[cid]
                ptype = cls_item.get("page_type", "unknown")
                if ptype in PAGE_TYPES:
                    candidate.page_type = ptype
                candidate.confidence = cls_item.get("confidence")
                db.add(candidate)

    await db.commit()


# ── Content Extraction ────────────────────────────────────────────────────────

async def extract_entities(
    project: IntakeProject,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Phase 2: For each classified URL (product, category, application, faq),
    extract structured entity data using AI.
    """
    project.status = "extracting"
    project.updated_at = utcnow_naive()
    db.add(project)
    await db.commit()

    # Get accepted or pending URLs of extractable types
    extractable_types = ["product", "category", "application", "faq", "certification", "resource"]
    result = await db.exec(
        select(IntakeUrlCandidate).where(
            IntakeUrlCandidate.project_id == project.id,
            IntakeUrlCandidate.page_type.in_(extractable_types),
            IntakeUrlCandidate.review_status.in_(["pending", "accepted"]),
        )
    )
    url_candidates = result.all()

    entity_counts: dict[str, int] = {}

    for url_cand in url_candidates:
        try:
            entities = await _extract_from_page(url_cand)
            for entity_data in entities:
                etype = entity_data.get("entity_type", url_cand.page_type)
                entity = IntakeEntityCandidate(
                    project_id=project.id,
                    source_url_id=url_cand.id,
                    entity_type=etype,
                    extracted_data=json.dumps(entity_data, ensure_ascii=False),
                    display_name=entity_data.get("display_name", url_cand.title),
                    confidence=entity_data.get("confidence"),
                )
                db.add(entity)
                entity_counts[etype] = entity_counts.get(etype, 0) + 1
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", url_cand.url, exc)

    await db.commit()

    # Generate redirect candidates
    await _generate_redirect_candidates(project.id, db)

    # Generate brief candidates
    await _generate_brief_candidates(project.id, db)

    # Update project
    total_entities = sum(entity_counts.values())
    project.total_entities_extracted = total_entities
    project.status = "ready_for_review"
    project.updated_at = utcnow_naive()
    db.add(project)
    await db.commit()

    return {
        "total_entities": total_entities,
        "entities_by_type": entity_counts,
    }


async def _extract_from_page(url_candidate: IntakeUrlCandidate) -> list[dict]:
    """Use AI to extract structured entities from a page's text content."""
    page_type = url_candidate.page_type
    raw_text = url_candidate.raw_text or ""

    extraction_schemas = {
        "product": {
            "fields": ["product_name", "model_number", "short_description", "specifications", "applications", "certifications", "images"],
            "instruction": "Extract product information including name, model number, specifications (as key-value pairs), and applications.",
        },
        "category": {
            "fields": ["category_name", "description", "subcategories", "product_count"],
            "instruction": "Extract category/classification information including name and description.",
        },
        "application": {
            "fields": ["application_name", "challenge", "solution", "related_products", "industry"],
            "instruction": "Extract application/use-case information including the problem it solves and relevant products.",
        },
        "faq": {
            "fields": ["questions"],  # [{question, answer}]
            "instruction": "Extract FAQ items as question-answer pairs.",
        },
        "certification": {
            "fields": ["certification_name", "issuing_body", "scope", "valid_until"],
            "instruction": "Extract certification or quality standard information.",
        },
        "resource": {
            "fields": ["resource_name", "resource_type", "download_url", "description", "product_names", "model_numbers", "specifications"],
            "instruction": "Extract downloadable resource information (PDFs, catalogues, spec sheets). If this is a product catalogue or spec sheet, also extract any product names, model numbers, and specifications you can find.",
        },
    }

    schema = extraction_schemas.get(page_type)
    if not schema:
        return []

    prompt = f"""{schema['instruction']}

Page URL: {url_candidate.url}
Page title: {url_candidate.title or 'N/A'}

Page content:
{raw_text[:6000]}

Return a JSON array of extracted entities. Each entity should have:
- "entity_type": "{page_type}"
- "display_name": human-readable name
- "confidence": 0.0-1.0 indicating extraction quality
- Plus the relevant fields: {', '.join(schema['fields'])}

Only return valid JSON array. If no entities found, return []."""

    try:
        response = await ai_client.chat.completions.create(
            model=settings.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Extract structured data from web page content. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "[]"
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        # Handle wrapped responses
        for key in ("entities", "results", "items"):
            if key in parsed:
                return parsed[key]
        return [parsed] if "entity_type" in parsed else []
    except Exception as exc:
        logger.error("AI extraction failed for %s: %s", url_candidate.url, exc)
        return []


async def _generate_redirect_candidates(
    project_id: uuid.UUID, db: AsyncSession
) -> None:
    """Generate redirect candidates from old URLs to suggested ForgeBase slugs."""
    result = await db.exec(
        select(IntakeUrlCandidate).where(
            IntakeUrlCandidate.project_id == project_id,
            IntakeUrlCandidate.page_type.in_(["product", "category", "application", "faq"]),
        )
    )
    url_candidates = result.all()

    # Also load entity candidates to generate better slugs
    entity_result = await db.exec(
        select(IntakeEntityCandidate).where(
            IntakeEntityCandidate.project_id == project_id,
        )
    )
    entities_by_url: dict[str, IntakeEntityCandidate] = {}
    for ent in entity_result.all():
        if ent.source_url_id:
            entities_by_url[str(ent.source_url_id)] = ent

    PAGE_TYPE_PREFIX = {
        "product": "/products/",
        "category": "/categories/",
        "application": "/applications/",
        "faq": "/faq",
    }

    for uc in url_candidates:
        parsed = urlparse(uc.url)
        from_path = parsed.path
        if not from_path or from_path == "/":
            continue

        # Generate a meaningful target slug
        prefix = PAGE_TYPE_PREFIX.get(uc.page_type, "/")
        entity = entities_by_url.get(str(uc.id))
        if entity and entity.display_name:
            slug = _slugify(entity.display_name)
        elif uc.title:
            slug = _slugify(uc.title)
        else:
            slug = _slugify(from_path.split("/")[-1])

        suggested_to = f"{prefix}{slug}" if prefix != "/faq" else "/faq"

        redirect = IntakeRedirectCandidate(
            project_id=project_id,
            from_path=from_path,
            suggested_to_path=suggested_to,
        )
        db.add(redirect)

    await db.commit()


async def _generate_brief_candidates(
    project_id: uuid.UUID, db: AsyncSession
) -> None:
    """Generate PageBrief drafts from entity candidates with SEO + buyer persona."""
    result = await db.exec(
        select(IntakeEntityCandidate).where(
            IntakeEntityCandidate.project_id == project_id,
            IntakeEntityCandidate.entity_type.in_(["product", "category", "application", "faq"]),
        )
    )
    entities = result.all()

    # Load project for locale
    project_result = await db.exec(
        select(IntakeProject).where(IntakeProject.id == project_id)
    )
    project = project_result.first()
    locale = project.locale if project else "en"

    BUYER_STAGE_MAP = {
        "product": "consideration",
        "category": "awareness",
        "application": "awareness",
        "faq": "awareness",
    }
    AUDIENCE_MAP = {
        "product": "Engineers, procurement managers, and technical buyers evaluating specific models",
        "category": "B2B buyers exploring product categories and comparing options",
        "application": "Decision-makers researching solutions for specific industrial challenges",
        "faq": "Potential buyers with pre-purchase questions about products and services",
    }
    CTA_MAP = {
        "product": "request_quote",
        "category": "browse_products",
        "application": "contact_specialist",
        "faq": "contact_us",
    }

    for entity in entities:
        try:
            data = json.loads(entity.extracted_data) if entity.extracted_data else {}
        except json.JSONDecodeError:
            data = {}

        target_page_type = entity.entity_type
        display_name = entity.display_name or ""

        # Extract primary keyword based on entity type
        primary_keyword = (
            data.get("product_name")
            or data.get("category_name")
            or data.get("application_name")
            or display_name
        )

        # Build secondary keywords from specs, model numbers, applications
        secondary_kws: list[str] = []
        if data.get("model_number"):
            secondary_kws.append(data["model_number"])
        if isinstance(data.get("applications"), list):
            secondary_kws.extend(data["applications"][:3])
        if isinstance(data.get("subcategories"), list):
            secondary_kws.extend(data["subcategories"][:3])
        if data.get("industry"):
            secondary_kws.append(data["industry"])

        # Determine word count target
        word_count = 800 if target_page_type == "product" else 600

        brief = IntakeBriefCandidate(
            project_id=project_id,
            entity_candidate_id=entity.id,
            target_page_type=target_page_type,
            title_draft=display_name,
            suggested_slug=_slugify(display_name),
            primary_keyword=primary_keyword,
            secondary_keywords=json.dumps(secondary_kws, ensure_ascii=False) if secondary_kws else None,
            audience_persona=AUDIENCE_MAP.get(target_page_type, "B2B industrial buyers"),
            buyer_stage=BUYER_STAGE_MAP.get(target_page_type, "awareness"),
            notes=f"Auto-generated from intake. Source entity: {entity.entity_type}. "
                  f"Model: {data.get('model_number', 'N/A')}. "
                  f"Confidence: {entity.confidence or 'N/A'}",
        )
        db.add(brief)

    await db.commit()


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:120]
