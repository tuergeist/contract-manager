"""Tests for transaction match details, invoice search, and suggested matches."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from django.core.files.base import ContentFile

from apps.banking.models import BankAccount, BankTransaction, Counterparty
from apps.customers.models import Customer
from apps.invoices.models import ImportedInvoice, InvoiceRecord, InvoicePaymentMatch
from apps.core.context import Context
from config.schema import schema


# --- Helpers ---


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


# --- Fixtures ---


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="Acme Corp",
        is_active=True,
    )


@pytest.fixture
def account(db, tenant):
    return BankAccount.objects.create(
        tenant=tenant,
        name="Main Account",
        bank_code="85090000",
        account_number="2721891006",
        iban="DE12850900002721891006",
        bic="GENODEF1DRS",
    )


@pytest.fixture
def counterparty(db, tenant):
    return Counterparty.objects.create(
        tenant=tenant,
        name="Acme Corp GmbH",
    )


@pytest.fixture
def transaction(db, tenant, account, counterparty):
    return BankTransaction.objects.create(
        tenant=tenant,
        account=account,
        entry_date=date(2026, 1, 15),
        value_date=date(2026, 1, 15),
        amount=Decimal("1500.00"),
        currency="EUR",
        counterparty=counterparty,
        booking_text="Zahlung Rechnung INV-2026-001",
        reference="EREF+INV-2026-001",
        import_hash="abc123hash",
    )


def _create_imported_invoice(tenant, customer, number="INV-2026-001", amount="1500.00", status="confirmed"):
    return ImportedInvoice.objects.create(
        tenant=tenant,
        invoice_number=number,
        invoice_date=date(2026, 1, 10),
        total_amount=Decimal(amount),
        customer=customer,
        customer_name=customer.name,
        extraction_status=status,
        pdf_file=ContentFile(b"%PDF-fake", name=f"{number}.pdf"),
        original_filename=f"{number}.pdf",
        file_size=100,
    )


@pytest.fixture
def imported_invoice(db, tenant, customer):
    return _create_imported_invoice(tenant, customer)


@pytest.fixture
def generated_invoice(db, tenant, customer):
    return InvoiceRecord.objects.create(
        tenant=tenant,
        invoice_number="R-2026-0001",
        invoice_date=date(2026, 1, 10),
        billing_date=date(2026, 1, 1),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_net=Decimal("840.00"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("159.60"),
        total_gross=Decimal("999.60"),
        customer=customer,
        status="finalized",
        line_items_snapshot=[],
        company_data_snapshot={},
    )


MATCH_DETAILS_QUERY = """
query($transactionId: Int!) {
  transactionMatchDetails(transactionId: $transactionId) {
    id
    entryDate
    valueDate
    amount
    currency
    counterpartyName
    bookingText
    reference
    accountName
    totalMatched
    difference
    matches {
      id
      invoiceId
      invoiceRecordId
      invoiceNumber
      invoiceAmount
      customerName
      invoiceType
      matchType
      confidence
    }
  }
}
"""

SEARCH_INVOICES_QUERY = """
query($search: String, $unmatchedOnly: Boolean, $limit: Int) {
  searchInvoicesForMatching(search: $search, unmatchedOnly: $unmatchedOnly, limit: $limit) {
    items {
      id
      invoiceNumber
      amount
      customerName
      invoiceType
      status
      isPaid
    }
    hasMore
  }
}
"""


# =========================================================================
# Tests: transactionMatchDetails
# =========================================================================


class TestTransactionMatchDetails:

    def test_single_imported_match(self, user, transaction, imported_invoice, tenant):
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=imported_invoice,
            transaction=transaction,
            match_type="invoice_number",
            confidence=Decimal("0.95"),
        )

        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        data = result.data["transactionMatchDetails"]
        assert data["id"] == transaction.id
        assert data["amount"] == "1500.00"
        assert data["counterpartyName"] == "Acme Corp GmbH"
        assert data["accountName"] == "Main Account"
        assert len(data["matches"]) == 1

        match = data["matches"][0]
        assert match["invoiceNumber"] == "INV-2026-001"
        assert match["invoiceAmount"] == "1500.00"
        assert match["customerName"] == "Acme Corp"
        assert match["invoiceType"] == "imported"
        assert match["matchType"] == "invoice_number"

    def test_single_generated_match(self, user, transaction, generated_invoice, tenant):
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice_record=generated_invoice,
            transaction=transaction,
            match_type="manual",
            confidence=Decimal("1.00"),
        )

        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        data = result.data["transactionMatchDetails"]
        assert len(data["matches"]) == 1

        match = data["matches"][0]
        assert match["invoiceNumber"] == "R-2026-0001"
        assert match["invoiceAmount"] == "999.60"
        assert match["invoiceType"] == "generated"
        assert match["invoiceRecordId"] == generated_invoice.id

    def test_multiple_matches_total_calculation(self, user, transaction, imported_invoice, generated_invoice, tenant):
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=imported_invoice,
            transaction=transaction,
            match_type="invoice_number",
            confidence=Decimal("0.95"),
        )
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice_record=generated_invoice,
            transaction=transaction,
            match_type="manual",
            confidence=Decimal("1.00"),
        )

        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        data = result.data["transactionMatchDetails"]
        assert len(data["matches"]) == 2

        # 1500.00 + 999.60 = 2499.60
        assert Decimal(data["totalMatched"]) == Decimal("2499.60")
        # difference = abs(1500.00) - 2499.60 = -999.60
        assert Decimal(data["difference"]) == Decimal("-999.60")

    def test_no_matches(self, user, transaction):
        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        data = result.data["transactionMatchDetails"]
        assert len(data["matches"]) == 0
        assert Decimal(data["totalMatched"]) == Decimal("0")
        assert Decimal(data["difference"]) == Decimal("1500.00")

    def test_transaction_not_found(self, user):
        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": 99999}, make_context(user))
        assert result.errors is None
        assert result.data["transactionMatchDetails"] is None

    def test_tenant_isolation(self, user, transaction, imported_invoice, tenant):
        """User from another tenant cannot see the transaction."""
        from apps.tenants.models import Role, Tenant, User

        other_tenant = Tenant.objects.create(name="Other Co", currency="EUR")
        other_user = User.objects.create_user(
            email="other@example.com", password="pass", tenant=other_tenant
        )
        other_user.roles.add(Role.objects.get(tenant=other_tenant, name="Admin"))

        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=imported_invoice,
            transaction=transaction,
            match_type="invoice_number",
            confidence=Decimal("0.95"),
        )

        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": transaction.id}, make_context(other_user))
        assert result.errors is None
        assert result.data["transactionMatchDetails"] is None

    def test_difference_exact_match(self, user, transaction, imported_invoice, tenant):
        """When matched amount equals transaction, difference is 0."""
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=imported_invoice,
            transaction=transaction,
            match_type="invoice_number",
            confidence=Decimal("0.95"),
        )

        result = run_graphql(MATCH_DETAILS_QUERY, {"transactionId": transaction.id}, make_context(user))
        data = result.data["transactionMatchDetails"]
        # transaction.amount = 1500, invoice.total_amount = 1500
        assert Decimal(data["difference"]) == Decimal("0.00")
        assert Decimal(data["totalMatched"]) == Decimal("1500.00")


# =========================================================================
# Tests: searchInvoicesForMatching
# =========================================================================


class TestSearchInvoicesForMatching:

    def test_search_by_invoice_number(self, user, imported_invoice, generated_invoice):
        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": "INV-2026"}, make_context(user))
        assert result.errors is None

        items = result.data["searchInvoicesForMatching"]["items"]
        assert len(items) == 1
        assert items[0]["invoiceNumber"] == "INV-2026-001"
        assert items[0]["invoiceType"] == "imported"

    def test_search_returns_both_types(self, user, imported_invoice, generated_invoice):
        """Empty search returns both imported and generated invoices."""
        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": ""}, make_context(user))
        assert result.errors is None

        items = result.data["searchInvoicesForMatching"]["items"]
        types = {i["invoiceType"] for i in items}
        assert types == {"imported", "generated"}
        assert len(items) == 2

    def test_search_by_customer_name(self, user, imported_invoice, generated_invoice):
        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": "Acme"}, make_context(user))
        assert result.errors is None

        items = result.data["searchInvoicesForMatching"]["items"]
        assert len(items) == 2
        assert all(i["customerName"] == "Acme Corp" for i in items)

    def test_search_case_insensitive(self, user, imported_invoice):
        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": "inv-2026"}, make_context(user))
        assert result.errors is None
        assert len(result.data["searchInvoicesForMatching"]["items"]) == 1

    def test_unmatched_only_excludes_paid(self, user, tenant, customer):
        """Paid invoices are excluded when unmatchedOnly is true."""
        _create_imported_invoice(tenant, customer, "PAID-001", "500.00", "paid")
        _create_imported_invoice(tenant, customer, "OPEN-001", "700.00", "confirmed")
        InvoiceRecord.objects.create(
            tenant=tenant,
            invoice_number="REC-PAID-001",
            invoice_date=date(2026, 1, 1),
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("19.00"),
            total_gross=Decimal("119.00"),
            customer=customer,
            status="paid",
            line_items_snapshot=[],
            company_data_snapshot={},
        )
        InvoiceRecord.objects.create(
            tenant=tenant,
            invoice_number="REC-OPEN-001",
            invoice_date=date(2026, 1, 1),
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("200.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("38.00"),
            total_gross=Decimal("238.00"),
            customer=customer,
            status="finalized",
            line_items_snapshot=[],
            company_data_snapshot={},
        )

        result = run_graphql(
            SEARCH_INVOICES_QUERY,
            {"search": "", "unmatchedOnly": True},
            make_context(user),
        )
        assert result.errors is None

        items = result.data["searchInvoicesForMatching"]["items"]
        numbers = {i["invoiceNumber"] for i in items}
        assert "PAID-001" not in numbers
        assert "REC-PAID-001" not in numbers
        assert "OPEN-001" in numbers
        assert "REC-OPEN-001" in numbers

    def test_pagination_limit(self, user, tenant, customer):
        """Respects limit and sets hasMore correctly."""
        for i in range(5):
            _create_imported_invoice(tenant, customer, f"INV-{i:04d}", "100.00")

        result = run_graphql(
            SEARCH_INVOICES_QUERY,
            {"search": "INV-", "limit": 3},
            make_context(user),
        )
        assert result.errors is None

        data = result.data["searchInvoicesForMatching"]
        assert len(data["items"]) == 3
        assert data["hasMore"] is True

    def test_excludes_voided_records(self, user, tenant, customer):
        """Voided invoice records are excluded from search."""
        InvoiceRecord.objects.create(
            tenant=tenant,
            invoice_number="VOIDED-001",
            invoice_date=date(2026, 1, 1),
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("19.00"),
            total_gross=Decimal("119.00"),
            customer=customer,
            status="voided",
            line_items_snapshot=[],
            company_data_snapshot={},
        )

        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": "VOIDED"}, make_context(user))
        assert result.errors is None
        assert len(result.data["searchInvoicesForMatching"]["items"]) == 0

    def test_excludes_pending_imported(self, user, tenant, customer):
        """Only confirmed/sent/paid imported invoices are searchable."""
        _create_imported_invoice(tenant, customer, "PENDING-001", "100.00", "pending")

        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": "PENDING"}, make_context(user))
        assert result.errors is None
        assert len(result.data["searchInvoicesForMatching"]["items"]) == 0

    def test_tenant_isolation(self, user, imported_invoice, tenant):
        """User from another tenant cannot see invoices."""
        from apps.tenants.models import Role, Tenant, User

        other_tenant = Tenant.objects.create(name="Other Co", currency="EUR")
        other_user = User.objects.create_user(
            email="other2@example.com", password="pass", tenant=other_tenant
        )
        other_user.roles.add(Role.objects.get(tenant=other_tenant, name="Admin"))

        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": "INV-2026"}, make_context(other_user))
        assert result.errors is None
        assert len(result.data["searchInvoicesForMatching"]["items"]) == 0

    def test_sorted_by_invoice_number(self, user, tenant, customer):
        """Results are sorted by invoice number."""
        for num in ["Z-003", "A-001", "M-002"]:
            _create_imported_invoice(tenant, customer, num, "100.00")

        result = run_graphql(SEARCH_INVOICES_QUERY, {"search": ""}, make_context(user))
        assert result.errors is None

        numbers = [i["invoiceNumber"] for i in result.data["searchInvoicesForMatching"]["items"]]
        assert numbers == sorted(numbers)


# =========================================================================
# Tests: suggestedInvoiceMatches
# =========================================================================


SUGGESTED_MATCHES_QUERY = """
query($transactionId: Int!) {
  suggestedInvoiceMatches(transactionId: $transactionId) {
    customerName
    customerId
    items {
      id
      invoiceNumber
      amount
      customerName
      invoiceType
      status
      invoiceDate
      amountDifference
    }
  }
}
"""

MATCH_DETAILS_CUSTOMER_QUERY = """
query($transactionId: Int!) {
  transactionMatchDetails(transactionId: $transactionId) {
    id
    customerId
  }
}
"""


def _create_record(tenant, customer, number, gross, status="finalized", inv_date=None):
    return InvoiceRecord.objects.create(
        tenant=tenant,
        invoice_number=number,
        invoice_date=inv_date or date(2026, 1, 5),
        billing_date=date(2026, 1, 1),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_net=Decimal(gross) / Decimal("1.19"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal(gross) - Decimal(gross) / Decimal("1.19"),
        total_gross=Decimal(gross),
        customer=customer,
        status=status,
        line_items_snapshot=[],
        company_data_snapshot={},
    )


class TestSuggestedInvoiceMatches:

    def test_linked_counterparty_returns_candidates(self, user, transaction, customer, counterparty, tenant):
        """Linked counterparty suggests the customer's unpaid invoices."""
        counterparty.customer = customer
        counterparty.save()

        _create_imported_invoice(tenant, customer, "INV-SUGGEST-001", "1500.00")

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        data = result.data["suggestedInvoiceMatches"]
        assert data["customerName"] == "Acme Corp"
        assert data["customerId"] == customer.id
        assert len(data["items"]) == 1
        assert data["items"][0]["invoiceNumber"] == "INV-SUGGEST-001"

    def test_unlinked_counterparty_returns_none(self, user, transaction):
        """No customer link returns None."""
        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None
        assert result.data["suggestedInvoiceMatches"] is None

    def test_date_filter_excludes_future_invoices(self, user, transaction, customer, counterparty, tenant):
        """Invoices dated after the transaction are excluded."""
        counterparty.customer = customer
        counterparty.save()

        # Transaction entry_date is 2026-01-15
        _create_imported_invoice(tenant, customer, "BEFORE", "1000.00")  # date 2026-01-10
        inv_after = _create_imported_invoice(tenant, customer, "AFTER", "1000.00")
        ImportedInvoice.objects.filter(id=inv_after.id).update(invoice_date=date(2026, 2, 1))

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        numbers = [i["invoiceNumber"] for i in result.data["suggestedInvoiceMatches"]["items"]]
        assert "BEFORE" in numbers
        assert "AFTER" not in numbers

    def test_null_date_included(self, user, transaction, customer, counterparty, tenant):
        """Invoices with null date are still included."""
        counterparty.customer = customer
        counterparty.save()

        inv = _create_imported_invoice(tenant, customer, "NO-DATE", "1000.00")
        ImportedInvoice.objects.filter(id=inv.id).update(invoice_date=None)

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None
        assert len(result.data["suggestedInvoiceMatches"]["items"]) == 1

    def test_excludes_paid_invoices(self, user, transaction, customer, counterparty, tenant):
        """Paid imported invoices and paid records are excluded."""
        counterparty.customer = customer
        counterparty.save()

        _create_imported_invoice(tenant, customer, "PAID-IMP", "1000.00", "paid")
        _create_record(tenant, customer, "PAID-REC", "1000.00", "paid")
        _create_imported_invoice(tenant, customer, "OPEN-IMP", "1000.00", "confirmed")

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        numbers = [i["invoiceNumber"] for i in result.data["suggestedInvoiceMatches"]["items"]]
        assert "PAID-IMP" not in numbers
        assert "PAID-REC" not in numbers
        assert "OPEN-IMP" in numbers

    def test_excludes_already_matched(self, user, transaction, customer, counterparty, tenant):
        """Invoices already matched to this transaction are excluded."""
        counterparty.customer = customer
        counterparty.save()

        matched_inv = _create_imported_invoice(tenant, customer, "MATCHED", "1500.00")
        unmatched_inv = _create_imported_invoice(tenant, customer, "UNMATCHED", "1500.00")

        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=matched_inv,
            transaction=transaction,
            match_type="manual",
            confidence=Decimal("1.00"),
        )

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        numbers = [i["invoiceNumber"] for i in result.data["suggestedInvoiceMatches"]["items"]]
        assert "MATCHED" not in numbers
        assert "UNMATCHED" in numbers

    def test_amount_ranking_exact_first(self, user, transaction, customer, counterparty, tenant):
        """Exact amount match is ranked first."""
        counterparty.customer = customer
        counterparty.save()

        # Transaction amount is 1500.00
        _create_imported_invoice(tenant, customer, "FAR", "500.00")
        _create_imported_invoice(tenant, customer, "EXACT", "1500.00")
        _create_imported_invoice(tenant, customer, "CLOSE", "1400.00")

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        items = result.data["suggestedInvoiceMatches"]["items"]
        assert items[0]["invoiceNumber"] == "EXACT"
        assert Decimal(items[0]["amountDifference"]) == Decimal("0.00")

    def test_amount_ranking_proximity_order(self, user, transaction, customer, counterparty, tenant):
        """Candidates ordered by amount proximity."""
        counterparty.customer = customer
        counterparty.save()

        # Transaction amount is 1500.00
        _create_imported_invoice(tenant, customer, "DIFF-500", "2000.00")   # diff 500
        _create_imported_invoice(tenant, customer, "DIFF-50", "1450.00")    # diff 50
        _create_imported_invoice(tenant, customer, "DIFF-200", "1300.00")   # diff 200

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        numbers = [i["invoiceNumber"] for i in result.data["suggestedInvoiceMatches"]["items"]]
        assert numbers == ["DIFF-50", "DIFF-200", "DIFF-500"]

    def test_mixed_imported_and_generated(self, user, transaction, customer, counterparty, tenant):
        """Both imported and generated invoices appear as candidates."""
        counterparty.customer = customer
        counterparty.save()

        _create_imported_invoice(tenant, customer, "IMP-001", "1500.00")
        _create_record(tenant, customer, "REC-001", "1500.00")

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None

        types = {i["invoiceType"] for i in result.data["suggestedInvoiceMatches"]["items"]}
        assert types == {"imported", "generated"}

    def test_tenant_isolation(self, user, transaction, customer, counterparty, tenant):
        """Other tenant cannot see suggestions."""
        from apps.tenants.models import Role, Tenant, User

        counterparty.customer = customer
        counterparty.save()
        _create_imported_invoice(tenant, customer, "SECRET", "1500.00")

        other_tenant = Tenant.objects.create(name="Other Co", currency="EUR")
        other_user = User.objects.create_user(
            email="other3@example.com", password="pass", tenant=other_tenant
        )
        other_user.roles.add(Role.objects.get(tenant=other_tenant, name="Admin"))

        result = run_graphql(SUGGESTED_MATCHES_QUERY, {"transactionId": transaction.id}, make_context(other_user))
        assert result.errors is None
        assert result.data["suggestedInvoiceMatches"] is None


class TestTransactionMatchDetailsCustomerId:

    def test_customer_id_present_when_linked(self, user, transaction, customer, counterparty):
        counterparty.customer = customer
        counterparty.save()

        result = run_graphql(MATCH_DETAILS_CUSTOMER_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None
        assert result.data["transactionMatchDetails"]["customerId"] == customer.id

    def test_customer_id_null_when_unlinked(self, user, transaction):
        result = run_graphql(MATCH_DETAILS_CUSTOMER_QUERY, {"transactionId": transaction.id}, make_context(user))
        assert result.errors is None
        assert result.data["transactionMatchDetails"]["customerId"] is None


# --- Delete Payment Match Status Revert ---

DELETE_MATCH_MUTATION = """
mutation($matchId: Int!) {
  deletePaymentMatch(matchId: $matchId) {
    success
    error
  }
}
"""


@pytest.mark.django_db
class TestDeletePaymentMatchStatusRevert:
    """Deleting a payment match should revert invoice status when no remaining matches."""

    def test_imported_invoice_reverts_to_sent(self, user, tenant, customer, transaction):
        inv = _create_imported_invoice(tenant, customer, "INV-REVERT-1", "1500.00", "sent")
        match = InvoicePaymentMatch.objects.create(
            tenant=tenant, invoice=inv, transaction=transaction,
            match_type="manual", confidence=Decimal("1.0"),
        )
        inv.extraction_status = "paid"
        inv.save(update_fields=["extraction_status"])

        result = run_graphql(DELETE_MATCH_MUTATION, {"matchId": match.id}, make_context(user))
        assert result.errors is None
        assert result.data["deletePaymentMatch"]["success"] is True

        inv.refresh_from_db()
        assert inv.extraction_status == "sent"

    def test_generated_invoice_reverts_to_sent(self, user, tenant, customer, transaction, generated_invoice):
        match = InvoicePaymentMatch.objects.create(
            tenant=tenant, invoice_record=generated_invoice, transaction=transaction,
            match_type="manual", confidence=Decimal("1.0"),
        )
        generated_invoice.status = "paid"
        generated_invoice.save(update_fields=["status"])

        result = run_graphql(DELETE_MATCH_MUTATION, {"matchId": match.id}, make_context(user))
        assert result.errors is None
        assert result.data["deletePaymentMatch"]["success"] is True

        generated_invoice.refresh_from_db()
        assert generated_invoice.status == "sent"

    def test_imported_stays_paid_with_remaining_match(self, user, tenant, customer, account, counterparty, transaction):
        inv = _create_imported_invoice(tenant, customer, "INV-MULTI", "1500.00", "paid")
        txn2 = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date=date(2026, 2, 1),
            amount=Decimal("500.00"), currency="EUR",
            counterparty=counterparty,
            import_hash="hash-second",
        )
        match1 = InvoicePaymentMatch.objects.create(
            tenant=tenant, invoice=inv, transaction=transaction,
            match_type="manual", confidence=Decimal("1.0"),
        )
        InvoicePaymentMatch.objects.create(
            tenant=tenant, invoice=inv, transaction=txn2,
            match_type="manual", confidence=Decimal("1.0"),
        )

        result = run_graphql(DELETE_MATCH_MUTATION, {"matchId": match1.id}, make_context(user))
        assert result.data["deletePaymentMatch"]["success"] is True

        inv.refresh_from_db()
        assert inv.extraction_status == "paid"  # Still has another match
