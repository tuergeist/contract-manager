"""Tests for offer numbering, service, status transitions, and model logic."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import CompanyLegalData
from apps.offers.models import OfferNumberScheme, OfferRecord
from apps.offers.numbering import OfferNumberService
from apps.offers.schema import _convert_offer_record, _VALID_TRANSITIONS
from apps.products.models import Product


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def numbering_service(tenant):
    return OfferNumberService(tenant)


@pytest.fixture
def customer(db, tenant):
    """Create a domestic test customer."""
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer GmbH",
        address={"street": "Musterstraße 1", "city": "Berlin", "country": "Deutschland"},
        is_active=True,
    )


@pytest.fixture
def eu_customer(db, tenant):
    """Create an EU customer for VAT-exempt offers."""
    return Customer.objects.create(
        tenant=tenant,
        name="EU Customer BV",
        address={"street": "Keizersgracht 1", "city": "Amsterdam", "country": "Netherlands"},
        vat_id="NL123456789B01",
        is_active=True,
    )


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Test Product",
        sku="TP-001",
    )


@pytest.fixture
def legal_data(db, tenant):
    """Create company legal data required for offer generation."""
    return CompanyLegalData.objects.create(
        tenant=tenant,
        company_name="Acme GmbH",
        street="Hauptstraße 1",
        zip_code="10115",
        city="Berlin",
        country="Deutschland",
        tax_number="27/123/45678",
        vat_id="DE123456789",
        default_tax_rate=Decimal("19.00"),
        bank_name="Deutsche Bank",
        iban="DE89370400440532013000",
        bic="DEUTDEDB",
    )


@pytest.fixture
def monthly_contract(db, tenant, customer):
    """Active monthly contract starting Jan 2026."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Monthly SaaS",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def draft_contract(db, tenant, customer):
    """Draft monthly contract."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Draft Contract",
        status=Contract.Status.DRAFT,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_with_items(db, tenant, monthly_contract, product):
    """Monthly contract with two items."""
    ContractItem.objects.create(
        tenant=tenant,
        contract=monthly_contract,
        product=product,
        quantity=2,
        unit_price=Decimal("100.00"),
    )
    ContractItem.objects.create(
        tenant=tenant,
        contract=monthly_contract,
        description="Consulting",
        quantity=1,
        unit_price=Decimal("500.00"),
    )
    return monthly_contract


@pytest.fixture
def draft_offer(db, tenant, customer, monthly_contract):
    """A draft offer record."""
    return OfferRecord.objects.create(
        tenant=tenant,
        contract=monthly_contract,
        customer=customer,
        offer_number="2026-0001",
        offer_date=date(2026, 2, 1),
        valid_until=date(2026, 3, 3),
        billing_date=date(2026, 2, 1),
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        total_net=Decimal("700.00"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("133.00"),
        total_gross=Decimal("833.00"),
        line_items_snapshot=[
            {"product_name": "Test Product", "quantity": 2, "unit_price": "100.00", "amount": "200.00"},
            {"description": "Consulting", "quantity": 1, "unit_price": "500.00", "amount": "500.00"},
        ],
        company_data_snapshot={"company_name": "Acme GmbH"},
        status=OfferRecord.Status.DRAFT,
        customer_name="Test Customer GmbH",
        contract_name="Monthly SaaS",
    )


@pytest.fixture
def sent_offer(db, draft_offer):
    """A sent offer record."""
    draft_offer.status = OfferRecord.Status.SENT
    draft_offer.save(update_fields=["status"])
    return draft_offer


# =========================================================================
# 6.1 - OfferNumberService Tests
# =========================================================================


class TestOfferNumberServiceFormatting:
    """Test pattern placeholder resolution."""

    def test_yyyy_placeholder(self, numbering_service):
        result = OfferNumberService._format_number(
            "A-{YYYY}-{NNNN}", date(2026, 3, 15), 1
        )
        assert result == "A-2026-0001"

    def test_yy_and_mm_placeholder(self, numbering_service):
        result = OfferNumberService._format_number(
            "OFF/{YY}/{MM}/{NNN}", date(2026, 11, 1), 42
        )
        assert result == "OFF/26/11/042"

    def test_5_digit_counter(self, numbering_service):
        result = OfferNumberService._format_number(
            "{YYYY}-{NNNNN}", date(2026, 1, 1), 7
        )
        assert result == "2026-00007"


class TestOfferNumberServiceSequential:
    """Test sequential number generation."""

    def test_first_number_uses_default_pattern(self, db, numbering_service):
        number = numbering_service.get_next_number(date(2026, 1, 15))
        assert number == "2026-0001"

    def test_sequential_increment(self, db, numbering_service):
        n1 = numbering_service.get_next_number(date(2026, 1, 1))
        n2 = numbering_service.get_next_number(date(2026, 1, 2))
        n3 = numbering_service.get_next_number(date(2026, 1, 3))
        assert n1 == "2026-0001"
        assert n2 == "2026-0002"
        assert n3 == "2026-0003"

    def test_custom_pattern_and_start_counter(self, db, tenant):
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="A-{YYYY}-{NNNN}",
            next_counter=100,
            reset_period=OfferNumberScheme.ResetPeriod.NEVER,
        )
        service = OfferNumberService(tenant)
        number = service.get_next_number(date(2026, 5, 1))
        assert number == "A-2026-0100"


class TestOfferNumberServiceReset:
    """Test counter reset logic."""

    def test_yearly_reset_new_year(self, db, tenant):
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
            next_counter=50,
            reset_period=OfferNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=2025,
            last_reset_month=12,
        )
        service = OfferNumberService(tenant)
        number = service.get_next_number(date(2026, 1, 1))
        assert number == "2026-0001"

    def test_no_reset_same_year(self, db, tenant):
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
            next_counter=50,
            reset_period=OfferNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=2026,
            last_reset_month=1,
        )
        service = OfferNumberService(tenant)
        number = service.get_next_number(date(2026, 6, 1))
        assert number == "2026-0050"

    def test_monthly_reset(self, db, tenant):
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}/{MM}-{NNN}",
            next_counter=25,
            reset_period=OfferNumberScheme.ResetPeriod.MONTHLY,
            last_reset_year=2026,
            last_reset_month=1,
        )
        service = OfferNumberService(tenant)
        number = service.get_next_number(date(2026, 2, 1))
        assert number == "2026/02-001"

    def test_never_reset(self, db, tenant):
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="{NNNN}",
            next_counter=999,
            reset_period=OfferNumberScheme.ResetPeriod.NEVER,
            last_reset_year=2020,
            last_reset_month=1,
        )
        service = OfferNumberService(tenant)
        number = service.get_next_number(date(2026, 12, 1))
        assert number == "0999"


class TestOfferNumberServiceDefault:
    """Test default scheme creation and preview."""

    def test_creates_default_scheme(self, db, tenant):
        assert not OfferNumberScheme.objects.filter(tenant=tenant).exists()
        service = OfferNumberService(tenant)
        number = service.get_next_number(date(2026, 1, 1))
        assert number == "2026-0001"
        scheme = OfferNumberScheme.objects.get(tenant=tenant)
        assert scheme.pattern == "{YYYY}-{NNNN}"
        assert scheme.reset_period == OfferNumberScheme.ResetPeriod.YEARLY

    def test_preview_does_not_increment(self, db, tenant):
        service = OfferNumberService(tenant)
        preview = service.preview_next_number(date(2026, 3, 15))
        assert preview == "2026-0001"
        scheme = OfferNumberScheme.objects.get(tenant=tenant)
        assert scheme.next_counter == 1


class TestOfferPatternValidation:
    """Test pattern validation."""

    def test_valid_pattern(self):
        errors = OfferNumberService.validate_pattern("A-{YYYY}-{NNNN}")
        assert errors == []

    def test_missing_counter(self):
        errors = OfferNumberService.validate_pattern("A-{YYYY}-{MM}")
        assert len(errors) == 1
        assert "counter placeholder" in errors[0]

    def test_empty_pattern(self):
        errors = OfferNumberService.validate_pattern("")
        assert len(errors) == 1

    def test_unknown_placeholder(self):
        errors = OfferNumberService.validate_pattern("{INVALID}-{NNNN}")
        assert any("Unknown placeholder" in e for e in errors)


# =========================================================================
# 6.2 - OfferService.create_offer Tests
# =========================================================================


class TestOfferServiceCreateOffer:
    """Test offer creation from contract billing events."""

    @patch("apps.offers.services.HTML")
    def test_creates_offer_with_correct_amounts(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """Test that an offer is created with correct line items and amounts."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        record = service.create_offer(
            contract_id=contract_with_items.id,
            billing_date=date(2026, 1, 1),
        )

        assert isinstance(record, OfferRecord)
        assert record.status == OfferRecord.Status.DRAFT
        assert record.customer_name == "Test Customer GmbH"
        assert record.contract_name == "Monthly SaaS"
        assert record.billing_date == date(2026, 1, 1)
        # 2 * 100 + 1 * 500 = 700
        assert record.total_net == Decimal("700.00")
        assert record.tax_rate == Decimal("19.00")
        assert record.tax_amount == Decimal("133.00")
        assert record.total_gross == Decimal("833.00")
        assert len(record.line_items_snapshot) == 2

    @patch("apps.offers.services.HTML")
    def test_assigns_sequential_offer_number(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """Test that offer numbers are assigned sequentially."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        r1 = service.create_offer(contract_with_items.id, date(2026, 1, 1))
        r2 = service.create_offer(contract_with_items.id, date(2026, 2, 1))

        assert r1.offer_number == "2026-0001"
        assert r2.offer_number == "2026-0002"

    @patch("apps.offers.services.HTML")
    def test_retries_on_duplicate_offer_number(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """If the scheme counter is behind existing records, create_offer
        retries until it finds a free number rather than raising."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        # Seed the scheme so the next generated number is 0001, but also
        # create an OfferRecord that already occupies 0001 — this is the
        # exact state the bug report described (deleted-then-recreated /
        # stale scheme counter).
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
            next_counter=1,
            reset_period=OfferNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=2026,
        )
        OfferRecord.objects.create(
            tenant=tenant,
            contract=contract_with_items,
            customer=contract_with_items.customer,
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
            customer_name="Test Customer GmbH",
            contract_name="Monthly SaaS",
        )

        service = OfferService(tenant)
        record = service.create_offer(contract_with_items.id, date(2026, 1, 1))

        # Should land on the next free number, not raise IntegrityError.
        assert record.offer_number == "2026-0002"

    @patch("apps.offers.services.HTML")
    def test_snapshots_company_data(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """Test that company data is snapshotted into the record."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        record = service.create_offer(contract_with_items.id, date(2026, 1, 1))

        assert record.company_data_snapshot["company_name"] == "Acme GmbH"
        assert record.company_data_snapshot["vat_id"] == "DE123456789"

    @patch("apps.offers.services.HTML")
    def test_domestic_customer_has_tax(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """Domestic customer gets 19% VAT."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        record = service.create_offer(contract_with_items.id, date(2026, 1, 1))

        assert record.tax_rate == Decimal("19.00")
        assert record.tax_amount > Decimal("0")

    @patch("apps.offers.services.HTML")
    def test_eu_customer_zero_tax(
        self, mock_html, tenant, eu_customer, product, legal_data
    ):
        """EU customer gets 0% VAT with reverse charge sentence."""
        from apps.offers.services import OfferService

        contract = Contract.objects.create(
            tenant=tenant,
            customer=eu_customer,
            name="EU Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
        )

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        record = service.create_offer(contract.id, date(2026, 1, 1))

        assert record.tax_rate == Decimal("0.00")
        assert record.tax_amount == Decimal("0.00")
        assert record.total_net == record.total_gross
        assert record.vat_sentence != ""

    @patch("apps.offers.services.HTML")
    def test_generates_pdf_file(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """Test that a PDF file is saved on the record."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        record = service.create_offer(contract_with_items.id, date(2026, 1, 1))

        assert record.pdf_file
        assert record.pdf_file.name

    def test_raises_without_legal_data(self, tenant, contract_with_items):
        """Creating an offer without company legal data raises ValueError."""
        from apps.offers.services import OfferService

        service = OfferService(tenant)
        with pytest.raises(ValueError, match="Company legal data"):
            service.create_offer(contract_with_items.id, date(2026, 1, 1))

    def test_raises_for_invalid_billing_date(
        self, tenant, contract_with_items, legal_data
    ):
        """Creating an offer for a date with no billing event raises ValueError."""
        from apps.offers.services import OfferService

        service = OfferService(tenant)
        # 2025-06-15 is before the contract start_date, so no event
        with pytest.raises(ValueError, match="No billing event found"):
            service.create_offer(contract_with_items.id, date(2025, 6, 15))

    @patch("apps.offers.services.HTML")
    def test_calculates_period_correctly(
        self, mock_html, tenant, contract_with_items, legal_data
    ):
        """Test that period_start and period_end are calculated for monthly billing."""
        from apps.offers.services import OfferService

        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"

        service = OfferService(tenant)
        record = service.create_offer(contract_with_items.id, date(2026, 3, 1))

        assert record.period_start == date(2026, 3, 1)
        assert record.period_end == date(2026, 3, 31)


# =========================================================================
# 6.3 - Status Transition Tests
# =========================================================================


class TestOfferStatusTransitions:
    """Test valid and invalid status transitions."""

    def test_valid_transitions_from_draft(self):
        assert _VALID_TRANSITIONS["draft"] == {"sent", "cancelled"}

    def test_valid_transitions_from_sent(self):
        assert _VALID_TRANSITIONS["sent"] == {"accepted", "rejected", "cancelled"}

    def test_no_transitions_from_accepted(self):
        assert "accepted" not in _VALID_TRANSITIONS

    def test_no_transitions_from_rejected(self):
        assert "rejected" not in _VALID_TRANSITIONS

    def test_no_transitions_from_cancelled(self):
        assert "cancelled" not in _VALID_TRANSITIONS

    def test_draft_to_sent(self, db, draft_offer):
        draft_offer.status = OfferRecord.Status.SENT
        draft_offer.save(update_fields=["status"])
        draft_offer.refresh_from_db()
        assert draft_offer.status == OfferRecord.Status.SENT

    def test_draft_to_cancelled(self, db, draft_offer):
        draft_offer.status = OfferRecord.Status.CANCELLED
        draft_offer.save(update_fields=["status"])
        draft_offer.refresh_from_db()
        assert draft_offer.status == OfferRecord.Status.CANCELLED

    def test_sent_to_accepted(self, db, sent_offer):
        sent_offer.status = OfferRecord.Status.ACCEPTED
        sent_offer.save(update_fields=["status"])
        sent_offer.refresh_from_db()
        assert sent_offer.status == OfferRecord.Status.ACCEPTED

    def test_sent_to_rejected(self, db, sent_offer):
        sent_offer.status = OfferRecord.Status.REJECTED
        sent_offer.save(update_fields=["status"])
        sent_offer.refresh_from_db()
        assert sent_offer.status == OfferRecord.Status.REJECTED

    def test_sent_to_cancelled(self, db, sent_offer):
        sent_offer.status = OfferRecord.Status.CANCELLED
        sent_offer.save(update_fields=["status"])
        sent_offer.refresh_from_db()
        assert sent_offer.status == OfferRecord.Status.CANCELLED

    def test_invalid_transition_draft_to_accepted(self):
        """The schema validation prevents draft → accepted."""
        assert "accepted" not in _VALID_TRANSITIONS.get("draft", set())

    def test_invalid_transition_sent_to_draft(self):
        """Cannot go back from sent to draft."""
        assert "draft" not in _VALID_TRANSITIONS.get("sent", set())


# =========================================================================
# 6.4 - Query / Model Tests
# =========================================================================


class TestOfferRecordModel:
    """Test OfferRecord model behavior."""

    def test_unique_offer_number_per_tenant(self, db, tenant, customer, monthly_contract):
        """Duplicate offer numbers in the same tenant should fail."""
        base_fields = dict(
            tenant=tenant,
            contract=monthly_contract,
            customer=customer,
            offer_number="DUP-001",
            offer_date=date(2026, 1, 1),
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("19.00"),
            total_gross=Decimal("119.00"),
            line_items_snapshot=[],
            company_data_snapshot={},
            customer_name="Test",
            contract_name="Test",
        )
        OfferRecord.objects.create(**base_fields)
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            OfferRecord.objects.create(**base_fields)

    def test_default_ordering(self, db, tenant, customer, monthly_contract):
        """Records are ordered by -offer_date, -created_at."""
        base = dict(
            tenant=tenant,
            contract=monthly_contract,
            customer=customer,
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total_gross=Decimal("100.00"),
            line_items_snapshot=[],
            company_data_snapshot={},
            customer_name="Test",
            contract_name="Test",
        )
        r1 = OfferRecord.objects.create(
            **base, offer_number="O-001", offer_date=date(2026, 1, 1)
        )
        r2 = OfferRecord.objects.create(
            **base, offer_number="O-002", offer_date=date(2026, 2, 1)
        )
        records = list(OfferRecord.objects.filter(tenant=tenant))
        assert records[0].id == r2.id
        assert records[1].id == r1.id

    def test_customer_set_null_on_delete(self, db, tenant, customer, monthly_contract, draft_offer):
        """Deleting a customer sets the offer FK to null, preserves frozen name."""
        # Must remove contract first (Contract.customer is PROTECTED)
        draft_offer.contract = None
        draft_offer.save(update_fields=["contract"])
        monthly_contract.delete()
        customer.delete()
        draft_offer.refresh_from_db()
        assert draft_offer.customer is None
        assert draft_offer.customer_name == "Test Customer GmbH"  # frozen name preserved

    def test_contract_set_null_on_delete(self, db, tenant, monthly_contract, draft_offer):
        """Deleting a contract sets the FK to null, preserves offer."""
        monthly_contract.delete()
        draft_offer.refresh_from_db()
        assert draft_offer.contract is None
        assert draft_offer.contract_name == "Monthly SaaS"  # frozen name preserved

    def test_str_representation(self, draft_offer):
        assert "2026-0001" in str(draft_offer)
        assert "Test Customer GmbH" in str(draft_offer)


class TestOfferTenantIsolation:
    """Test that offers are scoped to tenants."""

    def test_offers_isolated_by_tenant(self, db, tenant, customer, monthly_contract):
        from apps.tenants.models import Tenant

        other_tenant = Tenant.objects.create(name="Other Tenant", currency="USD")
        base = dict(
            billing_date=date(2026, 1, 1),
            offer_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total_gross=Decimal("100.00"),
            line_items_snapshot=[],
            company_data_snapshot={},
            customer_name="Test",
            contract_name="Test",
        )
        OfferRecord.objects.create(
            tenant=tenant,
            contract=monthly_contract,
            customer=customer,
            offer_number="T1-001",
            **base,
        )
        OfferRecord.objects.create(
            tenant=other_tenant,
            offer_number="T2-001",
            **base,
        )

        tenant_offers = OfferRecord.objects.filter(tenant=tenant)
        other_offers = OfferRecord.objects.filter(tenant=other_tenant)
        assert tenant_offers.count() == 1
        assert other_offers.count() == 1
        assert tenant_offers.first().offer_number == "T1-001"


# =========================================================================
# 6.5 - GraphQL Conversion & Delete Logic Tests
# =========================================================================


class TestOfferGraphQLConversion:
    """Test the _convert_offer_record helper."""

    def test_converts_all_fields(self, db, draft_offer):
        gql_offer = _convert_offer_record(draft_offer)
        assert gql_offer.id == draft_offer.id
        assert gql_offer.offer_number == "2026-0001"
        assert gql_offer.customer_name == "Test Customer GmbH"
        assert gql_offer.contract_name == "Monthly SaaS"
        assert gql_offer.status == "draft"
        assert gql_offer.total_net == Decimal("700.00")
        assert gql_offer.total_gross == Decimal("833.00")
        assert gql_offer.billing_date == date(2026, 2, 1)
        assert gql_offer.notes == ""
        assert isinstance(gql_offer.line_items_snapshot, list)
        assert len(gql_offer.line_items_snapshot) == 2

    def test_handles_null_customer(self, db, tenant, monthly_contract, draft_offer):
        """When customer is deleted, conversion should not fail."""
        draft_offer.customer = None
        draft_offer.save(update_fields=["customer"])
        gql_offer = _convert_offer_record(draft_offer)
        assert gql_offer.customer_id is None
        assert gql_offer.customer_billing_emails == []

    def test_handles_email_sent_fields(self, db, draft_offer):
        from django.utils import timezone

        now = timezone.now()
        draft_offer.email_sent_at = now
        draft_offer.email_sent_to = ["a@b.com", "c@d.com"]
        draft_offer.email_message_id = "msg-123"
        draft_offer.save()
        gql_offer = _convert_offer_record(draft_offer)
        assert gql_offer.email_sent_at is not None
        assert gql_offer.email_sent_to == ["a@b.com", "c@d.com"]
        assert gql_offer.email_message_id == "msg-123"


class TestOfferDeleteLogic:
    """Test draft-only delete constraint."""

    def test_can_delete_draft_offer(self, db, draft_offer):
        offer_id = draft_offer.id
        draft_offer.delete()
        assert not OfferRecord.objects.filter(id=offer_id).exists()

    def test_sent_offer_still_deletable_at_model_level(self, db, sent_offer):
        """Model doesn't enforce delete restrictions, schema does."""
        offer_id = sent_offer.id
        sent_offer.delete()
        assert not OfferRecord.objects.filter(id=offer_id).exists()


class TestOfferNumberSchemeModel:
    """Test OfferNumberScheme model."""

    def test_one_scheme_per_tenant(self, db, tenant):
        OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
        )
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            OfferNumberScheme.objects.create(
                tenant=tenant,
                pattern="A-{NNNN}",
            )

    def test_str_representation(self, db, tenant):
        scheme = OfferNumberScheme.objects.create(
            tenant=tenant,
            pattern="A-{YYYY}-{NNNN}",
        )
        assert "Test Company" in str(scheme)
        assert "A-{YYYY}-{NNNN}" in str(scheme)

    def test_default_values(self, db, tenant):
        scheme = OfferNumberScheme.objects.create(tenant=tenant)
        assert scheme.pattern == "{YYYY}-{NNNN}"
        assert scheme.next_counter == 1
        assert scheme.reset_period == OfferNumberScheme.ResetPeriod.YEARLY


# =========================================================================
# Scoped Offer Creation Tests
# =========================================================================


class TestScopedOfferCreation:
    """Tests for creating offers scoped to specific contract items."""

    @patch("apps.offers.services.OfferService._generate_and_save_pdf")
    def test_scoped_offer_includes_only_specified_items(
        self, mock_pdf, tenant, contract_with_items, legal_data
    ):
        from apps.offers.services import OfferService

        items = list(contract_with_items.items.all())
        first_item = items[0]

        service = OfferService(tenant)
        record = service.create_offer(
            contract_with_items.id,
            date(2026, 1, 1),
            item_ids=[first_item.id],
        )

        assert len(record.line_items_snapshot) == 1
        assert record.line_items_snapshot[0]["item_id"] == first_item.id
        assert record.scoped_item_ids == [first_item.id]

    @patch("apps.offers.services.OfferService._generate_and_save_pdf")
    def test_scoped_offer_totals_only_scoped_items(
        self, mock_pdf, tenant, contract_with_items, legal_data
    ):
        from apps.offers.services import OfferService

        items = list(contract_with_items.items.all())
        first_item = items[0]  # 2 x 100 = 200

        service = OfferService(tenant)
        record = service.create_offer(
            contract_with_items.id,
            date(2026, 1, 1),
            item_ids=[first_item.id],
        )

        assert record.total_net == Decimal("200.00")

    @patch("apps.offers.services.OfferService._generate_and_save_pdf")
    def test_unscoped_offer_includes_all_items(
        self, mock_pdf, tenant, contract_with_items, legal_data
    ):
        from apps.offers.services import OfferService

        service = OfferService(tenant)
        record = service.create_offer(
            contract_with_items.id,
            date(2026, 1, 1),
        )

        assert len(record.line_items_snapshot) == 2
        assert record.scoped_item_ids is None
        assert record.total_net == Decimal("700.00")

    @patch("apps.offers.services.OfferService._generate_and_save_pdf")
    def test_scoped_item_ids_stored_on_record(
        self, mock_pdf, tenant, contract_with_items, legal_data
    ):
        from apps.offers.services import OfferService

        items = list(contract_with_items.items.all())
        item_ids = [items[0].id, items[1].id]

        service = OfferService(tenant)
        record = service.create_offer(
            contract_with_items.id,
            date(2026, 1, 1),
            item_ids=item_ids,
        )

        assert record.scoped_item_ids == item_ids
