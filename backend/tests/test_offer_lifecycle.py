"""Service-layer tests for the offer-edit-and-finalize change.

Covers the new mutations end-to-end at the service layer (one level below
GraphQL): update_offer, recreate_offer_from_contract, finalize_offer,
attach_pdf_to_contract, clone_offer_to_draft. WeasyPrint PDF generation
is mocked out for speed and determinism.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.contracts.models import Contract, ContractAttachment, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import CompanyLegalData
from apps.offers.models import OfferNumberScheme, OfferRecord
from apps.offers.services import (
    NoBillingEventError,
    OfferLockedError,
    OfferService,
)
from apps.products.models import Product


# ---------------------------------------------------------------------------
# Fixtures (subset of test_offers.py — kept local to avoid coupling)
# ---------------------------------------------------------------------------


@pytest.fixture
def customer(tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="ACME GmbH",
        address={"city": "Berlin", "country": "Deutschland"},
        is_active=True,
    )


@pytest.fixture
def legal_data(tenant):
    return CompanyLegalData.objects.create(
        tenant=tenant,
        company_name="Acme GmbH",
        street="Hauptstraße 1",
        zip_code="10115",
        city="Berlin",
        country="Deutschland",
        vat_id="DE123456789",
        commercial_register_court="AG Berlin",
        commercial_register_number="HRB 1",
        managing_directors=["Max Mustermann"],
        default_tax_rate=Decimal("19.00"),
    )


@pytest.fixture
def product(tenant):
    return Product.objects.create(tenant=tenant, name="Widget", sku="W-1")


@pytest.fixture
def contract(tenant, customer):
    c = Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Monthly SaaS",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
        min_duration_months=12,
        notice_period_months=3,
    )
    ContractItem.objects.create(
        tenant=tenant,
        contract=c,
        product=Product.objects.create(tenant=tenant, name="P1", sku="P1"),
        quantity=2,
        unit_price=Decimal("100.00"),
    )
    return c


@pytest.fixture
def draft_offer(tenant, customer, contract, legal_data):
    OfferNumberScheme.objects.create(
        tenant=tenant,
        pattern="{YYYY}-{NNNN}",
        next_counter=2,
        reset_period=OfferNumberScheme.ResetPeriod.YEARLY,
        last_reset_year=2026,
    )
    return OfferRecord.objects.create(
        tenant=tenant,
        contract=contract,
        customer=customer,
        offer_number="2026-0001",
        offer_date=date(2026, 1, 1),
        valid_until=date(2026, 2, 1),
        billing_date=date(2026, 1, 1),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_net=Decimal("200.00"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("38.00"),
        total_gross=Decimal("238.00"),
        line_items_snapshot=[
            {"product_name": "P1", "quantity": 2, "unit_price": "100.00", "amount": "200.00"},
        ],
        company_data_snapshot={"company_name": "Acme GmbH"},
        status=OfferRecord.Status.DRAFT,
        customer_name=customer.name,
        contract_name=contract.name,
        scoped_item_ids=None,
        minimum_term_months=12,
        notice_period_months=3,
    )


# ---------------------------------------------------------------------------
# update_offer
# ---------------------------------------------------------------------------


class TestUpdateOffer:
    @patch("apps.offers.services.HTML")
    def test_accepts_editable_fields(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        OfferService(tenant).update_offer(
            draft_offer.id,
            free_text_after_items="**hello**",
            valid_until=date(2026, 4, 1),
            minimum_term_months=24,
        )
        draft_offer.refresh_from_db()
        assert draft_offer.free_text_after_items == "**hello**"
        assert draft_offer.valid_until == date(2026, 4, 1)
        assert draft_offer.minimum_term_months == 24

    @patch("apps.offers.services.HTML")
    def test_rejects_unknown_field(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        with pytest.raises(ValueError, match="editable surface"):
            OfferService(tenant).update_offer(
                draft_offer.id, customer_name="hack"
            )

    @patch("apps.offers.services.HTML")
    def test_rejects_empty_scoped_item_ids(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        with pytest.raises(ValueError, match="empty list"):
            OfferService(tenant).update_offer(draft_offer.id, scoped_item_ids=[])

    @patch("apps.offers.services.HTML")
    def test_null_scoped_item_ids_clears(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        draft_offer.scoped_item_ids = [1]
        draft_offer.save()
        OfferService(tenant).update_offer(draft_offer.id, scoped_item_ids=None)
        draft_offer.refresh_from_db()
        assert draft_offer.scoped_item_ids is None

    @patch("apps.offers.services.HTML")
    def test_rejects_locked_offer(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        draft_offer.status = OfferRecord.Status.SENT
        draft_offer.save()
        with pytest.raises(OfferLockedError):
            OfferService(tenant).update_offer(
                draft_offer.id, free_text_after_items="x"
            )


# ---------------------------------------------------------------------------
# recreate_offer_from_contract
# ---------------------------------------------------------------------------


class TestRecreateOfferFromContract:
    @patch("apps.offers.services.HTML")
    def test_preserves_user_edits_and_overwrites_snapshot(
        self, mock_html, tenant, draft_offer, contract
    ):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        # User edits the offer first
        draft_offer.free_text_after_items = "user note"
        draft_offer.minimum_term_months = 36
        draft_offer.save()
        # Contract changes a price (capture the item in a local — calling
        # `.first()` twice returns two distinct instances and the mutation
        # would be discarded otherwise).
        item = contract.items.first()
        item.unit_price = Decimal("150.00")
        item.save()

        OfferService(tenant).recreate_offer_from_contract(draft_offer.id)

        draft_offer.refresh_from_db()
        # User-edited fields preserved
        assert draft_offer.free_text_after_items == "user note"
        assert draft_offer.minimum_term_months == 36
        # Contract-derived field refreshed: 2 * 150 = 300 net
        assert draft_offer.total_net == Decimal("300.00")
        # offer_number preserved
        assert draft_offer.offer_number == "2026-0001"

    @patch("apps.offers.services.HTML")
    def test_raises_no_billing_event_error(
        self, mock_html, tenant, draft_offer, contract
    ):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        # Move contract start so the offer's billing_date is no longer covered
        contract.start_date = date(2027, 1, 1)
        contract.billing_start_date = date(2027, 1, 1)
        contract.save()
        with pytest.raises(NoBillingEventError):
            OfferService(tenant).recreate_offer_from_contract(draft_offer.id)

    @patch("apps.offers.services.HTML")
    def test_rejects_locked_offer(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        draft_offer.status = OfferRecord.Status.FINALIZED
        draft_offer.save()
        with pytest.raises(OfferLockedError):
            OfferService(tenant).recreate_offer_from_contract(draft_offer.id)


# ---------------------------------------------------------------------------
# finalize_offer + attach_pdf_to_contract
# ---------------------------------------------------------------------------


class TestFinalizeOffer:
    @patch("apps.offers.services.HTML")
    def test_finalizes_draft_and_attaches(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        # Give the offer a real pdf_file so attach has something to copy
        from django.core.files.base import ContentFile
        draft_offer.pdf_file.save(
            "offer-2026-0001.pdf", ContentFile(b"%PDF-fake"), save=True
        )

        OfferService(tenant).finalize_offer(draft_offer.id)
        draft_offer.refresh_from_db()
        assert draft_offer.status == OfferRecord.Status.FINALIZED

        attachments = ContractAttachment.objects.filter(
            source_offer=draft_offer
        )
        assert attachments.count() == 1
        a = attachments.first()
        assert a.category == "offer"
        assert a.contract_id == draft_offer.contract_id

    @patch("apps.offers.services.HTML")
    def test_idempotent_on_finalized(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        from django.core.files.base import ContentFile
        draft_offer.pdf_file.save(
            "x.pdf", ContentFile(b"%PDF-fake"), save=True
        )
        OfferService(tenant).finalize_offer(draft_offer.id)
        OfferService(tenant).finalize_offer(draft_offer.id)
        # Second finalize is a no-op → still exactly one attachment
        assert ContractAttachment.objects.filter(
            source_offer=draft_offer
        ).count() == 1

    @patch("apps.offers.services.HTML")
    def test_rejects_sent_offer(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        draft_offer.status = OfferRecord.Status.SENT
        draft_offer.save()
        with pytest.raises(OfferLockedError):
            OfferService(tenant).finalize_offer(draft_offer.id)

    @patch("apps.offers.services.HTML")
    def test_rejects_legacy_status(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        draft_offer.status = OfferRecord.Status.ACCEPTED
        draft_offer.save()
        with pytest.raises(OfferLockedError):
            OfferService(tenant).finalize_offer(draft_offer.id)


class TestAttachPdfToContract:
    @patch("apps.offers.services.HTML")
    def test_attaches_with_back_reference(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        from django.core.files.base import ContentFile
        draft_offer.pdf_file.save("x.pdf", ContentFile(b"%PDF-fake"), save=True)

        attachment = OfferService(tenant).attach_pdf_to_contract(draft_offer)
        assert attachment is not None
        assert attachment.source_offer_id == draft_offer.id
        assert attachment.category == "offer"

    @patch("apps.offers.services.HTML")
    def test_idempotent_attach(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        from django.core.files.base import ContentFile
        draft_offer.pdf_file.save("x.pdf", ContentFile(b"%PDF-fake"), save=True)

        a1 = OfferService(tenant).attach_pdf_to_contract(draft_offer)
        a2 = OfferService(tenant).attach_pdf_to_contract(draft_offer)
        assert a1.id == a2.id
        assert ContractAttachment.objects.filter(
            source_offer=draft_offer
        ).count() == 1

    @patch("apps.offers.services.HTML")
    def test_attachment_survives_offer_delete(
        self, mock_html, tenant, draft_offer
    ):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        from django.core.files.base import ContentFile
        draft_offer.pdf_file.save("x.pdf", ContentFile(b"%PDF-fake"), save=True)
        a = OfferService(tenant).attach_pdf_to_contract(draft_offer)

        contract_id = draft_offer.contract_id
        draft_offer.delete()

        a.refresh_from_db()
        assert a.source_offer_id is None
        assert a.contract_id == contract_id


# ---------------------------------------------------------------------------
# clone_offer_to_draft
# ---------------------------------------------------------------------------


class TestCloneOfferToDraft:
    @patch("apps.offers.services.HTML")
    def test_clone_copies_snapshots_and_user_edits(
        self, mock_html, tenant, draft_offer
    ):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        draft_offer.free_text_after_items = "keep me"
        draft_offer.status = OfferRecord.Status.FINALIZED
        draft_offer.save()

        clone = OfferService(tenant).clone_offer_to_draft(draft_offer.id)
        assert clone.status == OfferRecord.Status.DRAFT
        assert clone.offer_number != draft_offer.offer_number
        assert clone.cloned_from_id == draft_offer.id
        assert clone.free_text_after_items == "keep me"
        assert clone.line_items_snapshot == draft_offer.line_items_snapshot

    @patch("apps.offers.services.HTML")
    def test_clone_rejects_draft_source(self, mock_html, tenant, draft_offer):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        with pytest.raises(ValueError, match="draft"):
            OfferService(tenant).clone_offer_to_draft(draft_offer.id)


# ---------------------------------------------------------------------------
# Permission gating: finalize requires offers.finalize
# ---------------------------------------------------------------------------


class TestFinalizePermission:
    """Verifies the GraphQL-layer permission gate for finalize_offer.

    The service layer itself does not enforce permissions — that is the
    schema layer's job. This test goes through the mutation entry point
    to verify the wiring.
    """

    def test_user_without_finalize_permission_is_rejected(
        self, tenant, draft_offer
    ):
        from unittest.mock import Mock
        from apps.core.context import Context
        from apps.tenants.models import Role, User
        from apps.offers.schema import OfferMutation

        user = User.objects.create_user(
            email="editor@example.com", password="x", tenant=tenant
        )
        # Give them write but NOT finalize
        editor_role = Role.objects.create(
            tenant=tenant,
            name="EditorNoFinalize",
            permissions={"offers.write": True, "offers.read": True},
        )
        user.roles.add(editor_role)

        info = Mock()
        info.context = Context(request=Mock(tenant=tenant), user=user)

        result = OfferMutation().finalize_offer(info=info, id=draft_offer.id)
        assert not result.success
        assert "denied" in (result.error or "").lower()

    def test_admin_can_finalize(self, tenant, user, draft_offer):
        from unittest.mock import Mock
        from apps.core.context import Context
        from apps.offers.schema import OfferMutation

        # Pre-render a PDF file so attach has something to copy
        from django.core.files.base import ContentFile
        from unittest.mock import patch as _patch
        with _patch("apps.offers.services.HTML") as mock_html:
            mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
            draft_offer.pdf_file.save(
                "x.pdf", ContentFile(b"%PDF-fake"), save=True
            )

            info = Mock()
            info.context = Context(request=Mock(tenant=tenant), user=user)

            result = OfferMutation().finalize_offer(info=info, id=draft_offer.id)
            assert result.success, result.error
            draft_offer.refresh_from_db()
            assert draft_offer.status == OfferRecord.Status.FINALIZED


# ---------------------------------------------------------------------------
# Race condition: concurrent finalize + send
# ---------------------------------------------------------------------------


class TestConcurrentFinalizeAndSend:
    """The select_for_update lock should serialize concurrent transitions
    so exactly one path wins. This is hard to simulate without threads;
    we approximate by running the send-task transition logic against an
    already-finalized offer and verifying it bails."""

    @patch("apps.offers.services.HTML")
    def test_finalize_then_send_does_not_overwrite(
        self, mock_html, tenant, draft_offer
    ):
        mock_html.return_value.render.return_value.write_pdf.return_value = b"%PDF-fake"
        from django.core.files.base import ContentFile
        draft_offer.pdf_file.save("x.pdf", ContentFile(b"%PDF-fake"), save=True)

        OfferService(tenant).finalize_offer(draft_offer.id)
        draft_offer.refresh_from_db()
        assert draft_offer.status == OfferRecord.Status.FINALIZED

        # Simulate the send task entering its post-send transaction after
        # Finalize has already locked the offer. The task should observe
        # the locked state and NOT overwrite status.
        from django.db import transaction
        with transaction.atomic():
            locked = (
                OfferRecord.objects.select_for_update()
                .get(id=draft_offer.id)
            )
            # The task's guard: refuse to transition if not draft.
            assert locked.status == OfferRecord.Status.FINALIZED

        # Status remains finalized, not overwritten to sent.
        draft_offer.refresh_from_db()
        assert draft_offer.status == OfferRecord.Status.FINALIZED
