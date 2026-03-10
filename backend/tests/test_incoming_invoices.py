"""Tests for incoming invoice import: polling, extraction, counterparty matching, GraphQL."""
from decimal import Decimal
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.core.files.base import ContentFile

from apps.banking.models import Counterparty, IncomingInvoice, InvoiceInbox
from apps.banking.services.inbox_polling import InboxPollingService
from apps.banking.services.incoming_extraction import (
    _auto_assign_counterparty,
    _parse_amount,
    run_incoming_extraction,
)
from apps.core.context import Context
from apps.core.permissions import PERMISSION_REGISTRY, DEFAULT_ROLES
from config.schema import schema


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    return Context(request=Mock(), user=user)


@pytest.fixture
def inbox(db, tenant):
    return InvoiceInbox.objects.create(
        tenant=tenant, name="Test IMAP", inbox_type="imap",
        host="mail.example.com", port=993, username="test@example.com",
        password="secret", folder="INBOX", use_ssl=True,
    )


@pytest.fixture
def m365_inbox(db, tenant):
    return InvoiceInbox.objects.create(
        tenant=tenant, name="Test M365", inbox_type="m365",
        m365_mailbox="invoices@company.com",
    )


@pytest.fixture
def counterparty(db, tenant):
    return Counterparty.objects.create(tenant=tenant, name="Acme Corp", iban="DE89370400440532013000")


@pytest.fixture
def incoming_invoice(db, tenant, inbox):
    inv = IncomingInvoice(
        tenant=tenant, inbox=inbox, original_filename="invoice.pdf",
        file_size=1024, email_message_id="<test@example.com>",
        source_email_subject="Invoice",
        extraction_status=IncomingInvoice.ExtractionStatus.PENDING,
    )
    inv.pdf_file.save("test.pdf", ContentFile(b"%PDF-1.4 test"), save=False)
    inv.save()
    return inv


# === Permission Tests ===

class TestPermissions:
    def test_in_registry(self):
        assert "incoming_invoices" in PERMISSION_REGISTRY
        assert set(PERMISSION_REGISTRY["incoming_invoices"]) == {"read", "write", "config"}

    def test_manager_has_read_write(self):
        assert DEFAULT_ROLES["Manager"].get("incoming_invoices.read") is True
        assert DEFAULT_ROLES["Manager"].get("incoming_invoices.write") is True

    def test_manager_no_config(self):
        assert DEFAULT_ROLES["Manager"].get("incoming_invoices.config") is not True

    def test_viewer_has_read(self):
        assert DEFAULT_ROLES["Viewer"].get("incoming_invoices.read") is True

    def test_viewer_no_write(self):
        assert DEFAULT_ROLES["Viewer"].get("incoming_invoices.write") is not True

    def test_admin_has_all(self):
        for perm in ["read", "write", "config"]:
            assert DEFAULT_ROLES["Admin"].get(f"incoming_invoices.{perm}") is True


# === IMAP Polling Tests ===

def _make_email_with_pdf(message_id, subject, filename="invoice.pdf"):
    msg = MIMEMultipart()
    msg["Message-ID"] = message_id
    msg["Subject"] = subject
    msg["Date"] = "Mon, 01 Jan 2024 10:00:00 +0000"
    msg.attach(MIMEText("Please find invoice attached."))
    pdf = MIMEApplication(b"%PDF-1.4 test", _subtype="pdf")
    pdf.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(pdf)
    return msg


def _make_email_no_pdf(message_id, subject):
    msg = MIMEMultipart()
    msg["Message-ID"] = message_id
    msg["Subject"] = subject
    msg["Date"] = "Mon, 01 Jan 2024 10:00:00 +0000"
    msg.attach(MIMEText("No invoice here."))
    return msg


class TestIMAPPolling:
    @patch("apps.banking.services.inbox_polling.imaplib")
    def test_new_email_creates_record(self, mock_imaplib, db, tenant, inbox):
        mock_conn = MagicMock()
        mock_imaplib.IMAP4_SSL.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        email_msg = _make_email_with_pdf("<msg1@test.com>", "Invoice 001")
        mock_conn.fetch.return_value = ("OK", [(b"1", email_msg.as_bytes())])

        created = InboxPollingService()._poll_imap(inbox)
        assert len(created) == 1
        assert created[0].original_filename == "invoice.pdf"
        assert created[0].email_message_id == "<msg1@test.com>"

    @patch("apps.banking.services.inbox_polling.imaplib")
    def test_duplicate_skipped(self, mock_imaplib, db, tenant, inbox):
        IncomingInvoice.objects.create(
            tenant=tenant, inbox=inbox, original_filename="invoice.pdf",
            email_message_id="<msg1@test.com>", extraction_status="pending", pdf_file="test.pdf",
        )
        mock_conn = MagicMock()
        mock_imaplib.IMAP4_SSL.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = ("OK", [(b"1", _make_email_with_pdf("<msg1@test.com>", "Invoice 001").as_bytes())])

        assert len(InboxPollingService()._poll_imap(inbox)) == 0

    @patch("apps.banking.services.inbox_polling.imaplib")
    def test_no_pdf_skipped(self, mock_imaplib, db, tenant, inbox):
        mock_conn = MagicMock()
        mock_imaplib.IMAP4_SSL.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = ("OK", [(b"1", _make_email_no_pdf("<msg2@test.com>", "No invoice").as_bytes())])

        assert len(InboxPollingService()._poll_imap(inbox)) == 0


# === Extraction Tests ===

class TestExtraction:
    def test_parse_amount_german(self):
        assert _parse_amount("1.234,56") == Decimal("1234.56")
        assert _parse_amount("1234,56") == Decimal("1234.56")
        assert _parse_amount("1234.56") == Decimal("1234.56")
        assert _parse_amount(None) is None

    @patch("apps.banking.services.incoming_extraction.extract_incoming_invoice_metadata")
    def test_extraction_success(self, mock_extract, db, tenant, incoming_invoice):
        from django.conf import settings
        settings.ANTHROPIC_API_KEY = "test-key"
        mock_extract.return_value = {
            "supplier_name": "Test GmbH", "invoice_number": "RE-2024-001",
            "invoice_date": "2024-01-15", "due_date": "2024-02-15",
            "net_amount": "1000.00", "vat_amount": "190.00", "gross_amount": "1190.00",
            "currency": "EUR", "iban": None,
        }
        assert run_incoming_extraction(incoming_invoice) is True
        incoming_invoice.refresh_from_db()
        assert incoming_invoice.supplier_name == "Test GmbH"
        assert incoming_invoice.gross_amount == Decimal("1190.00")
        assert incoming_invoice.extraction_status == "extracted"

    @patch("apps.banking.services.incoming_extraction.extract_incoming_invoice_metadata")
    def test_extraction_failure(self, mock_extract, db, tenant, incoming_invoice):
        from django.conf import settings
        settings.ANTHROPIC_API_KEY = "test-key"
        mock_extract.side_effect = Exception("API error")
        assert run_incoming_extraction(incoming_invoice) is False
        incoming_invoice.refresh_from_db()
        assert incoming_invoice.extraction_status == "extraction_failed"


# === Counterparty Assignment ===

class TestCounterpartyAssignment:
    def test_match_by_iban(self, db, tenant, counterparty, incoming_invoice):
        incoming_invoice.supplier_name = "Some Name"
        incoming_invoice.save()
        _auto_assign_counterparty(incoming_invoice, "DE89370400440532013000")
        incoming_invoice.refresh_from_db()
        assert incoming_invoice.counterparty == counterparty

    def test_match_by_name(self, db, tenant, counterparty, incoming_invoice):
        incoming_invoice.supplier_name = "Acme Corp GmbH"
        incoming_invoice.save()
        _auto_assign_counterparty(incoming_invoice)
        incoming_invoice.refresh_from_db()
        assert incoming_invoice.counterparty == counterparty

    def test_no_match(self, db, tenant, counterparty, incoming_invoice):
        incoming_invoice.supplier_name = "Unknown Vendor"
        incoming_invoice.save()
        _auto_assign_counterparty(incoming_invoice)
        incoming_invoice.refresh_from_db()
        assert incoming_invoice.counterparty is None


# === GraphQL Queries ===

class TestGraphQLQueries:
    def test_list(self, db, user, tenant, incoming_invoice):
        r = run_graphql("{ incomingInvoices { items { id originalFilename } totalCount } }", {}, make_context(user))
        assert r.errors is None
        assert r.data["incomingInvoices"]["totalCount"] == 1

    def test_filter_by_status(self, db, user, tenant, incoming_invoice):
        r = run_graphql('query($s: String) { incomingInvoices(status: $s) { totalCount } }', {"s": "extracted"}, make_context(user))
        assert r.errors is None
        assert r.data["incomingInvoices"]["totalCount"] == 0

    def test_detail(self, db, user, tenant, incoming_invoice):
        r = run_graphql("query($id: ID!) { incomingInvoice(id: $id) { id originalFilename } }", {"id": str(incoming_invoice.id)}, make_context(user))
        assert r.errors is None
        assert r.data["incomingInvoice"]["originalFilename"] == "invoice.pdf"

    def test_search(self, db, user, tenant, incoming_invoice):
        incoming_invoice.supplier_name = "Searchable Vendor"
        incoming_invoice.save()
        r = run_graphql('query($s: String) { incomingInvoices(search: $s) { totalCount } }', {"s": "Searchable"}, make_context(user))
        assert r.data["incomingInvoices"]["totalCount"] == 1


# === GraphQL Mutations ===

class TestGraphQLMutations:
    def test_update(self, db, user, tenant, incoming_invoice):
        r = run_graphql(
            'mutation($i: UpdateIncomingInvoiceInput!) { updateIncomingInvoice(input: $i) { success invoice { supplierName } } }',
            {"i": {"id": str(incoming_invoice.id), "supplierName": "Updated"}}, make_context(user),
        )
        assert r.errors is None
        assert r.data["updateIncomingInvoice"]["success"] is True
        assert r.data["updateIncomingInvoice"]["invoice"]["supplierName"] == "Updated"

    def test_delete(self, db, user, tenant, incoming_invoice):
        inv_id = str(incoming_invoice.id)
        r = run_graphql('mutation($id: ID!) { deleteIncomingInvoice(id: $id) { success } }', {"id": inv_id}, make_context(user))
        assert r.errors is None
        assert r.data["deleteIncomingInvoice"]["success"] is True
        assert not IncomingInvoice.objects.filter(id=inv_id).exists()


# === Inbox CRUD ===

class TestInboxCRUD:
    def test_create(self, db, user, tenant):
        r = run_graphql(
            'mutation($i: CreateInvoiceInboxInput!) { createInvoiceInbox(input: $i) { success inbox { id name } } }',
            {"i": {"name": "New Inbox", "inboxType": "imap", "host": "mail.test.com"}}, make_context(user),
        )
        assert r.errors is None
        assert r.data["createInvoiceInbox"]["success"] is True

    def test_update(self, db, user, tenant, inbox):
        r = run_graphql(
            'mutation($i: UpdateInvoiceInboxInput!) { updateInvoiceInbox(input: $i) { success inbox { name } } }',
            {"i": {"id": str(inbox.id), "name": "Renamed"}}, make_context(user),
        )
        assert r.errors is None
        assert r.data["updateInvoiceInbox"]["success"] is True

    def test_delete(self, db, user, tenant, inbox):
        r = run_graphql('mutation($id: ID!) { deleteInvoiceInbox(id: $id) { success } }', {"id": str(inbox.id)}, make_context(user))
        assert r.data["deleteInvoiceInbox"]["success"] is True

    def test_list(self, db, user, tenant, inbox):
        r = run_graphql("{ invoiceInboxes { id name } }", {}, make_context(user))
        assert r.errors is None
        assert len(r.data["invoiceInboxes"]) == 1


# === Tenant Isolation ===

class TestTenantIsolation:
    def test_invoices(self, db, user, tenant):
        from apps.tenants.models import Tenant
        other = Tenant.objects.create(name="Other Corp", currency="EUR")
        other_inbox = InvoiceInbox.objects.create(tenant=other, name="Other", inbox_type="imap")
        IncomingInvoice.objects.create(tenant=other, inbox=other_inbox, original_filename="x.pdf", extraction_status="pending", pdf_file="x.pdf")
        r = run_graphql("{ incomingInvoices { totalCount } }", {}, make_context(user))
        assert r.data["incomingInvoices"]["totalCount"] == 0

    def test_inboxes(self, db, user, tenant):
        from apps.tenants.models import Tenant
        other = Tenant.objects.create(name="Other Corp 2", currency="EUR")
        InvoiceInbox.objects.create(tenant=other, name="Other 2", inbox_type="m365")
        r = run_graphql("{ invoiceInboxes { id } }", {}, make_context(user))
        assert len(r.data["invoiceInboxes"]) == 0
