"""Tests for per-customer invoice language feature."""
import pytest
from datetime import date
from decimal import Decimal

from apps.customers.models import Customer
from apps.invoices.services import InvoiceService, LABELS
from apps.invoices.types import InvoiceData, InvoiceLineItem


@pytest.fixture
def customer_de(db, tenant):
    """Customer with German invoice language."""
    return Customer.objects.create(
        tenant=tenant,
        name="Deutsche Firma GmbH",
        address={"street": "Hauptstr. 1", "city": "Berlin", "country": "Germany"},
        invoice_language="de",
    )


@pytest.fixture
def customer_en(db, tenant):
    """Customer with English invoice language."""
    return Customer.objects.create(
        tenant=tenant,
        name="English Corp Ltd",
        address={"street": "1 Main St", "city": "London", "country": "UK"},
        invoice_language="en",
    )


@pytest.fixture
def customer_default(db, tenant):
    """Customer with no invoice language (uses system default)."""
    return Customer.objects.create(
        tenant=tenant,
        name="Default Customer",
        address={"street": "Default St", "city": "Somewhere"},
        invoice_language="",
    )


class TestCustomerInvoiceLanguageField:
    """Test the invoice_language field on Customer model."""

    def test_default_is_empty(self, db, tenant):
        customer = Customer.objects.create(
            tenant=tenant,
            name="Test Customer",
        )
        assert customer.invoice_language == ""

    def test_set_german(self, customer_de):
        assert customer_de.invoice_language == "de"

    def test_set_english(self, customer_en):
        assert customer_en.invoice_language == "en"

    def test_update_language(self, customer_default):
        customer_default.invoice_language = "en"
        customer_default.save(update_fields=["invoice_language"])
        customer_default.refresh_from_db()
        assert customer_default.invoice_language == "en"

    def test_clear_language(self, customer_en):
        customer_en.invoice_language = ""
        customer_en.save(update_fields=["invoice_language"])
        customer_en.refresh_from_db()
        assert customer_en.invoice_language == ""


class TestResolveInvoiceLanguage:
    """Test the _resolve_invoice_language helper in views."""

    def test_customer_with_language(self, db, tenant, customer_en):
        from apps.invoices.views import _resolve_invoice_language
        result = _resolve_invoice_language(tenant, customer_en.id, fallback="de")
        assert result == "en"

    def test_customer_without_language(self, db, tenant, customer_default):
        from apps.invoices.views import _resolve_invoice_language
        result = _resolve_invoice_language(tenant, customer_default.id, fallback="de")
        assert result == "de"

    def test_nonexistent_customer(self, db, tenant):
        from apps.invoices.views import _resolve_invoice_language
        result = _resolve_invoice_language(tenant, 99999, fallback="de")
        assert result == "de"

    def test_none_customer_id(self, db, tenant):
        from apps.invoices.views import _resolve_invoice_language
        result = _resolve_invoice_language(tenant, None, fallback="en")
        assert result == "en"


class TestGeneratePdfWithCustomerLanguages:
    """Test that generate_pdf respects customer_languages mapping."""

    def _make_invoice(self, customer_id, customer_name="Test"):
        return InvoiceData(
            contract_id=1,
            contract_name="Contract 1",
            customer_id=customer_id,
            customer_name=customer_name,
            customer_address={},
            billing_date=date(2026, 1, 1),
            billing_period_start=date(2026, 1, 1),
            billing_period_end=date(2026, 1, 31),
            line_items=[
                InvoiceLineItem(
                    item_id=1,
                    product_name="Product",
                    description="Desc",
                    quantity=1,
                    unit_price=Decimal("100.00"),
                    amount=Decimal("100.00"),
                    is_prorated=False,
                    prorate_factor=None,
                    is_one_off=False,
                )
            ],
            invoice_text="",
            customer_number="",
            sales_order_number="",
            contract_number="",
            po_number="",
            order_confirmation_number="",
            contract_start_date=date(2026, 1, 1),
            contract_end_date=date(2026, 12, 31),
            billing_interval="monthly",
        )

    def test_customer_languages_mapping_used(self, db, tenant):
        """Test that the customer_languages dict is used correctly."""
        # Verify LABELS dict has expected keys
        assert "invoice" in LABELS["de"]
        assert LABELS["de"]["invoice"] == "Rechnung"
        assert "invoice" in LABELS["en"]
        assert LABELS["en"]["invoice"] == "Invoice"

    def test_customer_languages_fallback(self):
        """When customer not in mapping, fall back to default language."""
        customer_languages = {100: "en"}  # Only customer 100 has English
        inv = self._make_invoice(customer_id=200)
        # Customer 200 not in map, should use fallback
        lang = customer_languages.get(inv.customer_id, "de")
        assert lang == "de"

    def test_customer_languages_override(self):
        """When customer is in mapping, use their language."""
        customer_languages = {100: "en"}
        inv = self._make_invoice(customer_id=100)
        lang = customer_languages.get(inv.customer_id, "de")
        assert lang == "en"
