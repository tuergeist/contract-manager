"""Tests for invoice PDF generation: legal fields, tax, numbers, template customization."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.template.loader import render_to_string

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import CompanyLegalData, InvoiceTemplate
from apps.invoices.services import InvoiceService, LABELS
from apps.invoices.types import InvoiceData, InvoiceLineItem
from apps.products.models import Product


@pytest.fixture
def legal_data(db, tenant):
    return CompanyLegalData.objects.create(
        tenant=tenant,
        company_name="Test GmbH",
        street="Teststraße 1",
        zip_code="80331",
        city="München",
        country="Deutschland",
        tax_number="123/456/78901",
        vat_id="DE123456789",
        commercial_register_court="Amtsgericht München",
        commercial_register_number="HRB 12345",
        managing_directors=["Max Mustermann", "Erika Mustermann"],
        bank_name="Deutsche Bank",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        phone="+49 89 12345",
        email="info@test-gmbh.de",
        website="https://www.test-gmbh.de",
        share_capital="25.000,00 EUR",
        default_tax_rate=Decimal("19.00"),
    )


@pytest.fixture
def template_settings(db, tenant):
    return InvoiceTemplate.objects.create(
        tenant=tenant,
        accent_color="#e63946",
        header_text="Ihr zuverlässiger Partner",
        footer_text="Zahlbar innerhalb von 14 Tagen.\nVielen Dank für Ihr Vertrauen.",
    )


@pytest.fixture
def sample_invoice():
    return InvoiceData(
        contract_id=1,
        contract_name="SaaS Contract",
        customer_id=1,
        customer_name="Acme Corp",
        customer_address={"street": "Hauptstraße 1", "city": "Berlin", "zip": "10115"},
        billing_date=date(2026, 1, 1),
        billing_period_start=date(2026, 1, 1),
        billing_period_end=date(2026, 1, 31),
        line_items=[
            InvoiceLineItem(
                item_id=1,
                product_name="SaaS License",
                description="",
                quantity=1,
                unit_price=Decimal("1000.00"),
                amount=Decimal("1000.00"),
                is_prorated=False,
                prorate_factor=None,
                is_one_off=False,
            ),
        ],
        invoice_text="",
    )


def render_invoice_html(tenant, invoice, language="de", invoice_number="",
                        legal_data_obj=None, template_obj=None):
    """Helper to render invoice HTML via the service's template context."""
    service = InvoiceService(tenant)
    labels = LABELS.get(language, LABELS["en"])
    template_ctx = service._get_template_context()
    tax_rate = template_ctx["tax_rate"]
    total_net = invoice.total_amount
    tax_amount, total_gross = InvoiceService.calculate_tax(total_net, tax_rate)

    invoice_dict = {
        "contract_id": invoice.contract_id,
        "contract_name": invoice.contract_name,
        "customer_id": invoice.customer_id,
        "customer_name": invoice.customer_name,
        "customer_address": invoice.customer_address,
        "billing_date": invoice.billing_date,
        "billing_period_start": invoice.billing_period_start,
        "billing_period_end": invoice.billing_period_end,
        "line_items": [
            {
                "item_id": item.item_id,
                "product_name": item.product_name,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount,
                "is_prorated": item.is_prorated,
                "prorate_factor": item.prorate_factor,
                "is_one_off": item.is_one_off,
            }
            for item in invoice.line_items
        ],
        "total_amount": invoice.total_amount,
        "total_net": total_net,
        "tax_amount": tax_amount,
        "total_gross": total_gross,
        "invoice_text": invoice.invoice_text,
        "po_number": invoice.po_number,
        "order_confirmation_number": invoice.order_confirmation_number,
    }

    return render_to_string(
        "invoices/invoice.html",
        {
            "invoice": invoice_dict,
            "labels": labels,
            "language": language,
            "currency_symbol": "€",
            "invoice_number": invoice_number,
            "tax_rate": tax_rate,
            **template_ctx,
        },
    )


class TestInvoiceNumberInPdf:
    def test_invoice_number_shown_in_header(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice, invoice_number="2026-0001")
        assert "2026-0001" in html

    def test_invoice_number_in_details_section(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice, invoice_number="2026-0001")
        assert "Rechnungsnr." in html
        assert "2026-0001" in html

    def test_no_invoice_number_when_empty(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice, invoice_number="")
        assert "Rechnungsnr." not in html


class TestTaxBreakdownInPdf:
    def test_net_total_shown(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Nettobetrag" in html
        # Django floatformat uses locale-specific separator (comma in de)
        assert "1000" in html

    def test_tax_line_shown(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "MwSt." in html
        assert "19" in html
        assert "190" in html

    def test_gross_total_shown(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Rechnungsbetrag" in html
        assert "1190" in html


class TestCompanyLegalDataInPdf:
    def test_company_name_in_header(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Test GmbH" in html

    def test_company_address_in_header(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Teststraße 1" in html
        assert "80331" in html
        assert "München" in html

    def test_vat_id_in_header(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "DE123456789" in html

    def test_tax_number_in_header(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "123/456/78901" in html


class TestGmbHLegalFooter:
    def test_register_info(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Amtsgericht München" in html
        assert "HRB 12345" in html

    def test_managing_directors(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Max Mustermann" in html
        assert "Erika Mustermann" in html
        assert "Geschäftsführer" in html

    def test_bank_details(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Deutsche Bank" in html
        assert "DE89370400440532013000" in html
        assert "COBADEFFXXX" in html

    def test_share_capital(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "25.000,00 EUR" in html

    def test_contact_info(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "+49 89 12345" in html
        assert "info@test-gmbh.de" in html
        assert "https://www.test-gmbh.de" in html


class TestTemplateCustomization:
    def test_accent_color_applied(self, db, tenant, legal_data, template_settings, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "#e63946" in html

    def test_header_text_shown(self, db, tenant, legal_data, template_settings, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Ihr zuverlässiger Partner" in html

    def test_footer_text_shown(self, db, tenant, legal_data, template_settings, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Zahlbar innerhalb von 14 Tagen." in html
        assert "Vielen Dank für Ihr Vertrauen." in html

    def test_default_accent_when_no_template(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "#2563eb" in html

    def test_no_header_text_when_not_set(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        # The div with class header-text should not appear in the body when empty
        assert 'class="header-text"' not in html.split("</style>")[1]


class TestServicePeriodDisplay:
    def test_service_period_label(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Leistungszeitraum" in html

    def test_service_period_dates(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "01.01.2026" in html
        assert "31.01.2026" in html

    def test_service_period_english(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice, language="en")
        assert "Service Period" in html


class TestFallbackRendering:
    def test_renders_without_legal_data(self, db, tenant, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        # Should use tenant name as fallback company name
        assert tenant.name in html
        # Should not have legal footer
        assert "Handelsregister" not in html

    def test_renders_without_template_settings(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        # Should use default accent color
        assert "#2563eb" in html
        # Company data should still be present
        assert "Test GmbH" in html

    def test_no_logo_renders_cleanly(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        # The img tag should not appear when no logo is set
        assert "<img" not in html.split("</style>")[1]


class TestEnglishLabels:
    def test_english_tax_labels(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice, language="en")
        assert "Net Total" in html
        assert "VAT" in html
        assert "Invoice Total" in html

    def test_english_legal_labels(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice, language="en")
        assert "Commercial Register" in html
        assert "Managing Directors" in html
        assert "Bank Details" in html


class TestInvoiceMetadataFields:
    def test_po_number_shown_when_set(self, db, tenant, legal_data, sample_invoice):
        sample_invoice.po_number = "PO-2026-001"
        html = render_invoice_html(tenant, sample_invoice)
        assert "Bestellnummer" in html
        assert "PO-2026-001" in html

    def test_po_number_hidden_when_empty(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Bestellnummer" not in html

    def test_order_confirmation_shown_when_set(self, db, tenant, legal_data, sample_invoice):
        sample_invoice.order_confirmation_number = "AB-2026-001"
        html = render_invoice_html(tenant, sample_invoice)
        assert "Auftragsbestätigung" in html
        assert "AB-2026-001" in html

    def test_order_confirmation_hidden_when_empty(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert "Auftragsbestätigung" not in html

    def test_invoice_text_shown_when_set(self, db, tenant, legal_data, sample_invoice):
        sample_invoice.invoice_text = "Payment due within 30 days"
        html = render_invoice_html(tenant, sample_invoice)
        assert "Payment due within 30 days" in html

    def test_invoice_text_hidden_when_empty(self, db, tenant, legal_data, sample_invoice):
        html = render_invoice_html(tenant, sample_invoice)
        assert 'class="invoice-text"' not in html.split("</style>")[1]

    def test_english_labels_for_metadata(self, db, tenant, legal_data, sample_invoice):
        sample_invoice.po_number = "PO-123"
        sample_invoice.order_confirmation_number = "AB-456"
        html = render_invoice_html(tenant, sample_invoice, language="en")
        assert "PO Number" in html
        assert "Order Confirmation" in html
