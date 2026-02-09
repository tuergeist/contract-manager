"""Tests for invoice generation: persistence, tax, duplicate prevention, cancellation."""
import pytest
from datetime import date
from decimal import Decimal

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import CompanyLegalData, InvoiceRecord
from apps.invoices.services import InvoiceService
from apps.products.models import Product


@pytest.fixture
def legal_data(db, tenant):
    """Create company legal data for the tenant."""
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
        managing_directors=["Max Mustermann"],
        bank_name="Deutsche Bank",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        default_tax_rate=Decimal("19.00"),
    )


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="Acme Corp",
        address={"street": "Hauptstraße 1", "city": "Berlin", "zip": "10115"},
        is_active=True,
    )


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="SaaS License",
        sku="SAAS-001",
    )


@pytest.fixture
def active_contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="SaaS Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_item(db, active_contract, product):
    return ContractItem.objects.create(
        contract=active_contract,
        product=product,
        tenant=active_contract.tenant,
        quantity=1,
        unit_price=Decimal("1000.00"),
        billing_start_date=date(2026, 1, 1),
    )


class TestTaxCalculation:
    def test_standard_rate(self):
        tax, gross = InvoiceService.calculate_tax(
            Decimal("1000.00"), Decimal("19.00")
        )
        assert tax == Decimal("190.00")
        assert gross == Decimal("1190.00")

    def test_reduced_rate(self):
        tax, gross = InvoiceService.calculate_tax(
            Decimal("100.00"), Decimal("7.00")
        )
        assert tax == Decimal("7.00")
        assert gross == Decimal("107.00")

    def test_zero_rate(self):
        tax, gross = InvoiceService.calculate_tax(
            Decimal("500.00"), Decimal("0.00")
        )
        assert tax == Decimal("0.00")
        assert gross == Decimal("500.00")

    def test_rounding(self):
        tax, gross = InvoiceService.calculate_tax(
            Decimal("33.33"), Decimal("19.00")
        )
        assert tax == Decimal("6.33")
        assert gross == Decimal("39.66")


class TestGenerateAndPersist:
    def test_generates_invoices(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        assert len(records) == 1
        record = records[0]
        assert record.invoice_number == "2026-0001"
        assert record.status == InvoiceRecord.Status.FINALIZED
        assert record.total_net == Decimal("1000.00")
        assert record.tax_rate == Decimal("19.00")
        assert record.tax_amount == Decimal("190.00")
        assert record.total_gross == Decimal("1190.00")
        assert record.customer_name == "Acme Corp"
        assert record.contract_name == "SaaS Contract"

    def test_line_items_snapshot(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        snapshot = records[0].line_items_snapshot
        assert len(snapshot) == 1
        assert snapshot[0]["product_name"] == "SaaS License"
        assert snapshot[0]["unit_price"] == "1000.00"

    def test_company_data_snapshot(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        snapshot = records[0].company_data_snapshot
        assert snapshot["company_name"] == "Test GmbH"
        assert snapshot["vat_id"] == "DE123456789"
        assert snapshot["commercial_register_number"] == "HRB 12345"

    def test_requires_legal_data(self, db, tenant, active_contract, contract_item):
        service = InvoiceService(tenant)
        with pytest.raises(ValueError, match="Company legal data"):
            service.generate_and_persist(2026, 1)

    def test_empty_month(self, db, tenant, legal_data):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 6)
        assert records == []


class TestDuplicatePrevention:
    def test_skips_existing_finalized(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        first = service.generate_and_persist(2026, 1)
        assert len(first) == 1

        # Second call should skip the already-generated invoice
        second = service.generate_and_persist(2026, 1)
        assert len(second) == 0

        # Only one record should exist
        assert InvoiceRecord.objects.filter(tenant=tenant).count() == 1

    def test_generates_for_new_contracts(
        self, db, tenant, legal_data, customer, active_contract, contract_item, product
    ):
        service = InvoiceService(tenant)
        service.generate_and_persist(2026, 1)

        # Add a new contract
        new_contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="New Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            contract=new_contract,
            product=product,
            tenant=tenant,
            quantity=2,
            unit_price=Decimal("500.00"),
            billing_start_date=date(2026, 1, 1),
        )

        second = service.generate_and_persist(2026, 1)
        assert len(second) == 1
        assert second[0].contract_name == "New Contract"
        assert InvoiceRecord.objects.filter(tenant=tenant).count() == 2


class TestCancelInvoice:
    def test_cancel_finalized(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]

        InvoiceService.cancel_invoice(record)
        record.refresh_from_db()
        assert record.status == InvoiceRecord.Status.CANCELLED

    def test_cancel_non_finalized_raises(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]
        record.status = InvoiceRecord.Status.CANCELLED
        record.save()

        with pytest.raises(ValueError, match="Only finalized"):
            InvoiceService.cancel_invoice(record)

    def test_cancelled_number_not_reused(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        old_number = records[0].invoice_number
        InvoiceService.cancel_invoice(records[0])

        # Generate again for the same month — cancelled record should allow re-generation
        # but with a NEW number
        records[0].refresh_from_db()
        new_records = service.generate_and_persist(2026, 1)
        assert len(new_records) == 1
        assert new_records[0].invoice_number != old_number


class TestGetPersistedInvoices:
    def test_returns_invoices_for_month(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        service.generate_and_persist(2026, 1)

        results = service.get_persisted_invoices(2026, 1)
        assert len(results) == 1

        # Different month returns empty
        results = service.get_persisted_invoices(2026, 2)
        assert len(results) == 0

    def test_filter_by_status(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        service.generate_and_persist(2026, 1)

        results = service.get_persisted_invoices(2026, 1, status="finalized")
        assert len(results) == 1

        results = service.get_persisted_invoices(2026, 1, status="cancelled")
        assert len(results) == 0
