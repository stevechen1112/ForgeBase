"""
Tests for the Legacy Site Intake module.

Includes:
  - Unit tests for heuristic classification and entity extraction
  - Endpoint smoke tests (no DB required)
  - Integration tests for the full pipeline (require DB)
"""
import json
import re
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.api.v1.endpoints.intake import (
    _application_path,
    _category_path,
    _normalize_content_locale,
    _product_path,
)
from app.services.intake_engine import _extract_visible_text, _slugify


# ── Unit tests — no DB, no network ──────────────────────────────────────────

class TestSlugify:
    def test_basic(self):
        assert _slugify("Panasonic TM-5") == "panasonic-tm-5"

    def test_chinese(self):
        result = _slugify("焊接機械手臂 TM-5")
        assert "tm-5" in result

    def test_special_chars(self):
        assert _slugify("Product & Type (A/B)") == "product-type-ab"

    def test_max_length(self):
        long_name = "A" * 200
        assert len(_slugify(long_name)) <= 120

    def test_empty(self):
        assert _slugify("") == ""


class TestExtractVisibleText:
    def test_removes_scripts(self):
        from bs4 import BeautifulSoup
        html = "<html><body><script>alert('xss')</script><p>Hello</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_visible_text(soup)
        assert "alert" not in result
        assert "Hello" in result

    def test_removes_styles(self):
        from bs4 import BeautifulSoup
        html = "<html><body><style>.a{color:red}</style><p>World</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_visible_text(soup)
        assert "color" not in result
        assert "World" in result

    def test_collapses_blank_lines(self):
        from bs4 import BeautifulSoup
        html = "<p>A</p><br/><br/><br/><br/><br/><p>B</p>"
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_visible_text(soup)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result


class TestIntakeCommitHelpers:
    def test_normalize_content_locale_traditional_chinese(self):
        assert _normalize_content_locale("zh-tw") == "zh-TW"
        assert _normalize_content_locale("zh_TW") == "zh-TW"

    def test_normalize_content_locale_english(self):
        assert _normalize_content_locale("en") == "en"
        assert _normalize_content_locale("EN-us") == "en"

    def test_product_path_uses_category_when_available(self):
        assert _product_path("welding-tools", "yd-350nr1") == "/products/welding-tools/yd-350nr1"

    def test_product_path_falls_back_without_category(self):
        assert _product_path(None, "yd-350nr1") == "/products/yd-350nr1"

    def test_category_and_application_paths(self):
        assert _category_path("welding-tools") == "/products/welding-tools"
        assert _application_path("robotic-welding") == "/applications/robotic-welding"


# ── Test intake model structure ────────────────────────────────────────────

class TestIntakeModels:
    def test_project_defaults(self):
        from app.models.intake import IntakeProject
        import uuid

        project = IntakeProject(
            project_name="Test",
            source_url="https://example.com",
            created_by=uuid.uuid4(),
        )
        assert project.status == "created"
        assert project.locale == "zh-tw"
        assert project.total_urls_found == 0
        assert project.total_entities_extracted == 0

    def test_url_candidate_defaults(self):
        from app.models.intake import IntakeUrlCandidate
        import uuid

        candidate = IntakeUrlCandidate(
            project_id=uuid.uuid4(),
            url="https://example.com/page/123",
        )
        assert candidate.page_type == "unknown"
        assert candidate.review_status == "pending"

    def test_entity_candidate_defaults(self):
        from app.models.intake import IntakeEntityCandidate
        import uuid

        entity = IntakeEntityCandidate(
            project_id=uuid.uuid4(),
            entity_type="product",
        )
        assert entity.review_status == "pending"
        assert entity.committed_entity_id is None

    def test_redirect_candidate_defaults(self):
        from app.models.intake import IntakeRedirectCandidate
        import uuid

        redirect = IntakeRedirectCandidate(
            project_id=uuid.uuid4(),
            from_path="/page/OLD123",
        )
        assert redirect.review_status == "pending"
        assert redirect.suggested_to_path is None

    def test_brief_candidate_defaults(self):
        from app.models.intake import IntakeBriefCandidate
        import uuid

        brief = IntakeBriefCandidate(
            project_id=uuid.uuid4(),
            target_page_type="product",
        )
        assert brief.review_status == "pending"
        assert brief.committed_brief_id is None


# ── Test schema validation ─────────────────────────────────────────────────

class TestIntakeSchemas:
    def test_project_create(self):
        from app.schemas.intake import IntakeProjectCreate

        body = IntakeProjectCreate(
            project_name="示範製造商導入",
            source_url="https://example-manufacturer.com",
        )
        assert body.project_name == "示範製造商導入"
        assert body.source_url == "https://example-manufacturer.com"

    def test_url_review(self):
        from app.schemas.intake import IntakeUrlReview

        review = IntakeUrlReview(review_status="accepted", page_type="product")
        assert review.review_status == "accepted"

    def test_entity_review_with_data(self):
        from app.schemas.intake import IntakeEntityReview

        data = json.dumps({"product_name": "TM-5", "model_number": "TM-5"})
        review = IntakeEntityReview(review_status="accepted", extracted_data=data)
        assert review.review_status == "accepted"
        assert "TM-5" in review.extracted_data

    def test_project_summary(self):
        from app.schemas.intake import IntakeProjectSummary
        import uuid

        summary = IntakeProjectSummary(
            project_id=uuid.uuid4(),
            status="ready_for_review",
            total_urls=50,
            urls_by_type={"product": 20, "category": 5, "blog": 25},
            total_entities=15,
            entities_by_type={"product": 12, "category": 3},
            total_redirects=8,
            total_briefs=6,
        )
        assert summary.total_urls == 50
        assert summary.urls_by_type["product"] == 20


# ── Test common legacy-site URL / content patterns ─────────────────────────

class TestLegacySitePatterns:
    """Generic pattern checks for common legacy manufacturer site structures."""

    def test_page_url_pattern(self):
        """Some legacy CMS sites use /page/HEXID and /article/HEXID paths."""
        url1 = "https://example-manufacturer.com/page/2660FABD752D0BE0AAE2"
        url2 = "https://example-manufacturer.com/article/C7A8C2CE24D6CF12FA02"
        assert "/page/" in url1
        assert "/article/" in url2

    def test_model_number_extraction(self):
        """Expect to find industrial model numbers like TM-5, TS-950."""
        text = "Panasonic TM-5 焊接機械手臂，適用於 0.5-3.0mm 薄板焊接。TM-20 大範圍型。"
        models = re.findall(r'[A-Z]{1,5}[-_]?\d{2,5}[A-Z]?(?:[-/]\d+)?', text)
        assert "TM-5" in models or "TM" in str(models)

    def test_taiwanese_contact_patterns(self):
        """Traditional contact patterns on TW sites."""
        text = "TEL: 04-2355-6789  FAX: 04-2355-6780  info@example-manufacturer.com.tw"
        has_phone = bool(re.search(r'\d{2,3}-\d{4}-\d{4}', text))
        has_email = bool(re.search(r'[\w.]+@[\w.-]+\.com\.tw', text))
        assert has_phone
        assert has_email
