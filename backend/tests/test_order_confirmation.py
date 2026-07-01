"""Tests for order confirmation (Auftragsbestätigung) feature."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.contracts.models import Contract, ContractItem, ContractItemPrice, OrderConfirmation, OrderConfirmationNumberScheme
from apps.contracts.order_confirmation_numbering import OrderConfirmationNumberService
from apps.contracts.services.order_confirmation import OrderConfirmationService, AB_LABELS
from apps.customers.models import Customer
from apps.products.models import Product


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
        billing_emails=["billing@acme.com"],
    )


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Test Product",
        sku="TEST-001",
    )


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Test Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_with_items(contract, tenant, product):
    ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        product=product,
        description="Monthly service",
        quantity=1,
        unit_price=Decimal("100.00"),
    )
    ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        description="Setup fee",
        quantity=1,
        unit_price=Decimal("500.00"),
    )
    return contract


# ---- Numbering ----

class TestOrderConfirmationNumbering:
    def test_default_pattern(self, tenant):
        service = OrderConfirmationNumberService(tenant)
        number = service.get_next_number(date(2026, 3, 4))
        assert number == "AB-2026-0001"

    def test_sequential(self, tenant):
        service = OrderConfirmationNumberService(tenant)
        n1 = service.get_next_number(date(2026, 1, 1))
        n2 = service.get_next_number(date(2026, 1, 2))
        n3 = service.get_next_number(date(2026, 1, 3))
        assert n1 == "AB-2026-0001"
        assert n2 == "AB-2026-0002"
        assert n3 == "AB-2026-0003"

    def test_custom_pattern(self, tenant):
        OrderConfirmationNumberScheme.objects.create(
            tenant=tenant,
            pattern="OC-{YY}-{NNN}",
            next_counter=42,
            reset_period=OrderConfirmationNumberScheme.ResetPeriod.NEVER,
        )
        service = OrderConfirmationNumberService(tenant)
        number = service.get_next_number(date(2026, 5, 1))
        assert number == "OC-26-042"

    def test_yearly_reset(self, tenant):
        scheme = OrderConfirmationNumberScheme.objects.create(
            tenant=tenant,
            pattern="AB-{YYYY}-{NNNN}",
            next_counter=5,
            reset_period=OrderConfirmationNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=2025,
        )
        service = OrderConfirmationNumberService(tenant)
        number = service.get_next_number(date(2026, 1, 1))
        assert number == "AB-2026-0001"


# ---- Service ----

class TestOrderConfirmationService:
    def test_build_line_items(self, tenant, contract_with_items):
        service = OrderConfirmationService(tenant)
        labels = AB_LABELS["de"]
        items = service._build_line_items(contract_with_items, labels)
        assert len(items) == 2
        assert items[0]["product_name"] == "Test Product"
        assert items[0]["amount"] == Decimal("100.00")
        assert items[1]["amount"] == Decimal("500.00")
        assert items[0]["is_one_off"] is False
        assert items[0]["has_price_periods"] is False
        assert items[0]["billing_interval_label"] == "/Monat"

    def test_build_totals(self, tenant):
        service = OrderConfirmationService(tenant)
        items = [
            {"amount": Decimal("100.00"), "is_one_off": False},
            {"amount": Decimal("500.00"), "is_one_off": False},
        ]
        totals = service._build_totals(items, Decimal("19.00"))
        assert totals["net"] == Decimal("600.00")
        assert totals["tax_amount"] == Decimal("114.00")
        assert totals["gross"] == Decimal("714.00")
        assert totals["recurring_net"] == Decimal("600.00")
        assert totals["one_off_net"] == Decimal("0")

    def test_render_html(self, tenant, contract_with_items):
        service = OrderConfirmationService(tenant)
        html = service.render_html(
            contract_with_items,
            ab_number="AB-2026-0001",
            language="de",
        )
        assert "Auftragsbestätigung" in html
        assert "AB-2026-0001" in html
        assert "Test Customer" in html

    def test_render_html_english(self, tenant, contract_with_items):
        service = OrderConfirmationService(tenant)
        html = service.render_html(
            contract_with_items,
            ab_number="AB-2026-0001",
            language="en",
        )
        assert "Order Confirmation" in html

    def test_personal_message_in_pdf(self, tenant, contract_with_items):
        service = OrderConfirmationService(tenant)
        html = service.render_html(
            contract_with_items,
            personal_message="Welcome aboard!",
            include_message_in_pdf=True,
            language="de",
        )
        assert "Welcome aboard!" in html

    def test_personal_message_excluded_from_pdf(self, tenant, contract_with_items):
        service = OrderConfirmationService(tenant)
        html = service.render_html(
            contract_with_items,
            personal_message="Welcome aboard!",
            include_message_in_pdf=False,
            language="de",
        )
        assert "Welcome aboard!" not in html

    def test_create_order_confirmation(self, tenant, user, contract_with_items):
        service = OrderConfirmationService(tenant)
        with patch.object(service, 'generate_pdf', return_value=b'%PDF-fake'):
            ab = service.create_order_confirmation(
                contract=contract_with_items,
                user=user,
                personal_message="Hello!",
                additional_emails=["extra@acme.com"],
            )
        assert ab.order_confirmation_number == "AB-2026-0001"
        assert ab.status == OrderConfirmation.Status.DRAFT
        assert ab.personal_message == "Hello!"
        assert ab.additional_emails == ["extra@acme.com"]
        assert ab.pdf_file
        # Contract should now hold the same number (fix: persist before PDF render)
        contract_with_items.refresh_from_db()
        assert contract_with_items.order_confirmation_number == "AB-2026-0001"

    def test_create_order_confirmation_reuses_existing_contract_number(
        self, tenant, user, contract_with_items
    ):
        """Second OC creation should reuse the contract's number, not allocate a new one."""
        contract_with_items.order_confirmation_number = "AB-MANUAL-007"
        contract_with_items.save()

        service = OrderConfirmationService(tenant)
        with patch.object(service, 'generate_pdf', return_value=b'%PDF-fake'):
            ab = service.create_order_confirmation(
                contract=contract_with_items, user=user,
            )
        assert ab.order_confirmation_number == "AB-MANUAL-007"
        contract_with_items.refresh_from_db()
        assert contract_with_items.order_confirmation_number == "AB-MANUAL-007"

    def test_two_consecutive_oc_creations_share_number(
        self, tenant, user, contract_with_items
    ):
        """Re-creating an OC for the same contract uses the same number."""
        service = OrderConfirmationService(tenant)
        with patch.object(service, 'generate_pdf', return_value=b'%PDF-fake'):
            first = service.create_order_confirmation(
                contract=contract_with_items, user=user,
            )
            contract_with_items.refresh_from_db()
            second = service.create_order_confirmation(
                contract=contract_with_items, user=user,
            )
        assert first.order_confirmation_number == second.order_confirmation_number

    def test_get_email_template_default(self, tenant):
        service = OrderConfirmationService(tenant)
        template = service.get_email_template("de")
        assert "Auftragsbestätigung" in template["subject"]

    def test_get_email_template_custom(self, tenant):
        tenant.settings = {
            "ab_email_templates": {
                "de": {
                    "subject": "Custom AB {order_confirmation_number}",
                    "body": "Custom body",
                }
            }
        }
        tenant.save()
        service = OrderConfirmationService(tenant)
        template = service.get_email_template("de")
        assert template["subject"] == "Custom AB {order_confirmation_number}"

    @patch("apps.core.m365.send_mail")
    def test_send_order_confirmation(self, mock_send_mail, tenant, user, contract_with_items):
        mock_send_mail.return_value = "msg-123"
        service = OrderConfirmationService(tenant)

        with patch.object(service, 'generate_pdf', return_value=b'%PDF-fake'):
            ab = service.create_order_confirmation(
                contract=contract_with_items,
                user=user,
            )

        result = service.send_order_confirmation(ab)
        assert result is True
        ab.refresh_from_db()
        assert ab.status == OrderConfirmation.Status.SENT
        assert ab.sent_at is not None
        assert "billing@acme.com" in ab.sent_to
        assert ab.email_message_id == "msg-123"

    @patch("apps.core.m365.send_mail")
    def test_send_with_additional_emails(self, mock_send_mail, tenant, user, contract_with_items):
        mock_send_mail.return_value = "msg-456"
        service = OrderConfirmationService(tenant)

        with patch.object(service, 'generate_pdf', return_value=b'%PDF-fake'):
            ab = service.create_order_confirmation(
                contract=contract_with_items,
                user=user,
                additional_emails=["cfo@acme.com"],
            )

        service.send_order_confirmation(ab)
        call_kwargs = mock_send_mail.call_args
        recipients = call_kwargs.kwargs.get("to") or call_kwargs[1].get("to")
        assert "billing@acme.com" in recipients
        assert "cfo@acme.com" in recipients


# ---- Price Periods & Sections ----

class TestOrderConfirmationPricePeriods:
    """Tests for price period support, recurring/one-off sections, and interval labels."""

    def test_item_with_price_periods(self, tenant, contract, product):
        """Item with 2 price periods shows both in line items."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            description="Software License",
            quantity=1,
            unit_price=Decimal("100.00"),
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 4, 1),
            valid_to=date(2027, 3, 31),
            unit_price=Decimal("100.00"),
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2027, 4, 1),
            unit_price=Decimal("120.00"),
        )

        service = OrderConfirmationService(tenant)
        labels = AB_LABELS["de"]
        items = service._build_line_items(contract, labels)

        assert len(items) == 1
        assert items[0]["has_price_periods"] is True
        assert len(items[0]["price_periods"]) == 2
        assert items[0]["price_periods"][0]["unit_price"] == Decimal("100.00")
        assert items[0]["price_periods"][0]["valid_from"] == date(2026, 4, 1)
        assert items[0]["price_periods"][0]["valid_to"] == date(2027, 3, 31)
        assert items[0]["price_periods"][1]["unit_price"] == Decimal("120.00")
        assert items[0]["price_periods"][1]["valid_to"] is None
        # Amount uses first period price
        assert items[0]["amount"] == Decimal("100.00")

    def test_price_periods_in_html(self, tenant, contract, product):
        """Item with 2 price periods -> both date ranges visible in HTML."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            description="Software License",
            quantity=1,
            unit_price=Decimal("100.00"),
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 4, 1),
            valid_to=date(2027, 3, 31),
            unit_price=Decimal("100.00"),
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2027, 4, 1),
            unit_price=Decimal("120.00"),
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "01.04.2026" in html
        assert "31.03.2027" in html
        assert "01.04.2027" in html

    def test_mixed_recurring_and_one_off_sections(self, tenant, contract, product):
        """Mixed recurring + one-off items -> separate sections with headers."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            description="Monthly service",
            quantity=1,
            unit_price=Decimal("100.00"),
            is_one_off=False,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Setup fee",
            quantity=1,
            unit_price=Decimal("500.00"),
            is_one_off=True,
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "Wiederkehrende Leistungen" in html
        assert "Einmalige Leistungen" in html
        assert "Zwischensumme" in html

    def test_only_recurring_no_section_header(self, tenant, contract, product):
        """Only recurring items -> no section headers."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            is_one_off=False,
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "Wiederkehrende Leistungen" not in html
        assert "Einmalige Leistungen" not in html

    def test_only_one_off_no_section_header(self, tenant, contract):
        """Only one-off items -> no section headers."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="One-time setup",
            quantity=1,
            unit_price=Decimal("500.00"),
            is_one_off=True,
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "Wiederkehrende Leistungen" not in html
        assert "Einmalige Leistungen" not in html

    def test_interval_labels_annual(self, tenant, contract, product):
        """Annual price period -> '/Jahr' label."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1200.00"),
            price_period="annual",
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "/Jahr" in html

    def test_interval_labels_quarterly(self, tenant, contract, product):
        """Quarterly price period -> '/Quartal' label."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("300.00"),
            price_period="quarterly",
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "/Quartal" in html

    def test_interval_labels_english(self, tenant, contract, product):
        """English annual label -> '/year'."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1200.00"),
            price_period="annual",
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="en")
        assert "/year" in html

    def test_item_with_start_date(self, tenant, contract, product):
        """Item with custom start_date -> date shown in HTML."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("50.00"),
            start_date=date(2026, 6, 1),
        )

        service = OrderConfirmationService(tenant)
        html = service.render_html(contract, language="de")
        assert "01.06.2026" in html

    def test_totals_with_recurring_and_one_off(self, tenant):
        """Totals split recurring and one-off amounts."""
        service = OrderConfirmationService(tenant)
        items = [
            {"amount": Decimal("100.00"), "is_one_off": False},
            {"amount": Decimal("200.00"), "is_one_off": False},
            {"amount": Decimal("500.00"), "is_one_off": True},
        ]
        totals = service._build_totals(items, Decimal("19.00"))
        assert totals["recurring_net"] == Decimal("300.00")
        assert totals["one_off_net"] == Decimal("500.00")
        assert totals["net"] == Decimal("800.00")
        assert totals["tax_amount"] == Decimal("152.00")
        assert totals["gross"] == Decimal("952.00")

    def test_price_period_billing_interval_label(self, tenant, contract, product):
        """Price periods get their own billing_interval_label."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2027, 1, 1),
            unit_price=Decimal("110.00"),
            price_period="annual",
        )

        service = OrderConfirmationService(tenant)
        labels = AB_LABELS["de"]
        items = service._build_line_items(contract, labels)
        pp = items[0]["price_periods"]
        assert pp[0]["billing_interval_label"] == "/Monat"
        assert pp[1]["billing_interval_label"] == "/Jahr"

    def test_mixed_sections_html_subtotals(self, tenant, contract, product):
        """Mixed sections show subtotals in totals area."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            description="Monthly service",
            quantity=1,
            unit_price=Decimal("100.00"),
            is_one_off=False,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Setup fee",
            quantity=1,
            unit_price=Decimal("2000.00"),
            is_one_off=True,
        )

        service = OrderConfirmationService(tenant)
        ctx = service.build_template_context(contract, language="de")
        assert len(ctx["recurring_items"]) == 1
        assert len(ctx["one_off_items"]) == 1
        assert ctx["has_both_sections"] is True
        assert ctx["totals"]["recurring_net"] == Decimal("100.00")
        assert ctx["totals"]["one_off_net"] == Decimal("2000.00")


# ---- VAT classification ----


def _make_legal_data(tenant, country="Deutschland"):
    from apps.invoices.models import CompanyLegalData
    return CompanyLegalData.objects.create(
        tenant=tenant,
        company_name="Test GmbH",
        country=country,
        vat_id="DE123456789",
        managing_directors=["Max Mustermann"],
        default_tax_rate=Decimal("19.00"),
    )


class TestOrderConfirmationVat:
    """VAT must reflect the customer country, not always the default rate."""

    def _customer(self, tenant, country):
        return Customer.objects.create(
            tenant=tenant,
            name=f"Customer {country}",
            is_active=True,
            address={"country": country},
        )

    def _contract(self, tenant, customer):
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="VAT Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Service",
            quantity=1,
            unit_price=Decimal("100.00"),
        )
        return contract

    def test_domestic_customer_has_vat(self, tenant):
        """German customer (company in Germany) is charged 19% VAT."""
        _make_legal_data(tenant, country="Deutschland")
        customer = self._customer(tenant, "Deutschland")
        contract = self._contract(tenant, customer)

        ctx = OrderConfirmationService(tenant).build_template_context(contract)

        assert ctx["totals"]["tax_rate"] == Decimal("19.00")
        assert ctx["totals"]["tax_amount"] == Decimal("19.00")
        assert ctx["totals"]["gross"] == Decimal("119.00")
        assert ctx["vat_sentence"] == ""

    def test_eu_customer_reverse_charge(self, tenant):
        """EU customer gets 0% VAT and a reverse-charge note."""
        _make_legal_data(tenant, country="Deutschland")
        customer = self._customer(tenant, "France")
        contract = self._contract(tenant, customer)

        ctx = OrderConfirmationService(tenant).build_template_context(contract)

        assert ctx["totals"]["tax_amount"] is None
        assert ctx["totals"]["gross"] == Decimal("100.00")
        assert "Reverse Charge" in ctx["vat_sentence"]

    def test_non_eu_customer_no_vat(self, tenant):
        """Non-EU (third country) customer gets 0% VAT and a place-of-supply note."""
        _make_legal_data(tenant, country="Deutschland")
        customer = self._customer(tenant, "United States")
        contract = self._contract(tenant, customer)

        ctx = OrderConfirmationService(tenant).build_template_context(contract)

        assert ctx["totals"]["tax_amount"] is None
        assert ctx["totals"]["gross"] == Decimal("100.00")
        assert ctx["vat_sentence"]
        assert "Reverse Charge" not in ctx["vat_sentence"]

    def test_eu_note_hidden_tax_row_in_html(self, tenant):
        """Reverse-charge HTML omits the tax row and shows the VAT note."""
        _make_legal_data(tenant, country="Deutschland")
        customer = self._customer(tenant, "France")
        contract = self._contract(tenant, customer)

        html = OrderConfirmationService(tenant).render_html(contract, language="de")

        assert "Reverse Charge" in html


# ---- Model ----

class TestOrderConfirmationModel:
    def test_create(self, tenant, contract):
        ab = OrderConfirmation.objects.create(
            tenant=tenant,
            contract=contract,
            order_confirmation_number="AB-2026-0001",
        )
        assert str(ab) == "AB AB-2026-0001 for Test Contract (Test Customer)"
        assert ab.status == OrderConfirmation.Status.DRAFT

    def test_defaults(self, tenant, contract):
        ab = OrderConfirmation.objects.create(
            tenant=tenant,
            contract=contract,
        )
        assert ab.include_message_in_pdf is True
        assert ab.include_message_in_email is True
        assert ab.additional_emails == []
        assert ab.sent_to == []
        assert ab.language == "de"
