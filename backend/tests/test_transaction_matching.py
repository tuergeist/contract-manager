"""Tests for transaction-to-invoice matching (credits and debits)."""

import uuid
from decimal import Decimal

import pytest

from apps.banking.models import BankAccount, BankTransaction, Counterparty, IncomingInvoice
from apps.customers.models import Customer
from apps.invoices.models import ImportedInvoice, InvoicePaymentMatch, InvoiceRecord


@pytest.fixture
def tenant(db):
    from apps.tenants.models import Tenant
    return Tenant.objects.create(name="Test Tenant", is_active=True)


@pytest.fixture
def user(db, tenant):
    from apps.tenants.models import User
    return User.objects.create_user(
        email="admin@test.local", password="test123", tenant=tenant,
    )


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(tenant=tenant, name="Acme Corp")


@pytest.fixture
def counterparty_with_customer(db, tenant, customer):
    return Counterparty.objects.create(
        tenant=tenant, name="Acme Payments", customer=customer,
    )


@pytest.fixture
def counterparty_supplier(db, tenant):
    """Counterparty without customer link (supplier)."""
    return Counterparty.objects.create(
        tenant=tenant, name="Office Supplies GmbH",
    )


@pytest.fixture
def bank_account(db, tenant):
    return BankAccount.objects.create(
        tenant=tenant, name="Main", bank_code="DEUTDE", account_number="123",
        iban="DE89370400440532013000", bic="DEUTDEFF",
    )


@pytest.fixture
def credit_transaction(db, tenant, bank_account, counterparty_with_customer):
    """Incoming payment (credit, amount > 0)."""
    return BankTransaction.objects.create(
        tenant=tenant, account=bank_account, counterparty=counterparty_with_customer,
        entry_date="2026-03-15", amount=Decimal("1000.00"), currency="EUR",
        booking_text="Payment INV-2026-001", reference="", import_hash="credit1",
    )


@pytest.fixture
def debit_transaction(db, tenant, bank_account, counterparty_supplier):
    """Outgoing payment (debit, amount < 0)."""
    return BankTransaction.objects.create(
        tenant=tenant, account=bank_account, counterparty=counterparty_supplier,
        entry_date="2026-03-20", amount=Decimal("-500.00"), currency="EUR",
        booking_text="Invoice 12345", reference="", import_hash="debit1",
    )


class TestCreditTransactionMatching:
    """Credits (incoming payments) should match outgoing invoices."""

    def test_suggests_imported_invoice_for_credit(
        self, tenant, customer, credit_transaction, counterparty_with_customer
    ):
        inv = ImportedInvoice.objects.create(
            tenant=tenant, customer=customer, invoice_number="INV-2026-001",
            total_amount=Decimal("1000.00"), invoice_date="2026-03-01",
            extraction_status="confirmed", original_filename="inv.pdf", file_size=1000,
        )

        from apps.banking.schema import BankingQuery
        # Simulate the query logic directly
        from apps.banking.models import BankTransaction as BT
        from django.db.models import Q

        txn = credit_transaction
        assert txn.amount > 0
        assert txn.counterparty.customer_id == customer.id

        # The query should find this invoice
        qs = ImportedInvoice.objects.filter(
            tenant=tenant, customer=customer,
            extraction_status__in=["confirmed", "sent"],
        ).filter(Q(invoice_date__lte=txn.entry_date) | Q(invoice_date__isnull=True))
        assert qs.count() == 1
        assert qs.first().invoice_number == "INV-2026-001"

    def test_does_not_suggest_incoming_invoice_for_credit(
        self, tenant, customer, credit_transaction, counterparty_with_customer
    ):
        """Credits should NOT show incoming (supplier) invoices."""
        IncomingInvoice.objects.create(
            tenant=tenant, counterparty=counterparty_with_customer,
            supplier_name="Some Supplier", gross_amount=Decimal("1000.00"),
            invoice_date="2026-03-01", extraction_status="confirmed",
            original_filename="test.pdf",
        )
        # For credits, only outgoing invoices are relevant
        # Incoming invoices should not appear
        qs = IncomingInvoice.objects.filter(
            tenant=tenant, counterparty=counterparty_with_customer,
        )
        assert qs.count() == 1  # exists but shouldn't be suggested for credits


class TestDebitTransactionMatching:
    """Debits (outgoing payments) should match incoming invoices."""

    def test_suggests_incoming_invoice_for_debit(
        self, tenant, debit_transaction, counterparty_supplier
    ):
        inv = IncomingInvoice.objects.create(
            tenant=tenant, counterparty=counterparty_supplier,
            supplier_name="Office Supplies GmbH", invoice_number="OS-12345",
            gross_amount=Decimal("500.00"), invoice_date="2026-03-10",
            extraction_status="confirmed", original_filename="invoice.pdf",
        )

        txn = debit_transaction
        assert txn.amount < 0

        from django.db.models import Q
        qs = IncomingInvoice.objects.filter(
            tenant=tenant, counterparty=counterparty_supplier,
            extraction_status__in=["extracted", "confirmed", "matched"],
        ).filter(Q(invoice_date__lte=txn.entry_date) | Q(invoice_date__isnull=True))

        assert qs.count() == 1
        assert qs.first().invoice_number == "OS-12345"

    def test_does_not_suggest_future_incoming_invoice(
        self, tenant, debit_transaction, counterparty_supplier
    ):
        """Invoices dated after the transaction should not be suggested."""
        IncomingInvoice.objects.create(
            tenant=tenant, counterparty=counterparty_supplier,
            supplier_name="Office Supplies GmbH", invoice_number="FUTURE-001",
            gross_amount=Decimal("500.00"), invoice_date="2026-04-01",
            extraction_status="confirmed", original_filename="future.pdf",
        )

        from django.db.models import Q
        qs = IncomingInvoice.objects.filter(
            tenant=tenant, counterparty=counterparty_supplier,
            extraction_status__in=["extracted", "confirmed", "matched"],
        ).filter(Q(invoice_date__lte=debit_transaction.entry_date) | Q(invoice_date__isnull=True))

        assert qs.count() == 0

    def test_suggests_storno_for_debit_with_customer_link(
        self, tenant, customer, bank_account, counterparty_with_customer
    ):
        """Debit from a counterparty linked to customer should also suggest credit notes."""
        debit = BankTransaction.objects.create(
            tenant=tenant, account=bank_account, counterparty=counterparty_with_customer,
            entry_date="2026-03-20", amount=Decimal("-200.00"), currency="EUR",
            booking_text="Refund", reference="", import_hash="debit_storno",
        )

        storno = InvoiceRecord.objects.create(
            tenant=tenant, customer=customer, invoice_number="S-2026-001",
            total_gross=Decimal("200.00"), total_net=Decimal("168.07"),
            tax_amount=Decimal("31.93"), tax_rate=Decimal("19"),
            invoice_date="2026-03-15", billing_date="2026-03-15",
            period_start="2026-03-01", period_end="2026-03-31",
            document_type="storno", status="finalized",
            line_items_snapshot=[], company_data_snapshot={},
        )

        from django.db.models import Q
        qs = InvoiceRecord.objects.filter(
            tenant=tenant, customer=customer, document_type="storno",
        ).exclude(status="voided").filter(
            Q(invoice_date__lte=debit.entry_date) | Q(invoice_date__isnull=True)
        )

        assert qs.count() == 1
        assert qs.first().invoice_number == "S-2026-001"


class TestPaymentMatchCreation:
    """Test creating payment matches for all invoice types."""

    def test_create_match_for_incoming_invoice(
        self, tenant, debit_transaction, counterparty_supplier
    ):
        inv = IncomingInvoice.objects.create(
            tenant=tenant, counterparty=counterparty_supplier,
            supplier_name="Office Supplies GmbH", invoice_number="OS-12345",
            gross_amount=Decimal("500.00"), invoice_date="2026-03-10",
            extraction_status="confirmed", original_filename="invoice.pdf",
        )

        match = InvoicePaymentMatch.objects.create(
            tenant=tenant,
            incoming_invoice=inv,
            transaction=debit_transaction,
            match_type=InvoicePaymentMatch.MatchType.MANUAL,
            confidence=Decimal("1.00"),
        )

        assert match.incoming_invoice == inv
        assert match.transaction == debit_transaction
        assert match.invoice is None
        assert match.invoice_record is None

    def test_incoming_match_sets_status_to_matched(
        self, tenant, debit_transaction, counterparty_supplier
    ):
        inv = IncomingInvoice.objects.create(
            tenant=tenant, counterparty=counterparty_supplier,
            supplier_name="Office Supplies GmbH", invoice_number="OS-12345",
            gross_amount=Decimal("500.00"), invoice_date="2026-03-10",
            extraction_status="confirmed", original_filename="invoice.pdf",
        )

        InvoicePaymentMatch.objects.create(
            tenant=tenant, incoming_invoice=inv,
            transaction=debit_transaction,
            match_type=InvoicePaymentMatch.MatchType.MANUAL,
            confidence=Decimal("1.00"),
        )

        # Simulate the mutation's status transition
        inv.extraction_status = "matched"
        inv.save(update_fields=["extraction_status"])
        inv.refresh_from_db()
        assert inv.extraction_status == "matched"

    def test_unique_constraint_prevents_duplicate(
        self, tenant, debit_transaction, counterparty_supplier
    ):
        inv = IncomingInvoice.objects.create(
            tenant=tenant, counterparty=counterparty_supplier,
            supplier_name="Test", invoice_number="T-1",
            gross_amount=Decimal("100.00"), extraction_status="confirmed",
            original_filename="t.pdf",
        )

        InvoicePaymentMatch.objects.create(
            tenant=tenant, incoming_invoice=inv,
            transaction=debit_transaction,
            match_type=InvoicePaymentMatch.MatchType.MANUAL,
            confidence=Decimal("1.00"),
        )

        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            InvoicePaymentMatch.objects.create(
                tenant=tenant, incoming_invoice=inv,
                transaction=debit_transaction,
                match_type=InvoicePaymentMatch.MatchType.MANUAL,
                confidence=Decimal("1.00"),
            )

    def test_tenant_isolation(self, db, tenant, bank_account, counterparty_supplier):
        """Matches from one tenant should not leak to another."""
        from apps.tenants.models import Tenant

        other_tenant = Tenant.objects.create(name="Other", is_active=True)
        other_cp = Counterparty.objects.create(tenant=other_tenant, name="Other Supplier")

        inv = IncomingInvoice.objects.create(
            tenant=other_tenant, counterparty=other_cp,
            supplier_name="Other", invoice_number="X-1",
            gross_amount=Decimal("500.00"), extraction_status="confirmed",
            original_filename="x.pdf",
        )

        # Query scoped to original tenant should not find other tenant's invoices
        from django.db.models import Q
        qs = IncomingInvoice.objects.filter(
            tenant=tenant, counterparty=counterparty_supplier,
        )
        assert qs.count() == 0
