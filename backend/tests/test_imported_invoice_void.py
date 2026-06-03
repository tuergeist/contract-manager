"""Tests for void / credit-note linking on ImportedInvoice."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from apps.core.context import Context
from apps.customers.models import Customer
from apps.invoices.models import ImportedInvoice
from apps.invoices.schema import InvoiceMutation as Mutation
from apps.tenants.models import Role, Tenant, User


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="VoidTest")


@pytest.fixture
def user(tenant):
    u = User.objects.create_user(
        email="void@test.com",
        password="test1234",
        tenant=tenant,
        is_admin=True,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def customer(tenant):
    return Customer.objects.create(tenant=tenant, name="Test Co")


@pytest.fixture
def invoice(tenant, user, customer):
    return ImportedInvoice.objects.create(
        tenant=tenant,
        invoice_number="INV-2026-001",
        invoice_date=date(2026, 1, 1),
        total_amount=Decimal("100.00"),
        currency="EUR",
        customer_name="Test Co",
        customer=customer,
        original_filename="inv.pdf",
        file_size=100,
        extraction_status=ImportedInvoice.ExtractionStatus.CONFIRMED,
        created_by=user,
    )


@pytest.fixture
def credit_note(tenant, user, customer):
    return ImportedInvoice.objects.create(
        tenant=tenant,
        invoice_number="CN-2026-001",
        invoice_date=date(2026, 1, 5),
        total_amount=Decimal("100.00"),
        currency="EUR",
        customer_name="Test Co",
        customer=customer,
        original_filename="cn.pdf",
        file_size=80,
        extraction_status=ImportedInvoice.ExtractionStatus.CONFIRMED,
        created_by=user,
    )


def _make_info(user):
    request = Mock()
    request.tenant = user.tenant
    ctx = Context(request=request, user=user)
    info = Mock()
    info.context = ctx
    return info


def _Info(user):
    return _make_info(user)


def _mutation():
    return Mutation()


class TestVoidImportedInvoice:
    def test_void_marks_invoice_voided(self, invoice, user):
        info = _Info(user)
        result = _mutation().void_imported_invoice(
            info, invoice_id=str(invoice.id), reason="Wrong amount"
        )
        assert result.success, result.error
        invoice.refresh_from_db()
        assert invoice.is_voided
        assert invoice.void_reason == "Wrong amount"
        assert invoice.voided_at is not None
        assert invoice.voided_by_id == user.id

    def test_void_rejects_empty_reason(self, invoice, user):
        info = _Info(user)
        result = _mutation().void_imported_invoice(
            info, invoice_id=str(invoice.id), reason="   "
        )
        assert not result.success
        assert "reason" in result.error.lower()

    def test_void_with_credit_note_links(self, invoice, credit_note, user):
        info = _Info(user)
        result = _mutation().void_imported_invoice(
            info,
            invoice_id=str(invoice.id),
            reason="Replaced",
            credit_note_id=str(credit_note.id),
        )
        assert result.success, result.error
        credit_note.refresh_from_db()
        invoice.refresh_from_db()
        assert credit_note.is_credit_note
        assert credit_note.storno_of_id == invoice.id
        assert invoice.is_voided

    def test_double_void_rejected(self, invoice, user):
        info = _Info(user)
        first = _mutation().void_imported_invoice(
            info, invoice_id=str(invoice.id), reason="a"
        )
        assert first.success
        second = _mutation().void_imported_invoice(
            info, invoice_id=str(invoice.id), reason="b"
        )
        assert not second.success


class TestLinkImportedCreditNote:
    def test_link_voids_target(self, invoice, credit_note, user):
        info = _Info(user)
        result = _mutation().link_imported_credit_note(
            info,
            credit_note_id=str(credit_note.id),
            target_invoice_id=str(invoice.id),
        )
        assert result.success, result.error
        invoice.refresh_from_db()
        credit_note.refresh_from_db()
        assert invoice.is_voided
        assert credit_note.is_credit_note
        assert credit_note.storno_of_id == invoice.id

    def test_link_self_rejected(self, invoice, user):
        info = _Info(user)
        result = _mutation().link_imported_credit_note(
            info,
            credit_note_id=str(invoice.id),
            target_invoice_id=str(invoice.id),
        )
        assert not result.success


class TestUnlinkImportedCreditNote:
    def test_unlink_restores_target(self, invoice, credit_note, user):
        info = _Info(user)
        _mutation().link_imported_credit_note(
            info,
            credit_note_id=str(credit_note.id),
            target_invoice_id=str(invoice.id),
        )
        result = _mutation().unlink_imported_credit_note(
            info, credit_note_id=str(credit_note.id)
        )
        assert result.success, result.error
        invoice.refresh_from_db()
        credit_note.refresh_from_db()
        assert not invoice.is_voided
        assert not credit_note.is_credit_note

    def test_unlink_keep_voided(self, invoice, credit_note, user):
        info = _Info(user)
        _mutation().link_imported_credit_note(
            info,
            credit_note_id=str(credit_note.id),
            target_invoice_id=str(invoice.id),
        )
        result = _mutation().unlink_imported_credit_note(
            info,
            credit_note_id=str(credit_note.id),
            keep_target_voided=True,
        )
        assert result.success
        invoice.refresh_from_db()
        assert invoice.is_voided


class TestUnvoidImportedInvoice:
    def test_unvoid_restores_invoice(self, invoice, user):
        info = _Info(user)
        _mutation().void_imported_invoice(
            info, invoice_id=str(invoice.id), reason="x"
        )
        result = _mutation().unvoid_imported_invoice(
            info, invoice_id=str(invoice.id)
        )
        assert result.success, result.error
        invoice.refresh_from_db()
        assert not invoice.is_voided
        # invoice has invoice_date set → restored to SENT
        assert invoice.extraction_status == ImportedInvoice.ExtractionStatus.SENT
        assert invoice.void_reason == ""
        assert invoice.voided_at is None


class TestSentDateLifecycle:
    def test_confirm_with_invoice_date_goes_to_sent(self, tenant, user, customer):
        inv = ImportedInvoice.objects.create(
            tenant=tenant,
            invoice_number="X-1",
            invoice_date=date(2026, 2, 1),
            total_amount=Decimal("50.00"),
            currency="EUR",
            customer_name="Test Co",
            customer=customer,
            original_filename="x.pdf",
            file_size=10,
            extraction_status=ImportedInvoice.ExtractionStatus.EXTRACTED,
            created_by=user,
        )
        info = _Info(user)
        result = _mutation().confirm_invoice(info, id=str(inv.id))
        assert result.success, result.error
        inv.refresh_from_db()
        assert inv.extraction_status == ImportedInvoice.ExtractionStatus.SENT

    def test_confirm_without_invoice_date_stays_confirmed(self, tenant, user, customer):
        inv = ImportedInvoice.objects.create(
            tenant=tenant,
            invoice_number="X-2",
            invoice_date=None,
            total_amount=Decimal("50.00"),
            currency="EUR",
            customer_name="Test Co",
            customer=customer,
            original_filename="x.pdf",
            file_size=10,
            extraction_status=ImportedInvoice.ExtractionStatus.EXTRACTED,
            created_by=user,
        )
        info = _Info(user)
        result = _mutation().confirm_invoice(info, id=str(inv.id))
        assert result.success, result.error
        inv.refresh_from_db()
        assert inv.extraction_status == ImportedInvoice.ExtractionStatus.CONFIRMED
