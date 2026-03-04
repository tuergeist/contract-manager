"""Tests for order confirmation (Auftragsbestätigung) feature."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.contracts.models import Contract, ContractItem, OrderConfirmation, OrderConfirmationNumberScheme
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
        items = service._build_line_items(contract_with_items)
        assert len(items) == 2
        assert items[0]["product_name"] == "Test Product"
        assert items[0]["amount"] == Decimal("100.00")
        assert items[1]["amount"] == Decimal("500.00")

    def test_build_totals(self, tenant):
        service = OrderConfirmationService(tenant)
        items = [
            {"amount": Decimal("100.00")},
            {"amount": Decimal("500.00")},
        ]
        totals = service._build_totals(items, Decimal("19.00"))
        assert totals["net"] == Decimal("600.00")
        assert totals["tax_amount"] == Decimal("114.00")
        assert totals["gross"] == Decimal("714.00")

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


# ---- Model ----

class TestOrderConfirmationModel:
    def test_create(self, tenant, contract):
        ab = OrderConfirmation.objects.create(
            tenant=tenant,
            contract=contract,
            order_confirmation_number="AB-2026-0001",
        )
        assert str(ab) == "AB AB-2026-0001 for Test Contract"
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
