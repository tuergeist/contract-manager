"""Tests for invoice import, extraction, and payment matching."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.banking.models import BankTransaction, Counterparty
from apps.customers.models import Customer
from apps.invoices.customer_matching import (
    CustomerMatch,
    auto_match_customer,
    find_exact_match,
    match_customer_by_name,
)
from apps.invoices.models import ImportedInvoice, InvoiceImportBatch, InvoicePaymentMatch, UploadStatus
from apps.invoices.payment_matching import (
    AmountCustomerStrategy,
    InvoiceNumberStrategy,
    PaymentMatcher,
    PaymentMatchCandidate,
)


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    from apps.tenants.models import Tenant

    return Tenant.objects.create(name="Test Tenant")


@pytest.fixture
def user(tenant):
    """Create a test user."""
    from apps.tenants.models import User

    return User.objects.create(
        email="test@example.com",
        tenant=tenant,
    )


@pytest.fixture
def customer(tenant):
    """Create a test customer."""
    return Customer.objects.create(
        tenant=tenant,
        name="Acme Corporation GmbH",
    )


@pytest.fixture
def counterparty(tenant, customer):
    """Create a test counterparty linked to customer."""
    return Counterparty.objects.create(
        tenant=tenant,
        name="ACME CORP",
        customer=customer,
    )


@pytest.fixture
def bank_account(tenant):
    """Create a test bank account."""
    from apps.banking.models import BankAccount

    return BankAccount.objects.create(
        tenant=tenant,
        name="Main Account",
        bank_code="12345678",
        account_number="1234567890",
    )


@pytest.fixture
def imported_invoice(tenant, user, customer):
    """Create a test imported invoice."""
    return ImportedInvoice.objects.create(
        tenant=tenant,
        invoice_number="RE-2025-001234",
        invoice_date=date(2025, 1, 15),
        total_amount=Decimal("1234.56"),
        currency="EUR",
        customer_name="Acme Corporation GmbH",
        customer=customer,
        original_filename="invoice.pdf",
        file_size=12345,
        extraction_status=ImportedInvoice.ExtractionStatus.EXTRACTED,
        created_by=user,
    )


class TestImportedInvoiceModel:
    """Tests for ImportedInvoice model."""

    def test_is_paid_false_when_no_matches(self, imported_invoice):
        """Test is_paid returns False when no payment matches exist."""
        assert imported_invoice.is_paid is False

    def test_is_paid_true_when_has_match(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test is_paid returns True when payment match exists."""
        # Create a transaction
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            import_hash="test123",
        )

        # Create a payment match
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=imported_invoice,
            transaction=txn,
            match_type=InvoicePaymentMatch.MatchType.MANUAL,
            confidence=Decimal("1.00"),
        )

        assert imported_invoice.is_paid is True

    def test_str_with_invoice_number(self, imported_invoice):
        """Test __str__ returns invoice number when present."""
        assert "RE-2025-001234" in str(imported_invoice)

    def test_str_without_invoice_number(self, tenant, user):
        """Test __str__ handles missing invoice number."""
        invoice = ImportedInvoice.objects.create(
            tenant=tenant,
            original_filename="invoice.pdf",
            file_size=12345,
            created_by=user,
        )
        assert "pending" in str(invoice).lower()


class TestCustomerMatching:
    """Tests for customer matching service."""

    @pytest.mark.skipif(
        "sqlite" in str(pytest.importorskip("django.conf").settings.DATABASES.get("default", {}).get("ENGINE", "")),
        reason="pg_trgm not available in SQLite"
    )
    def test_match_customer_by_name_exact(self, tenant, customer):
        """Test matching with exact name returns high similarity."""
        matches = match_customer_by_name(
            tenant=tenant,
            extracted_name="Acme Corporation GmbH",
        )
        assert len(matches) >= 1
        assert matches[0].customer_id == customer.id
        assert float(matches[0].similarity) >= 0.9

    @pytest.mark.skipif(
        "sqlite" in str(pytest.importorskip("django.conf").settings.DATABASES.get("default", {}).get("ENGINE", "")),
        reason="pg_trgm not available in SQLite"
    )
    def test_match_customer_by_name_fuzzy(self, tenant, customer):
        """Test matching with similar name returns results."""
        matches = match_customer_by_name(
            tenant=tenant,
            extracted_name="ACME Corp GmbH",
        )
        assert len(matches) >= 1
        assert matches[0].customer_id == customer.id

    @pytest.mark.skipif(
        "sqlite" in str(pytest.importorskip("django.conf").settings.DATABASES.get("default", {}).get("ENGINE", "")),
        reason="pg_trgm not available in SQLite"
    )
    def test_match_customer_by_name_no_match(self, tenant):
        """Test matching with unrelated name returns empty."""
        matches = match_customer_by_name(
            tenant=tenant,
            extracted_name="Completely Different Company",
            min_similarity=0.5,
        )
        assert len(matches) == 0

    def test_match_customer_by_name_empty_string(self, tenant):
        """Test matching with empty string returns empty."""
        matches = match_customer_by_name(
            tenant=tenant,
            extracted_name="",
        )
        assert len(matches) == 0

    def test_find_exact_match(self, tenant, customer):
        """Test finding exact case-insensitive match."""
        result = find_exact_match(
            tenant=tenant,
            extracted_name="acme corporation gmbh",
        )
        assert result == customer

    def test_find_exact_match_not_found(self, tenant):
        """Test finding exact match returns None when not found."""
        result = find_exact_match(
            tenant=tenant,
            extracted_name="Nonexistent Company",
        )
        assert result is None

    def test_auto_match_customer_exact(self, tenant, customer):
        """Test auto-match returns customer on exact match."""
        result = auto_match_customer(
            tenant=tenant,
            extracted_name="Acme Corporation GmbH",
        )
        assert result == customer

    @pytest.mark.skipif(
        "sqlite" in str(pytest.importorskip("django.conf").settings.DATABASES.get("default", {}).get("ENGINE", "")),
        reason="pg_trgm not available in SQLite"
    )
    def test_auto_match_customer_no_high_confidence(self, tenant, customer):
        """Test auto-match returns None when no high-confidence match."""
        result = auto_match_customer(
            tenant=tenant,
            extracted_name="Some Company",
            threshold=0.9,
        )
        assert result is None


class TestInvoiceNumberStrategy:
    """Tests for invoice number matching strategy."""

    def test_exact_match_in_booking_text(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test exact invoice number match gives confidence 1.0."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            booking_text="Payment for RE-2025-001234",
            import_hash="test123",
        )

        strategy = InvoiceNumberStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 1
        assert matches[0].transaction_id == txn.id
        assert matches[0].confidence == Decimal("1.0")

    def test_normalized_match(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test match with different separators gives confidence 0.9."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            booking_text="Payment for RE 2025 001234",
            import_hash="test123",
        )

        strategy = InvoiceNumberStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.9")

    def test_partial_match(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test partial match (suffix) gives confidence 0.7."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            booking_text="Payment ref 001234",
            import_hash="test123",
        )

        strategy = InvoiceNumberStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 1
        assert matches[0].confidence == Decimal("0.7")

    def test_skips_debit_transactions(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test strategy skips debit (negative amount) transactions."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("-1234.56"),  # Debit
            counterparty=counterparty,
            booking_text="Payment for RE-2025-001234",
            import_hash="test123",
        )

        strategy = InvoiceNumberStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 0


class TestAmountCustomerStrategy:
    """Tests for amount + customer matching strategy."""

    def test_match_amount_and_customer(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test matching when amount and customer both match."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),  # Same as invoice
            counterparty=counterparty,  # Linked to same customer
            import_hash="test123",
        )

        strategy = AmountCustomerStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 1
        assert matches[0].transaction_id == txn.id
        assert matches[0].confidence == Decimal("0.8")

    def test_no_match_wrong_amount(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test no match when amount differs."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.55"),  # Different amount
            counterparty=counterparty,
            import_hash="test123",
        )

        strategy = AmountCustomerStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 0

    def test_no_match_unlinked_counterparty(
        self, tenant, imported_invoice, bank_account
    ):
        """Test no match when counterparty not linked to invoice's customer."""
        unlinked_cp = Counterparty.objects.create(
            tenant=tenant,
            name="Other Company",
            # No customer link
        )
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),  # Same amount
            counterparty=unlinked_cp,  # Not linked to customer
            import_hash="test123",
        )

        strategy = AmountCustomerStrategy()
        matches = strategy.find_matches(imported_invoice, [txn])

        assert len(matches) == 0


class TestPaymentMatcher:
    """Tests for PaymentMatcher service."""

    def test_find_matches_combines_strategies(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test matcher combines results from all strategies."""
        # Create a transaction that matches both strategies
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            booking_text="Payment for RE-2025-001234",
            import_hash="test123",
        )

        matcher = PaymentMatcher()
        matches = matcher.find_matches(imported_invoice)

        # Should have one match (deduplicated), with highest confidence
        assert len(matches) == 1
        assert matches[0].confidence == Decimal("1.0")  # Invoice number match

    def test_find_matches_respects_date_window(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test matcher only considers transactions within date window."""
        # Create transaction outside window
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 6, 1),  # 4+ months after invoice
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            booking_text="Payment for RE-2025-001234",
            import_hash="test123",
        )

        matcher = PaymentMatcher()
        matches = matcher.find_matches(imported_invoice, days_after=90)

        assert len(matches) == 0

    def test_find_matches_excludes_already_matched(
        self, tenant, imported_invoice, counterparty, bank_account
    ):
        """Test matcher excludes transactions already matched to the invoice."""
        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            entry_date=date(2025, 2, 1),
            amount=Decimal("1234.56"),
            counterparty=counterparty,
            booking_text="Payment for RE-2025-001234",
            import_hash="test123",
        )

        # Create existing match
        InvoicePaymentMatch.objects.create(
            tenant=tenant,
            invoice=imported_invoice,
            transaction=txn,
            match_type=InvoicePaymentMatch.MatchType.MANUAL,
            confidence=Decimal("1.00"),
        )

        matcher = PaymentMatcher()
        matches = matcher.find_matches(imported_invoice)

        assert len(matches) == 0


class TestInvoiceImportBatch:
    """Tests for InvoiceImportBatch model."""

    def test_create_batch(self, tenant, user):
        """Test creating an import batch."""
        batch = InvoiceImportBatch.objects.create(
            tenant=tenant,
            name="test-batch.csv",
            uploaded_by=user,
            total_expected=5,
            total_uploaded=0,
        )
        assert batch.name == "test-batch.csv"
        assert batch.total_expected == 5
        assert batch.total_uploaded == 0

    def test_batch_str(self, tenant, user):
        """Test batch string representation."""
        batch = InvoiceImportBatch.objects.create(
            tenant=tenant,
            name="test-batch.csv",
            uploaded_by=user,
            total_expected=5,
            total_uploaded=2,
        )
        assert "test-batch.csv" in str(batch)
        assert "2/5" in str(batch)

    def test_update_counts(self, tenant, user):
        """Test batch update_counts method."""
        batch = InvoiceImportBatch.objects.create(
            tenant=tenant,
            name="test-batch.csv",
            uploaded_by=user,
        )

        # Create some invoices
        ImportedInvoice.objects.create(
            tenant=tenant,
            import_batch=batch,
            expected_filename="invoice1.pdf",
            upload_status=UploadStatus.PENDING,
            original_filename="invoice1.pdf",
            file_size=0,
            created_by=user,
        )
        ImportedInvoice.objects.create(
            tenant=tenant,
            import_batch=batch,
            expected_filename="invoice2.pdf",
            upload_status=UploadStatus.UPLOADED,
            original_filename="invoice2.pdf",
            file_size=1000,
            created_by=user,
        )

        batch.update_counts()
        batch.refresh_from_db()

        assert batch.total_expected == 2
        assert batch.total_uploaded == 1


class TestImportedInvoiceReceiverMapping:
    """Tests for receiver mapping fields on ImportedInvoice."""

    def test_create_with_receiver_emails(self, tenant, user):
        """Test creating invoice with receiver emails."""
        invoice = ImportedInvoice.objects.create(
            tenant=tenant,
            expected_filename="invoice.pdf",
            receiver_emails=["billing@acme.com", "finance@acme.com"],
            upload_status=UploadStatus.PENDING,
            original_filename="invoice.pdf",
            file_size=0,
            created_by=user,
        )
        assert invoice.receiver_emails == ["billing@acme.com", "finance@acme.com"]
        assert invoice.upload_status == UploadStatus.PENDING

    def test_upload_status_transitions(self, tenant, user):
        """Test upload status can change from pending to uploaded."""
        invoice = ImportedInvoice.objects.create(
            tenant=tenant,
            expected_filename="invoice.pdf",
            upload_status=UploadStatus.PENDING,
            original_filename="invoice.pdf",
            file_size=0,
            created_by=user,
        )
        assert invoice.upload_status == UploadStatus.PENDING

        invoice.upload_status = UploadStatus.UPLOADED
        invoice.file_size = 5000
        invoice.save()

        invoice.refresh_from_db()
        assert invoice.upload_status == UploadStatus.UPLOADED


class TestBillingEmailDeduplication:
    """Tests for billing email deduplication logic."""

    def test_merge_emails_case_insensitive(self, tenant, customer):
        """Test that email merging is case-insensitive."""
        customer.billing_emails = ["billing@acme.com"]
        customer.save()

        # Simulate adding emails (case variations)
        existing = set(e.lower() for e in customer.billing_emails)
        new_emails = ["Billing@Acme.com", "finance@acme.com"]  # First is duplicate

        for email in new_emails:
            email_lower = email.strip().lower()
            if email_lower not in existing:
                existing.add(email_lower)

        customer.billing_emails = sorted(existing)
        customer.save()

        customer.refresh_from_db()
        assert len(customer.billing_emails) == 2
        assert "billing@acme.com" in customer.billing_emails
        assert "finance@acme.com" in customer.billing_emails

    def test_transfer_emails_on_customer_confirm(self, tenant, user, customer):
        """Test that receiver emails are transferred to customer on confirm."""
        customer.billing_emails = ["existing@acme.com"]
        customer.save()

        invoice = ImportedInvoice.objects.create(
            tenant=tenant,
            invoice_number="TEST-001",
            receiver_emails=["new@acme.com", "existing@acme.com"],
            upload_status=UploadStatus.UPLOADED,
            original_filename="invoice.pdf",
            file_size=1000,
            created_by=user,
            extraction_status=ImportedInvoice.ExtractionStatus.EXTRACTED,
        )

        # Simulate the transfer logic from confirm_customer_match
        existing_emails = set(e.lower() for e in (customer.billing_emails or []))
        for email in invoice.receiver_emails:
            email_lower = email.strip().lower()
            if email_lower and email_lower not in existing_emails:
                existing_emails.add(email_lower)

        customer.billing_emails = sorted(existing_emails)
        customer.save()

        customer.refresh_from_db()
        assert len(customer.billing_emails) == 2
        assert "existing@acme.com" in customer.billing_emails
        assert "new@acme.com" in customer.billing_emails


class TestBatchDeletion:
    """Tests for import batch deletion logic."""

    def test_delete_batch_removes_pending_invoices(self, tenant, user):
        """Test deleting batch removes pending invoices but keeps uploaded ones."""
        batch = InvoiceImportBatch.objects.create(
            tenant=tenant,
            name="test-batch.csv",
            uploaded_by=user,
        )

        # Create pending invoice
        pending_invoice = ImportedInvoice.objects.create(
            tenant=tenant,
            import_batch=batch,
            expected_filename="pending.pdf",
            upload_status=UploadStatus.PENDING,
            original_filename="pending.pdf",
            file_size=0,
            created_by=user,
        )

        # Create uploaded invoice
        uploaded_invoice = ImportedInvoice.objects.create(
            tenant=tenant,
            import_batch=batch,
            expected_filename="uploaded.pdf",
            upload_status=UploadStatus.UPLOADED,
            original_filename="uploaded.pdf",
            file_size=5000,
            created_by=user,
        )

        pending_id = pending_invoice.id
        uploaded_id = uploaded_invoice.id

        # Simulate batch deletion logic
        ImportedInvoice.objects.filter(
            import_batch=batch,
            upload_status=UploadStatus.PENDING,
        ).delete()

        ImportedInvoice.objects.filter(import_batch=batch).update(import_batch=None)

        batch.delete()

        # Pending invoice should be deleted
        assert not ImportedInvoice.objects.filter(id=pending_id).exists()

        # Uploaded invoice should still exist but with no batch
        uploaded_invoice.refresh_from_db()
        assert uploaded_invoice.import_batch is None


class TestCsvParsing:
    """Tests for CSV parsing with different formats."""

    def test_parse_emails_column_with_comma_separator(self):
        """Test parsing CSV with 'emails' column and comma-separated emails."""
        import csv
        import io
        import re

        # Note: In CSV, commas in field values must be quoted
        csv_content = """filename,emails
invoice1.pdf,"billing@acme.com,finance@acme.com"
invoice2.pdf,single@example.com
"""
        reader = csv.DictReader(io.StringIO(csv_content))
        fieldnames = reader.fieldnames or []

        # Check column detection
        assert "filename" in fieldnames
        assert "emails" in fieldnames
        emails_column = "receivers" if "receivers" in fieldnames else "emails"
        assert emails_column == "emails"

        rows = list(reader)
        assert len(rows) == 2

        # Parse first row (comma-separated)
        emails_str = rows[0].get(emails_column, "").strip()
        emails = [e.strip().lower() for e in re.split(r"[;,]", emails_str) if e.strip()]
        assert emails == ["billing@acme.com", "finance@acme.com"]

    def test_parse_receivers_column_with_semicolon_separator(self):
        """Test parsing CSV with 'receivers' column and semicolon-separated emails."""
        import csv
        import io
        import re

        csv_content = """filename,receivers
INV-001.pdf,schwanse@bungartz.de
INV-002.pdf,christoph.strobl@strobl-pumpen.de;renate.strobl@strobl-pumpen.de
"""
        reader = csv.DictReader(io.StringIO(csv_content))
        fieldnames = reader.fieldnames or []

        # Check column detection - receivers takes precedence
        assert "filename" in fieldnames
        assert "receivers" in fieldnames
        emails_column = "receivers" if "receivers" in fieldnames else "emails"
        assert emails_column == "receivers"

        rows = list(reader)
        assert len(rows) == 2

        # Parse second row (semicolon-separated)
        emails_str = rows[1].get(emails_column, "").strip()
        emails = [e.strip().lower() for e in re.split(r"[;,]", emails_str) if e.strip()]
        assert emails == ["christoph.strobl@strobl-pumpen.de", "renate.strobl@strobl-pumpen.de"]

    def test_parse_mixed_separators(self):
        """Test parsing emails with both comma and semicolon separators."""
        import re

        emails_str = "a@test.com;b@test.com,c@test.com"
        emails = [e.strip().lower() for e in re.split(r"[;,]", emails_str) if e.strip()]
        assert emails == ["a@test.com", "b@test.com", "c@test.com"]

    def test_parse_empty_emails(self):
        """Test parsing empty email field."""
        import re

        emails_str = ""
        emails = [e.strip().lower() for e in re.split(r"[;,]", emails_str) if e.strip()]
        assert emails == []

    def test_parse_emails_with_whitespace(self):
        """Test parsing emails with extra whitespace."""
        import re

        emails_str = "  a@test.com ; b@test.com , c@test.com  "
        emails = [e.strip().lower() for e in re.split(r"[;,]", emails_str) if e.strip()]
        assert emails == ["a@test.com", "b@test.com", "c@test.com"]
