"""Tests for invoice generation: persistence, tax, duplicate prevention, voiding, queries."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import Contract, ContractItem
from apps.core.context import Context
from apps.customers.models import Customer
from apps.invoices.models import CompanyLegalData, InvoiceRecord
from apps.invoices.services import InvoiceService
from apps.products.models import Product
from apps.tenants.models import Role, Tenant, User


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
        address={"street": "Hauptstraße 1", "city": "Berlin", "zip": "10115", "country": "Deutschland"},
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


class TestVoidInvoice:
    def test_void_finalized(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]

        storno = service.void_invoice(record, reason="Test void reason")
        record.refresh_from_db()
        assert record.status == InvoiceRecord.Status.VOIDED
        assert record.void_reason == "Test void reason"

        # Verify storno record created
        assert storno is not None
        assert storno.document_type == "storno"
        assert storno.storno_of_id == record.id
        assert storno.status == InvoiceRecord.Status.FINALIZED
        assert storno.total_gross == record.total_gross
        assert storno.invoice_number.startswith("S-")

    def test_void_sent(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]
        record.status = InvoiceRecord.Status.SENT
        record.save()

        storno = service.void_invoice(record, reason="Error in sent invoice")
        record.refresh_from_db()
        assert record.status == InvoiceRecord.Status.VOIDED
        assert storno.document_type == "storno"

    def test_void_non_finalized_raises(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]
        record.status = InvoiceRecord.Status.VOIDED
        record.save()

        with pytest.raises(ValueError, match="Only finalized or sent"):
            service.void_invoice(record, reason="Should fail")

    def test_void_storno_raises(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        storno = service.void_invoice(records[0], reason="Void it")

        with pytest.raises(ValueError, match="Storno documents cannot be voided"):
            service.void_invoice(storno, reason="Should fail")

    def test_voided_number_not_reused(self, db, tenant, legal_data, active_contract, contract_item):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        old_number = records[0].invoice_number
        service.void_invoice(records[0], reason="Reissue needed")

        # Generate again for the same month — voided record should allow re-generation
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

        results = service.get_persisted_invoices(2026, 1, status="voided")
        assert len(results) == 0


class TestInvoiceRecordQuery:
    """Test the invoice_record GraphQL query."""

    QUERY = """
        query InvoiceRecord($id: Int!) {
            invoiceRecord(id: $id) {
                id
                invoiceNumber
                contractName
                customerName
                status
            }
        }
    """

    @pytest.fixture
    def admin_user(self, db, tenant):
        u = User.objects.create_user(
            email="admin-inv@test.local", password="pass", tenant=tenant
        )
        admin_role = Role.objects.get(tenant=tenant, name="Admin")
        u.roles.add(admin_role)
        return u

    def _ctx(self, user):
        return Context(request=Mock(), user=user)

    def test_returns_record_for_valid_id(
        self, db, tenant, legal_data, active_contract, contract_item, admin_user
    ):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]

        result = schema.execute_sync(
            self.QUERY, variable_values={"id": record.id}, context_value=self._ctx(admin_user)
        )
        assert result.errors is None
        assert result.data["invoiceRecord"]["id"] == record.id
        assert result.data["invoiceRecord"]["invoiceNumber"] == record.invoice_number

    def test_returns_null_for_missing_id(self, db, tenant, admin_user):
        result = schema.execute_sync(
            self.QUERY, variable_values={"id": 99999}, context_value=self._ctx(admin_user)
        )
        assert result.errors is None
        assert result.data["invoiceRecord"] is None

    def test_returns_null_for_other_tenant(
        self, db, tenant, legal_data, active_contract, contract_item, admin_user
    ):
        service = InvoiceService(tenant)
        records = service.generate_and_persist(2026, 1)
        record = records[0]

        # Create user in different tenant
        other_tenant = Tenant.objects.create(name="Other Co", currency="EUR")
        other_user = User.objects.create_user(
            email="other@test.local", password="pass", tenant=other_tenant
        )
        other_role = Role.objects.get(tenant=other_tenant, name="Admin")
        other_user.roles.add(other_role)

        result = schema.execute_sync(
            self.QUERY, variable_values={"id": record.id}, context_value=self._ctx(other_user)
        )
        assert result.errors is None
        assert result.data["invoiceRecord"] is None
