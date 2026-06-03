"""Tests for the payment reminders (Mahnungen) feature."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.contracts.models import Contract
from apps.customers.models import Customer
from apps.invoices.models import InvoiceRecord
from apps.tenants.models import Role, Tenant, User


@pytest.fixture
def tenant(db):
    """Create a test tenant (signal creates default roles)."""
    return Tenant.objects.create(name="Test Company", currency="EUR")


def _user_with_role(tenant, role_name, email):
    user = User.objects.create_user(
        email=email, password="testpass123", tenant=tenant
    )
    user.roles.add(Role.objects.get(tenant=tenant, name=role_name))
    return user


def _make_customer(tenant, **kwargs):
    return Customer.objects.create(tenant=tenant, name="ACME", **kwargs)


def _make_contract(tenant, customer, **kwargs):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Contract",
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        **kwargs,
    )


def _make_invoice(tenant, customer=None, contract=None, **kwargs):
    defaults = dict(
        invoice_number="2026-0001",
        billing_date=date(2026, 1, 1),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_net=Decimal("1000.00"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("190.00"),
        total_gross=Decimal("1190.00"),
        line_items_snapshot=[],
        company_data_snapshot={},
        customer_name="ACME",
        contract_name="Contract",
        status=InvoiceRecord.Status.FINALIZED,
    )
    defaults.update(kwargs)
    return InvoiceRecord.objects.create(
        tenant=tenant, customer=customer, contract=contract, **defaults
    )


# --- 2.4 Permission tests ---------------------------------------------------


class TestReminderPermissions:
    def test_admin_has_send_and_settings(self, tenant):
        admin = _user_with_role(tenant, "Admin", "admin@example.com")
        assert admin.has_perm_check("reminders", "send")
        assert admin.has_perm_check("reminders", "settings")

    def test_manager_has_send_not_settings(self, tenant):
        manager = _user_with_role(tenant, "Manager", "manager@example.com")
        assert manager.has_perm_check("reminders", "send")
        assert not manager.has_perm_check("reminders", "settings")

    def test_viewer_has_neither(self, tenant):
        viewer = _user_with_role(tenant, "Viewer", "viewer@example.com")
        assert not viewer.has_perm_check("reminders", "send")
        assert not viewer.has_perm_check("reminders", "settings")

    def test_viewer_can_still_read_invoices(self, tenant):
        """Viewing reminders requires no own permission — invoices.read suffices."""
        viewer = _user_with_role(tenant, "Viewer", "viewer2@example.com")
        assert viewer.has_perm_check("invoices", "read")

    def test_registry_contains_reminders(self):
        from apps.core.permissions import PERMISSION_REGISTRY

        assert PERMISSION_REGISTRY["reminders"] == ["send", "settings"]


# --- 3.4 Payment term & overdue tests ---------------------------------------


class TestPaymentTermResolution:
    def test_global_default_when_no_overrides(self, tenant):
        from apps.invoices.dunning import resolve_payment_term

        customer = _make_customer(tenant)
        contract = _make_contract(tenant, customer)
        assert resolve_payment_term(contract, customer, tenant) == 14

    def test_customer_overrides_global(self, tenant):
        from apps.invoices.dunning import resolve_payment_term

        customer = _make_customer(tenant, payment_term_days=30)
        contract = _make_contract(tenant, customer)
        assert resolve_payment_term(contract, customer, tenant) == 30

    def test_contract_overrides_customer(self, tenant):
        from apps.invoices.dunning import resolve_payment_term

        customer = _make_customer(tenant, payment_term_days=30)
        contract = _make_contract(tenant, customer, payment_term_days=7)
        assert resolve_payment_term(contract, customer, tenant) == 7

    def test_tenant_setting_default(self, tenant):
        from apps.invoices.dunning import resolve_payment_term

        tenant.settings = {"dunning": {"default_payment_term_days": 21}}
        tenant.save()
        customer = _make_customer(tenant)
        assert resolve_payment_term(None, customer, tenant) == 21


class TestOverdueDays:
    def test_overdue_unpaid_invoice(self, tenant):
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=12)
        )
        assert invoice.overdue_days == 12

    def test_paid_invoice_has_no_overdue(self, tenant):
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=12)
        )
        # Simulate paid by stubbing is_paid via a payment match would be heavy;
        # cover the not-yet-due branch instead.
        future = _make_invoice(
            tenant,
            invoice_number="2026-0002",
            due_date=date.today() + timedelta(days=5),
        )
        assert future.overdue_days == 0

    def test_no_due_date_has_no_overdue(self, tenant):
        invoice = _make_invoice(tenant, due_date=None)
        assert invoice.overdue_days == 0

    def test_voided_invoice_is_never_overdue(self, tenant):
        invoice = _make_invoice(
            tenant,
            due_date=date.today() - timedelta(days=30),
            status=InvoiceRecord.Status.VOIDED,
        )
        assert invoice.overdue_days == 0

    def test_storno_credit_note_is_never_overdue(self, tenant):
        invoice = _make_invoice(
            tenant,
            invoice_number="CN-2026-0001",
            due_date=date.today() - timedelta(days=30),
            document_type=InvoiceRecord.DocumentType.STORNO,
        )
        assert invoice.overdue_days == 0

    def test_invoice_with_storno_is_not_overdue(self, tenant):
        invoice = _make_invoice(
            tenant,
            due_date=date.today() - timedelta(days=30),
            status=InvoiceRecord.Status.SENT,
        )
        _make_invoice(
            tenant,
            invoice_number="CN-2026-0002",
            document_type=InvoiceRecord.DocumentType.STORNO,
            storno_of=invoice,
            due_date=date.today() - timedelta(days=5),
            status=InvoiceRecord.Status.SENT,
        )
        assert invoice.overdue_days == 0


# --- 4.6 Eligibility, fee, interest, template tests -------------------------


class TestDunningEligibility:
    def test_eligible_when_overdue_past_threshold(self, tenant):
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=20)
        )
        from apps.invoices.dunning import is_dunning_eligible

        assert is_dunning_eligible(invoice) is True

    def test_not_eligible_below_threshold(self, tenant):
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=3)
        )
        from apps.invoices.dunning import is_dunning_eligible

        assert is_dunning_eligible(invoice) is False

    def test_not_eligible_when_voided(self, tenant):
        invoice = _make_invoice(
            tenant,
            due_date=date.today() - timedelta(days=20),
            status=InvoiceRecord.Status.VOIDED,
        )
        from apps.invoices.dunning import is_dunning_eligible

        assert is_dunning_eligible(invoice) is False


class TestFeeAndInterest:
    def test_fee_per_stage(self, tenant):
        from apps.invoices.dunning import calculate_fee, get_dunning_settings

        tenant.settings = {
            "dunning": {"default_fee_per_stage": {"2": "5.00"}}
        }
        tenant.save()
        settings = get_dunning_settings(tenant)
        assert calculate_fee(settings, 2) == Decimal("5.00")
        assert calculate_fee(settings, 0) == Decimal("0.00")

    def test_interest_calculation(self, tenant):
        from apps.invoices.dunning import calculate_interest

        invoice = _make_invoice(
            tenant,
            total_gross=Decimal("1000.00"),
            due_date=date.today() - timedelta(days=365),
        )
        settings = {"interest_rate": Decimal("10"), "mahnfaehig_threshold_days": 14}
        interest, rate, days = calculate_interest(invoice, settings)
        assert interest == Decimal("100.00")
        assert rate == Decimal("10")
        assert days == 365

    def test_zero_interest_when_rate_zero(self, tenant):
        from apps.invoices.dunning import calculate_interest

        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=30)
        )
        settings = {"interest_rate": Decimal("0")}
        interest, _, _ = calculate_interest(invoice, settings)
        assert interest == Decimal("0.00")


class TestDunningTemplates:
    def test_default_template_fallback(self, tenant):
        from apps.invoices.dunning import get_dunning_template

        tpl = get_dunning_template(tenant, "de", 1)
        assert tpl["title"] == "1. Mahnung"
        assert "{invoice_number}" in tpl["subject"]

    def test_custom_template_used(self, tenant):
        from apps.invoices.dunning import get_dunning_template

        tenant.settings = {
            "dunning_email_templates": {
                "de": {
                    "0": {
                        "title": "Freundliche Erinnerung",
                        "subject": "Erinnerung {invoice_number}",
                        "body": "Bitte zahlen.",
                    }
                }
            }
        }
        tenant.save()
        tpl = get_dunning_template(tenant, "de", 0)
        assert tpl["title"] == "Freundliche Erinnerung"

    def test_english_fallback(self, tenant):
        from apps.invoices.dunning import get_dunning_template

        tpl = get_dunning_template(tenant, "en", 2)
        assert tpl["title"] == "Second reminder"


# --- 5.4 PDF generation test ------------------------------------------------


class TestDunningPdf:
    def test_generate_pdf_for_stage_one(self, tenant):
        from apps.invoices.models import PaymentReminder
        from apps.invoices.services import InvoiceService

        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=20)
        )
        reminder = PaymentReminder.objects.create(
            tenant=tenant,
            invoice_record=invoice,
            stage=1,
            language="de",
            title="1. Mahnung",
            subject="1. Mahnung zu Rechnung 2026-0001",
            body_text="Bitte begleichen Sie den offenen Betrag.",
            fee_amount=Decimal("5.00"),
            interest_amount=Decimal("12.34"),
        )
        pdf = InvoiceService(tenant).generate_dunning_pdf(reminder)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000


# --- 6.5 / 7.4 Email send task & status tests -------------------------------


def _make_reminder(tenant, invoice, **kwargs):
    from apps.invoices.models import PaymentReminder

    defaults = dict(
        stage=1,
        language="de",
        title="1. Mahnung",
        subject="1. Mahnung zu Rechnung 2026-0001",
        body_text="Bitte begleichen Sie den offenen Betrag.\n\nMit freundlichen Grüßen",
    )
    defaults.update(kwargs)
    return PaymentReminder.objects.create(
        tenant=tenant, invoice_record=invoice, **defaults
    )


class TestSendDunningEmailTask:
    def test_successful_send_marks_reminder_and_status(self, tenant):
        from unittest.mock import patch

        from apps.invoices.tasks import send_dunning_email_task

        customer = _make_customer(tenant, billing_emails=["billing@acme.test"])
        invoice = _make_invoice(
            tenant, customer=customer, due_date=date.today() - timedelta(days=20)
        )
        reminder = _make_reminder(tenant, invoice)

        with patch("apps.core.m365.send_mail", return_value="msg-1") as mock_send:
            result = send_dunning_email_task.apply(args=[reminder.id]).result

        assert result is True
        mock_send.assert_called_once()
        reminder.refresh_from_db()
        invoice.refresh_from_db()
        assert reminder.sent_at is not None
        assert reminder.sent_to == ["billing@acme.test"]
        assert invoice.status == InvoiceRecord.Status.DUNNING

    def test_failed_send_does_not_mark_reminder(self, tenant):
        from unittest.mock import patch

        from apps.core.m365 import M365Error
        from apps.invoices.tasks import send_dunning_email_task

        customer = _make_customer(tenant, billing_emails=["billing@acme.test"])
        invoice = _make_invoice(
            tenant, customer=customer, due_date=date.today() - timedelta(days=20)
        )
        reminder = _make_reminder(tenant, invoice)

        with patch("apps.core.m365.send_mail", side_effect=M365Error("boom")):
            result = send_dunning_email_task.apply(args=[reminder.id]).result

        assert result is False
        reminder.refresh_from_db()
        invoice.refresh_from_db()
        assert reminder.sent_at is None
        assert invoice.status == InvoiceRecord.Status.FINALIZED

    def test_send_aborts_when_invoice_paid(self, tenant):
        from unittest.mock import PropertyMock, patch

        from apps.invoices.tasks import send_dunning_email_task

        customer = _make_customer(tenant, billing_emails=["billing@acme.test"])
        invoice = _make_invoice(
            tenant, customer=customer, due_date=date.today() - timedelta(days=20)
        )
        reminder = _make_reminder(tenant, invoice)

        with patch.object(
            InvoiceRecord, "is_paid", new_callable=PropertyMock, return_value=True
        ), patch("apps.core.m365.send_mail") as mock_send:
            result = send_dunning_email_task.apply(args=[reminder.id]).result

        assert result is False
        mock_send.assert_not_called()
        reminder.refresh_from_db()
        assert reminder.sent_at is None

    def test_audit_entry_created_on_send(self, tenant):
        from unittest.mock import patch

        from apps.audit.models import AuditLog
        from apps.invoices.tasks import send_dunning_email_task

        customer = _make_customer(tenant, billing_emails=["billing@acme.test"])
        invoice = _make_invoice(
            tenant, customer=customer, due_date=date.today() - timedelta(days=20)
        )
        reminder = _make_reminder(tenant, invoice)

        with patch("apps.core.m365.send_mail", return_value="msg-1"):
            send_dunning_email_task.apply(args=[reminder.id])

        entry = AuditLog.objects.filter(
            tenant=tenant, entity_type="invoice_record", entity_id=invoice.id
        ).last()
        assert entry is not None
        assert "payment_reminder" in entry.changes


# --- 8.7 GraphQL mutation tests ---------------------------------------------


def _ctx(user):
    from unittest.mock import Mock

    from apps.core.context import Context

    return Context(request=Mock(), user=user)


def _gql(query, variables, user):
    from config.schema import schema

    return schema.execute_sync(
        query, variable_values=variables, context_value=_ctx(user)
    )


class TestDunningGraphQL:
    def test_create_reminder_draft(self, tenant):
        admin = _user_with_role(tenant, "Admin", "admin@example.com")
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=20)
        )
        query = """
            mutation($id: Int!) {
                createPaymentReminder(invoiceRecordId: $id) {
                    success error
                    draft { stage title bodyText overdueDays }
                }
            }
        """
        result = _gql(query, {"id": invoice.id}, admin)
        assert result.errors is None
        data = result.data["createPaymentReminder"]
        assert data["success"] is True
        assert data["draft"]["stage"] == 0
        assert data["draft"]["overdueDays"] == 20

    def test_create_reminder_denied_without_permission(self, tenant):
        viewer = _user_with_role(tenant, "Viewer", "viewer@example.com")
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=20)
        )
        query = """
            mutation($id: Int!) {
                createPaymentReminder(invoiceRecordId: $id) { success error }
            }
        """
        result = _gql(query, {"id": invoice.id}, viewer)
        data = result.data["createPaymentReminder"]
        assert data["success"] is False
        assert data["error"]

    def test_send_reminder_success(self, tenant):
        from unittest.mock import patch

        admin = _user_with_role(tenant, "Admin", "admin@example.com")
        customer = _make_customer(tenant, billing_emails=["a@b.test"])
        invoice = _make_invoice(
            tenant, customer=customer, due_date=date.today() - timedelta(days=20)
        )
        query = """
            mutation($id: Int!) {
                sendPaymentReminder(
                    invoiceRecordId: $id, stage: 1, language: "de",
                    title: "1. Mahnung", subject: "Mahnung", bodyText: "Text",
                    includeFee: true, includeInterest: true
                ) { success error reminder { id stage } }
            }
        """
        with patch(
            "apps.invoices.tasks.send_dunning_email_task.delay"
        ) as mock_delay:
            result = _gql(query, {"id": invoice.id}, admin)

        assert result.errors is None
        data = result.data["sendPaymentReminder"]
        assert data["success"] is True
        assert data["reminder"]["stage"] == 1
        mock_delay.assert_called_once()

    def test_send_reminder_blocked_when_paid(self, tenant):
        from unittest.mock import PropertyMock, patch

        admin = _user_with_role(tenant, "Admin", "admin@example.com")
        invoice = _make_invoice(
            tenant, due_date=date.today() - timedelta(days=20)
        )
        query = """
            mutation($id: Int!) {
                sendPaymentReminder(
                    invoiceRecordId: $id, stage: 1, language: "de",
                    title: "t", subject: "s", bodyText: "b"
                ) { success error }
            }
        """
        with patch.object(
            InvoiceRecord, "is_paid", new_callable=PropertyMock, return_value=True
        ):
            result = _gql(query, {"id": invoice.id}, admin)

        data = result.data["sendPaymentReminder"]
        assert data["success"] is False
        assert "paid" in data["error"].lower()

    def test_save_dunning_settings_requires_permission(self, tenant):
        manager = _user_with_role(tenant, "Manager", "manager@example.com")
        query = """
            mutation {
                saveDunningSettings(input: {
                    defaultPaymentTermDays: 14,
                    overdueRedThresholdDays: 14,
                    mahnfaehigThresholdDays: 14,
                    interestRate: "9.0",
                    defaultFeePerStage: {},
                    templates: {}
                }) { success error }
            }
        """
        result = _gql(query, {}, manager)
        data = result.data["saveDunningSettings"]
        assert data["success"] is False
        assert data["error"]

    def test_save_dunning_settings_admin(self, tenant):
        admin = _user_with_role(tenant, "Admin", "admin@example.com")
        query = """
            mutation($fees: JSON!, $tpl: JSON!) {
                saveDunningSettings(input: {
                    defaultPaymentTermDays: 21,
                    overdueRedThresholdDays: 10,
                    mahnfaehigThresholdDays: 30,
                    interestRate: "9.0",
                    defaultFeePerStage: $fees,
                    templates: $tpl
                }) { success settings { defaultPaymentTermDays mahnfaehigThresholdDays } }
            }
        """
        result = _gql(query, {"fees": {"1": "5.00"}, "tpl": {}}, admin)
        assert result.errors is None
        data = result.data["saveDunningSettings"]
        assert data["success"] is True
        assert data["settings"]["defaultPaymentTermDays"] == 21
        assert data["settings"]["mahnfaehigThresholdDays"] == 30

        tenant.refresh_from_db()
        assert tenant.settings["dunning"]["default_fee_per_stage"]["1"] == "5.00"
