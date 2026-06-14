"""Regression tests for the offer PDF rendering pipeline:

- Markdown free-text fields → sanitized HTML in the template context
- Min-term / notice-period lines rendered only when set + > 0
- Bleach allowlist strips dangerous tags

These tests bypass the WeasyPrint write_pdf step (which is expensive and
not deterministic) and assert on the template HTML directly, which is
faster, repeatable, and sufficient to lock the rendering contract.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.invoices.models import CompanyLegalData
from apps.offers.markdown_render import render_markdown_to_safe_html
from apps.offers.models import OfferNumberScheme, OfferRecord
from apps.offers.services import (
    OfferService,
    _render_minimum_term_line,
    _render_notice_period_line,
)


@pytest.fixture
def tenant(db):
    from apps.tenants.models import Tenant

    t = Tenant.objects.create(name="PdfRenderTest")
    return t


@pytest.fixture
def customer(tenant):
    from apps.customers.models import Customer

    return Customer.objects.create(
        tenant=tenant,
        name="ACME GmbH",
        address={"country": "Germany"},
    )


@pytest.fixture
def legal_data(tenant):
    return CompanyLegalData.objects.create(
        tenant=tenant,
        company_name="Acme GmbH",
        street="Street 1",
        zip_code="12345",
        city="Berlin",
        country="Germany",
        vat_id="DE123456789",
        commercial_register_court="AG Berlin",
        commercial_register_number="HRB 1",
        managing_directors=["Max Mustermann"],
        default_tax_rate=Decimal("19.00"),
    )


@pytest.fixture
def offer(tenant, customer, legal_data):
    OfferNumberScheme.objects.create(
        tenant=tenant,
        pattern="{YYYY}-{NNNN}",
        next_counter=1,
        reset_period=OfferNumberScheme.ResetPeriod.YEARLY,
        last_reset_year=2026,
    )
    return OfferRecord.objects.create(
        tenant=tenant,
        customer=customer,
        offer_number="2026-0001",
        offer_date=date(2026, 1, 1),
        valid_until=date(2026, 2, 1),
        billing_date=date(2026, 1, 1),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_net=Decimal("100.00"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("19.00"),
        total_gross=Decimal("119.00"),
        line_items_snapshot=[],
        company_data_snapshot={},
        status=OfferRecord.Status.DRAFT,
        customer_name=customer.name,
        contract_name="Contract X",
    )


class TestMarkdownSanitizer:
    """render_markdown_to_safe_html drops dangerous HTML and keeps safe."""

    def test_empty_input_returns_empty(self):
        assert render_markdown_to_safe_html("") == ""
        assert render_markdown_to_safe_html("   \n  ") == ""

    def test_paragraphs_preserved(self):
        out = render_markdown_to_safe_html("hello\n\nworld")
        assert "<p>hello</p>" in out
        assert "<p>world</p>" in out

    def test_bold_italic_preserved(self):
        out = render_markdown_to_safe_html("**bold** and *em*")
        assert "<strong>bold</strong>" in out
        assert "<em>em</em>" in out

    def test_lists_preserved(self):
        out = render_markdown_to_safe_html("- one\n- two")
        assert "<ul>" in out
        assert "<li>one</li>" in out

    def test_script_tag_stripped(self):
        # bleach with strip=True removes the <script> wrapper. The text
        # content of the tag remains as a plain text node — that is safe
        # in a PDF context (no JS execution) and matches bleach's
        # documented behavior. The security guarantee is "no <script>
        # tag survives", not "every byte of malicious markup vanishes".
        out = render_markdown_to_safe_html('<script>alert(1)</script> ok')
        assert "<script" not in out
        assert "</script" not in out
        assert "ok" in out

    def test_anchor_stripped(self):
        out = render_markdown_to_safe_html('[link](http://evil.example)')
        assert "<a " not in out
        assert "href" not in out

    def test_image_stripped(self):
        out = render_markdown_to_safe_html('![alt](http://x/y.png)')
        assert "<img" not in out

    def test_inline_style_stripped(self):
        out = render_markdown_to_safe_html(
            '<p style="color:red">x</p>'
        )
        assert "style=" not in out
        assert "x" in out

    def test_headings_h3_h4_kept(self):
        out = render_markdown_to_safe_html("### Title\n\n#### Sub")
        assert "<h3>Title</h3>" in out
        assert "<h4>Sub</h4>" in out


class TestMinTermNoticeLines:
    def test_minimum_term_german(self):
        assert _render_minimum_term_line(12, "de") == (
            "Mindestlaufzeit 12 Monate ab Vertragsbeginn."
        )

    def test_minimum_term_english(self):
        assert _render_minimum_term_line(12, "en") == (
            "Minimum term 12 months from the contract start date."
        )

    def test_minimum_term_zero_returns_empty(self):
        assert _render_minimum_term_line(0, "de") == ""

    def test_minimum_term_none_returns_empty(self):
        assert _render_minimum_term_line(None, "de") == ""

    def test_notice_period_german(self):
        assert _render_notice_period_line(3, "de") == (
            "Kündigungsfrist 3 Monate zum Ende der "
            "Mindestvertragslaufzeit."
        )

    def test_notice_period_english(self):
        assert _render_notice_period_line(3, "en") == (
            "Notice period 3 months to the end of the minimum term."
        )

    def test_notice_period_zero_returns_empty(self):
        assert _render_notice_period_line(0, "en") == ""


class TestTemplateContextWiring:
    """_build_record_template_context produces the keys the template
    relies on, including for newly-added blocks."""

    def test_context_has_free_text_html_keys(self, tenant, offer):
        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        assert "free_text_after_items_html" in ctx
        assert "free_text_before_terms_html" in ctx
        assert "minimum_term_line" in ctx
        assert "notice_period_line" in ctx

    def test_empty_free_text_yields_empty_html(self, tenant, offer):
        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        assert ctx["free_text_after_items_html"] == ""
        assert ctx["free_text_before_terms_html"] == ""

    def test_filled_free_text_yields_sanitized_html(self, tenant, offer):
        offer.free_text_after_items = "**hi** <script>bad</script>"
        offer.free_text_before_terms = "_world_"
        offer.save()
        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        assert "<strong>hi</strong>" in ctx["free_text_after_items_html"]
        assert "<script" not in ctx["free_text_after_items_html"]
        assert "<em>world</em>" in ctx["free_text_before_terms_html"]

    def test_min_term_and_notice_rendered_when_set(self, tenant, offer):
        offer.minimum_term_months = 12
        offer.notice_period_months = 3
        offer.save()
        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        assert "Mindestlaufzeit 12 Monate" in ctx["minimum_term_line"]
        assert "Kündigungsfrist 3 Monate" in ctx["notice_period_line"]

    def test_min_term_skipped_when_null(self, tenant, offer):
        # Both default to None per migration
        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        assert ctx["minimum_term_line"] == ""
        assert ctx["notice_period_line"] == ""


class TestRenderedHtmlIncludesBlocks:
    """End-to-end at the Jinja layer: the generated HTML actually
    contains the rendered blocks at their expected positions."""

    @patch("apps.offers.services.HTML")
    def test_html_contains_free_text_blocks_when_set(
        self, mock_html, tenant, offer
    ):
        from django.template.loader import render_to_string

        offer.free_text_after_items = "Note **after** items"
        offer.free_text_before_terms = "Footer note"
        offer.minimum_term_months = 24
        offer.notice_period_months = 6
        offer.save()

        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        html = render_to_string("offers/offer.html", ctx)

        assert "offer-free-text after-items" in html
        assert "offer-free-text before-terms" in html
        assert "<strong>after</strong>" in html
        assert "Footer note" in html
        assert "Mindestlaufzeit 24 Monate" in html
        assert "Kündigungsfrist 6 Monate" in html

    @patch("apps.offers.services.HTML")
    def test_html_omits_empty_blocks(self, mock_html, tenant, offer):
        from django.template.loader import render_to_string

        service = OfferService(tenant)
        ctx = service._build_record_template_context(offer, "de")
        html = render_to_string("offers/offer.html", ctx)

        assert "offer-free-text after-items" not in html
        assert "offer-free-text before-terms" not in html
        assert "Mindestlaufzeit" not in html
        assert "Kündigungsfrist" not in html
