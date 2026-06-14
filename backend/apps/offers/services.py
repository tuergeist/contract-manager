"""Offer service for generating offers from contract billing schedules."""
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Literal

from django.db import IntegrityError, transaction
from django.template.loader import render_to_string

try:
    from weasyprint import HTML
except ImportError:
    HTML = None

from apps.contracts.models import Contract
from apps.invoices.services import (
    _classify_customer,
    _get_vat_sentence,
)
from apps.tenants.models import Tenant

# Localization labels for offer PDF
LABELS = {
    "de": {
        "offer": "Angebot",
        "offer_no": "Angebotsnr.",
        "bill_to": "Rechnungsadresse",
        "offer_date": "Angebotsdatum",
        "valid_until": "Gültig bis",
        "billing_period": "Abrechnungszeitraum",
        "service_period": "Leistungszeitraum",
        "contract": "Vertrag",
        "description": "Beschreibung",
        "quantity": "Menge",
        "unit_price": "Einzelpreis",
        "per_month": "/Monat",
        "amount": "Betrag",
        "net_total": "Nettobetrag",
        "tax": "MwSt.",
        "gross_total": "Bruttobetrag",
        "total": "Gesamtbetrag",
        "one_off": "Einmalig",
        "offer_amount": "Angebotsbetrag",
        "customer_id": "Kunden-Nr.",
        "customer_vat_id": "USt-IdNr.",
        "vat_id": "USt-IdNr.",
        "tax_number": "Steuernummer",
        "register": "Handelsregister",
        "managing_directors": "Geschäftsführer",
        "share_capital": "Stammkapital",
        "bank_details": "Bankverbindung",
        "phone": "Telefon",
        "pos": "Pos.",
        "date_label": "Datum",
        "notes_label": "Anmerkungen",
    },
    "en": {
        "offer": "Offer",
        "offer_no": "Offer No.",
        "bill_to": "Bill To",
        "offer_date": "Offer Date",
        "valid_until": "Valid Until",
        "billing_period": "Billing Period",
        "service_period": "Service Period",
        "contract": "Contract",
        "description": "Description",
        "quantity": "Qty",
        "unit_price": "Unit Price",
        "per_month": "/mo.",
        "amount": "Amount",
        "net_total": "Net Total",
        "tax": "VAT",
        "gross_total": "Gross Total",
        "total": "Total",
        "one_off": "One-time",
        "offer_amount": "Offer Total",
        "customer_id": "Customer ID",
        "customer_vat_id": "VAT ID",
        "vat_id": "VAT ID",
        "tax_number": "Tax Number",
        "register": "Commercial Register",
        "managing_directors": "Managing Directors",
        "share_capital": "Share Capital",
        "bank_details": "Bank Details",
        "phone": "Phone",
        "pos": "Pos.",
        "date_label": "Date",
        "notes_label": "Notes",
    },
}


def _render_minimum_term_line(
    months: int | None, language: str
) -> str:
    """Return the rendered minimum-term sentence, or empty string."""
    if not months or months <= 0:
        return ""
    if language == "de":
        return (
            f"Mindestlaufzeit {months} Monate ab Vertragsbeginn."
        )
    return (
        f"Minimum term {months} months from the contract start date."
    )


def _render_notice_period_line(
    months: int | None, language: str
) -> str:
    """Return the rendered notice-period sentence, or empty string."""
    if not months or months <= 0:
        return ""
    if language == "de":
        return (
            f"Kündigungsfrist {months} Monate zum Ende der "
            f"Mindestvertragslaufzeit."
        )
    return (
        f"Notice period {months} months to the end of the minimum term."
    )


class OfferLockedError(Exception):
    """Raised when a mutation is attempted on a non-draft offer.

    Mapped to a typed GraphQL error in the schema layer so callers see a
    structured response rather than a generic 500.
    """

    def __init__(self, offer_id: int, status: str):
        self.offer_id = offer_id
        self.status = status
        super().__init__(
            f"OfferRecord {offer_id} is locked (status={status}); only "
            "drafts may be modified."
        )


class NoBillingEventError(Exception):
    """Raised when recreate_offer_from_contract cannot find a billing event
    on the offer's billing_date after the contract was edited."""


class OfferService:
    """Service for generating offers from contract billing schedules."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    # ------------------------------------------------------------------ #
    # Lock enforcement — single guard called by every mutation that writes
    # to an existing offer. See design.md::Decision 2.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _guard_writable(record) -> None:
        """Raise OfferLockedError if the offer is not editable.

        Caller MUST have acquired a row-level lock on `record` (e.g. via
        `select_for_update`) before invoking the guard, otherwise a
        concurrent finalize/send may slip past the check.
        """
        from apps.offers.models import OfferRecord

        if record.status != OfferRecord.Status.DRAFT:
            raise OfferLockedError(record.id, record.status)

    def create_offer(self, contract_id: int, billing_date: date, item_ids: list[int] | None = None) -> "OfferRecord":
        """Create an offer from a contract's billing event.

        Computes the billing event for the given date, snapshots line items
        and company data, assigns an offer number, generates a PDF, and
        returns the created OfferRecord.

        Args:
            item_ids: Optional list of contract item IDs to scope the offer to.
                      If provided, only those items are included in the snapshot.
        """
        from apps.invoices.models import CompanyLegalData
        from apps.offers.models import OfferRecord
        from apps.offers.numbering import OfferNumberService
        from dateutil.relativedelta import relativedelta

        contract = Contract.objects.select_related("customer").prefetch_related(
            "items__product"
        ).get(id=contract_id, tenant=self.tenant)

        # Get legal data
        try:
            legal_data = self.tenant.legal_data
        except CompanyLegalData.DoesNotExist:
            raise ValueError(
                "Company legal data must be configured before generating offers."
            )

        # Get billing schedule to find the matching event
        billing_events = contract.get_billing_schedule(
            from_date=billing_date,
            to_date=billing_date,
            include_history=True,
        )

        # Find the event matching the billing_date
        event = None
        for e in billing_events:
            if e["date"] == billing_date:
                event = e
                break

        if event is None or not event.get("items"):
            raise ValueError(
                f"No billing event found for contract {contract_id} on {billing_date}."
            )

        # Calculate billing period
        interval_months = contract.get_interval_months()
        period_start = billing_date
        period_end = billing_date + relativedelta(months=interval_months, days=-1)
        if contract.end_date and period_end > contract.end_date:
            period_end = contract.end_date

        # Classify customer for tax
        company_country = legal_data.country
        customer_address = contract.customer.address or {}
        classification = _classify_customer(company_country, customer_address)
        domestic = classification == "domestic"
        default_tax_rate = legal_data.default_tax_rate
        tax_rate = default_tax_rate if domestic else Decimal("0.00")
        vat_sentence = _get_vat_sentence(classification, legal_data)

        # Build line items snapshot
        contract_items_by_id = {ci.id: ci for ci in contract.items.all()}
        item_ids_set = set(item_ids) if item_ids else None
        line_items_snapshot = []
        total_net = Decimal("0.00")
        for item in event["items"]:
            # Skip items not in scope if item_ids provided
            if item_ids_set and item["item_id"] not in item_ids_set:
                continue
            amount = item["amount"]
            total_net += amount
            line_items_snapshot.append({
                "item_id": item["item_id"],
                "product_name": item["product_name"],
                "description": item.get("description", ""),
                "quantity": item["quantity"],
                "unit_price": str(item["unit_price"]),
                "amount": str(amount),
                "is_prorated": item.get("is_prorated", False),
                "prorate_factor": str(item["prorate_factor"]) if item.get("prorate_factor") else None,
                "is_one_off": item.get("is_one_off", False),
            })

        # Calculate tax
        tax_amount = (total_net * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        total_gross = total_net + tax_amount

        # Company data snapshot
        company_snapshot = legal_data.to_snapshot()

        # Assign offer number
        numbering = OfferNumberService(self.tenant)

        # Valid until: 30 days from today by default
        today = date.today()
        valid_until = today + relativedelta(days=30)

        # Retry on duplicate offer_number — happens when the scheme counter
        # falls behind existing records (e.g. an offer with the same number
        # was created out-of-band, or a delete + re-create races).
        #
        # Two correctness requirements:
        # 1. The scheme counter increment must NOT roll back when the
        #    OfferRecord insert fails — otherwise we loop forever on the
        #    same number. get_next_number() has its own transaction.atomic()
        #    and runs first, so the increment is already committed (or held
        #    at the savepoint above this loop).
        # 2. The failing INSERT must not poison the surrounding transaction;
        #    we wrap each attempt in its own atomic() block so the savepoint
        #    rolls back on IntegrityError without leaving the connection in
        #    a broken-transaction state.
        max_attempts = 10
        record = None
        for attempt in range(max_attempts):
            offer_number = numbering.get_next_number(billing_date)
            try:
                with transaction.atomic():
                    record = OfferRecord.objects.create(
                        tenant=self.tenant,
                        contract=contract,
                        customer=contract.customer,
                        offer_number=offer_number,
                        offer_date=today,
                        valid_until=valid_until,
                        billing_date=billing_date,
                        period_start=period_start,
                        period_end=period_end,
                        total_net=total_net,
                        tax_rate=tax_rate,
                        tax_amount=tax_amount,
                        total_gross=total_gross,
                        line_items_snapshot=line_items_snapshot,
                        company_data_snapshot=company_snapshot,
                        status=OfferRecord.Status.DRAFT,
                        customer_name=contract.customer.name,
                        contract_name=contract.name or f"Contract {contract.id}",
                        vat_sentence=vat_sentence,
                        scoped_item_ids=item_ids,
                        # Snapshot the contract's term + notice period at
                        # create time. User may override later via
                        # update_offer; re-create preserves overrides.
                        minimum_term_months=contract.min_duration_months,
                        notice_period_months=contract.notice_period_months,
                    )
                break
            except IntegrityError:
                # Number already taken — counter was behind. Loop; the next
                # get_next_number call will advance the scheme counter.
                if attempt == max_attempts - 1:
                    raise

        assert record is not None  # Loop either sets record or raises

        # Generate PDF synchronously (offers are single-page, fast)
        language = contract.customer.get_effective_invoice_language(default="en") if contract.customer else "en"
        self._generate_and_save_pdf(record, language)

        return record

    # ====================================================================
    # Draft editing — update_offer
    # See openspec/specs/offer-edit/spec.md
    # ====================================================================
    def update_offer(self, record_id: int, **fields):
        """Update editable fields on a draft offer and regenerate the PDF.

        Only fields listed in `OfferRecord._user_editable_fields()` are
        accepted; anything else raises ValueError before touching the DB.
        Locks via `select_for_update` + `_guard_writable` so concurrent
        finalize/send cannot slip in.
        """
        from apps.offers.models import OfferRecord

        editable = OfferRecord._user_editable_fields()
        unknown = set(fields.keys()) - editable
        if unknown:
            raise ValueError(
                f"Field(s) not in update_offer's editable surface: "
                f"{sorted(unknown)}"
            )

        # scoped_item_ids special case: empty list is invalid; None means
        # implicit "all items" and is fine.
        if "scoped_item_ids" in fields:
            value = fields["scoped_item_ids"]
            if value is not None and not isinstance(value, list):
                raise ValueError("scoped_item_ids must be a list or None")
            if isinstance(value, list) and len(value) == 0:
                raise ValueError(
                    "scoped_item_ids must not be an empty list; pass None "
                    "for implicit 'all items'"
                )

        with transaction.atomic():
            record = (
                OfferRecord.objects.select_for_update()
                .select_related("contract", "customer")
                .get(id=record_id, tenant=self.tenant)
            )
            self._guard_writable(record)

            # Apply only fields explicitly passed (allow None / empty
            # string distinct from "absent").
            for key, value in fields.items():
                setattr(record, key, value)

            # If scoped_item_ids changed, recompute line items from the
            # contract's current billing event so totals stay consistent
            # with the new scope.
            if "scoped_item_ids" in fields:
                self._refresh_line_items_for_scope(record)

            record.save()

        language = (
            record.customer.get_effective_invoice_language(default="en")
            if record.customer
            else "en"
        )
        self._generate_and_save_pdf(record, language)
        return record

    # ====================================================================
    # Re-create from contract — refreshes contract-derived snapshots only
    # See openspec/specs/offer-edit/spec.md::recreate_offer_from_contract
    # ====================================================================
    def recreate_offer_from_contract(self, record_id: int):
        """Re-snapshot the contract's billing data into an existing draft.

        Preserves `_user_editable_fields()` (free-text, valid_until,
        min-term, notice-period, scoped_item_ids). Overwrites every field
        listed in `_contract_derived_fields()`. The `offer_number` is
        preserved.
        """
        from apps.offers.models import OfferRecord

        with transaction.atomic():
            record = (
                OfferRecord.objects.select_for_update()
                .select_related("contract", "customer")
                .get(id=record_id, tenant=self.tenant)
            )
            self._guard_writable(record)

            contract = record.contract
            if contract is None:
                raise NoBillingEventError(
                    "Cannot re-create offer: its contract has been deleted."
                )

            # Recompute the billing event for the offer's billing_date.
            events = contract.get_billing_schedule(
                from_date=record.billing_date,
                to_date=record.billing_date,
                include_history=True,
            )
            event = next(
                (e for e in events if e["date"] == record.billing_date), None
            )
            if event is None or not event.get("items"):
                raise NoBillingEventError(
                    f"No billing event on {record.billing_date} for "
                    f"contract {contract.id}; cannot re-create from contract."
                )

            # Re-derive snapshot fields. We deliberately do NOT touch any
            # user-editable field — the contract spec for offer-edit is the
            # source of truth.
            self._apply_event_to_record(record, contract, event)
            record.save()

        language = (
            record.customer.get_effective_invoice_language(default="en")
            if record.customer
            else "en"
        )
        self._generate_and_save_pdf(record, language)
        return record

    # ====================================================================
    # Finalize — user-driven lock + attachment copy
    # See openspec/specs/offer-finalize/spec.md
    # ====================================================================
    def finalize_offer(self, record_id: int):
        """Transition a draft offer to finalized, idempotently.

        Idempotent on already-finalized records; rejects sent (already
        locked through the other path). Attaches the offer PDF to the
        contract's attachments list as the last step.
        """
        from apps.offers.models import OfferRecord

        with transaction.atomic():
            record = (
                OfferRecord.objects.select_for_update()
                .select_related("contract")
                .get(id=record_id, tenant=self.tenant)
            )
            if record.status == OfferRecord.Status.FINALIZED:
                # Idempotent: no state change, no duplicate attachment.
                return record
            if record.status == OfferRecord.Status.SENT:
                raise OfferLockedError(record.id, record.status)
            if record.status != OfferRecord.Status.DRAFT:
                # Legacy status (accepted / rejected / cancelled). Treat
                # as locked — finalize is a forward-only operation.
                raise OfferLockedError(record.id, record.status)

            record.status = OfferRecord.Status.FINALIZED
            record.save(update_fields=["status", "updated_at"])
            self.attach_pdf_to_contract(record)

        return record

    # ====================================================================
    # Attachment copy — idempotent, real ContractAttachment row
    # See openspec/specs/offer-finalize/spec.md
    # ====================================================================
    def attach_pdf_to_contract(self, record):
        """Copy the offer's PDF onto the parent contract as an attachment.

        Idempotent: returns an existing ContractAttachment when one is
        already wired to this OfferRecord. Otherwise creates a new row
        with its own copy of the file bytes so the attachment survives
        offer deletion (FK is SET_NULL).
        """
        from django.core.files.base import ContentFile
        from apps.contracts.models import ContractAttachment

        if not record.contract_id or not record.pdf_file:
            return None

        existing = ContractAttachment.objects.filter(
            contract_id=record.contract_id,
            source_offer=record,
        ).first()
        if existing is not None:
            return existing

        # Read source bytes once, write under a fresh upload path so the
        # attachment owns its own file.
        record.pdf_file.open("rb")
        try:
            pdf_bytes = record.pdf_file.read()
        finally:
            record.pdf_file.close()

        filename = f"offer-{record.offer_number}.pdf"
        # Description follows the tenant default language. Customer
        # language is offer-local; the attachment is contract-local.
        legal = getattr(self.tenant, "legal_data", None)
        country = (legal.country if legal else "").lower()
        if country.startswith("de") or country == "deutschland":
            description = f"Angebot {record.offer_number}"
        else:
            description = f"Offer {record.offer_number}"

        attachment = ContractAttachment(
            tenant=self.tenant,
            contract_id=record.contract_id,
            original_filename=filename,
            file_size=len(pdf_bytes),
            content_type="application/pdf",
            description=description,
            category="offer",
            source_offer=record,
        )
        attachment.file.save(filename, ContentFile(pdf_bytes), save=False)
        attachment.save()
        return attachment

    # ====================================================================
    # Clone-to-edit — copies the source offer's snapshots verbatim
    # See openspec/specs/offer-finalize/spec.md
    # ====================================================================
    def clone_offer_to_draft(self, source_id: int):
        """Create a new draft OfferRecord from a locked source.

        Does NOT re-read the contract — copies the source's existing
        snapshots so the user iterates on the document that was sent.
        New offer_number from the scheme; cloned_from points back for
        audit.
        """
        from apps.offers.models import OfferRecord
        from apps.offers.numbering import OfferNumberService

        source = OfferRecord.objects.select_related("contract", "customer").get(
            id=source_id, tenant=self.tenant
        )
        if source.status == OfferRecord.Status.DRAFT:
            raise ValueError(
                "Cannot clone a draft offer; edit the draft directly instead."
            )

        numbering = OfferNumberService(self.tenant)
        today = date.today()

        max_attempts = 10
        clone = None
        for attempt in range(max_attempts):
            new_number = numbering.get_next_number(source.billing_date)
            try:
                with transaction.atomic():
                    clone = OfferRecord.objects.create(
                        tenant=self.tenant,
                        contract=source.contract,
                        customer=source.customer,
                        offer_number=new_number,
                        offer_date=today,
                        valid_until=source.valid_until,
                        billing_date=source.billing_date,
                        period_start=source.period_start,
                        period_end=source.period_end,
                        total_net=source.total_net,
                        tax_rate=source.tax_rate,
                        tax_amount=source.tax_amount,
                        total_gross=source.total_gross,
                        line_items_snapshot=source.line_items_snapshot,
                        company_data_snapshot=source.company_data_snapshot,
                        status=OfferRecord.Status.DRAFT,
                        customer_name=source.customer_name,
                        contract_name=source.contract_name,
                        vat_sentence=source.vat_sentence,
                        scoped_item_ids=source.scoped_item_ids,
                        free_text_after_items=source.free_text_after_items,
                        free_text_before_terms=source.free_text_before_terms,
                        minimum_term_months=source.minimum_term_months,
                        notice_period_months=source.notice_period_months,
                        cloned_from=source,
                    )
                break
            except IntegrityError:
                if attempt == max_attempts - 1:
                    raise

        assert clone is not None
        language = (
            clone.customer.get_effective_invoice_language(default="en")
            if clone.customer
            else "en"
        )
        self._generate_and_save_pdf(clone, language)
        return clone

    # ------------------------------------------------------------------ #
    # Re-derive helpers used by both create_offer and recreate_offer.
    # ------------------------------------------------------------------ #
    def _apply_event_to_record(self, record, contract, event) -> None:
        """Overwrite the contract-derived snapshot fields on `record` from
        the given billing event. Caller is responsible for save().
        """
        from apps.invoices.models import CompanyLegalData
        from dateutil.relativedelta import relativedelta

        try:
            legal_data = self.tenant.legal_data
        except CompanyLegalData.DoesNotExist:
            raise ValueError(
                "Company legal data must be configured before generating offers."
            )

        # Period covers from the billing date through one interval.
        interval_months = contract.get_interval_months()
        period_start = record.billing_date
        period_end = period_start + relativedelta(
            months=interval_months, days=-1
        )
        if contract.end_date and period_end > contract.end_date:
            period_end = contract.end_date

        # Tax classification (same as create_offer / invoices).
        company_country = legal_data.country
        customer_address = contract.customer.address or {}
        classification = _classify_customer(company_country, customer_address)
        domestic = classification == "domestic"
        default_tax_rate = legal_data.default_tax_rate
        tax_rate = default_tax_rate if domestic else Decimal("0.00")
        vat_sentence = _get_vat_sentence(classification, legal_data)

        # Build the line-item snapshot, honouring the existing scope.
        item_ids_set = (
            set(record.scoped_item_ids) if record.scoped_item_ids else None
        )
        line_items_snapshot = []
        total_net = Decimal("0.00")
        for item in event["items"]:
            if item_ids_set and item["item_id"] not in item_ids_set:
                continue
            amount = item["amount"]
            total_net += amount
            line_items_snapshot.append({
                "item_id": item["item_id"],
                "product_name": item["product_name"],
                "description": item.get("description", ""),
                "quantity": item["quantity"],
                "unit_price": str(item["unit_price"]),
                "amount": str(amount),
                "is_prorated": item.get("is_prorated", False),
                "prorate_factor": (
                    str(item["prorate_factor"])
                    if item.get("prorate_factor")
                    else None
                ),
                "is_one_off": item.get("is_one_off", False),
            })

        tax_amount = (
            total_net * tax_rate / Decimal("100")
        ).quantize(Decimal("0.01"))
        total_gross = total_net + tax_amount

        # Mutate contract-derived fields. Anything in
        # `_user_editable_fields()` is left untouched.
        record.line_items_snapshot = line_items_snapshot
        record.company_data_snapshot = legal_data.to_snapshot()
        record.customer_name = contract.customer.name
        record.contract_name = contract.name or f"Contract {contract.id}"
        record.period_start = period_start
        record.period_end = period_end
        record.total_net = total_net
        record.tax_rate = tax_rate
        record.tax_amount = tax_amount
        record.total_gross = total_gross
        record.vat_sentence = vat_sentence

    def _refresh_line_items_for_scope(self, record) -> None:
        """Recompute line_items_snapshot + totals when scoped_item_ids
        changed inside update_offer. Reads the current contract billing
        event."""
        contract = record.contract
        if contract is None:
            # No contract = no recomputation possible. Leave snapshot.
            return
        events = contract.get_billing_schedule(
            from_date=record.billing_date,
            to_date=record.billing_date,
            include_history=True,
        )
        event = next(
            (e for e in events if e["date"] == record.billing_date), None
        )
        if event is None:
            return
        self._apply_event_to_record(record, contract, event)

    def _generate_and_save_pdf(self, record, language: str = "en") -> None:
        """Generate PDF for an offer record and save to the pdf_file field."""
        from django.core.files.base import ContentFile

        pdf_bytes = self.generate_pdf_for_record(record, language)
        filename = f"offer-{record.offer_number}.pdf"
        record.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    def generate_pdf_for_record(
        self,
        record,
        language: Literal["de", "en"] = "en",
    ) -> bytes:
        """Generate PDF for a single OfferRecord.

        Returns PDF bytes.
        """
        ctx = self._build_record_template_context(record, language)
        html = render_to_string("offers/offer.html", ctx)
        pdf_document = HTML(string=html).render()
        return pdf_document.write_pdf()

    def _build_record_template_context(
        self,
        record,
        language: Literal["de", "en"] = "en",
    ) -> dict:
        """Build the template context dict for rendering an OfferRecord as HTML."""
        from apps.invoices.models import InvoiceTemplate

        labels = LABELS.get(language, LABELS["en"])
        currency_symbol = self.tenant.currency_symbol
        template_ctx = self._get_template_context()

        offer_dict = {
            "contract_name": record.contract_name,
            "customer_name": record.customer_name,
            "customer_address": (
                record.customer.address if record.customer else {}
            ) or {},
            "customer_vat_id": (
                record.customer.vat_id if record.customer else ""
            ) or "",
            "customer_number": (
                record.customer.netsuite_customer_number if record.customer else ""
            ) or "",
            "offer_date": record.offer_date,
            "valid_until": record.valid_until,
            "billing_date": record.billing_date,
            "period_start": record.period_start,
            "period_end": record.period_end,
            "line_items": record.line_items_snapshot,
            "total_net": record.total_net,
            "tax_amount": record.tax_amount,
            "total_gross": record.total_gross,
            "notes": record.notes,
        }

        vat_sentence = record.vat_sentence or ""

        # Markdown free-text blocks → safe HTML for direct template
        # injection. Empty strings cause the template to skip the block.
        from apps.offers.markdown_render import render_markdown_to_safe_html

        free_text_after_items_html = render_markdown_to_safe_html(
            record.free_text_after_items or ""
        )
        free_text_before_terms_html = render_markdown_to_safe_html(
            record.free_text_before_terms or ""
        )

        # Min-term / notice-period: render only when the value is set and
        # greater than zero. Plain text (no Markdown).
        minimum_term_line = _render_minimum_term_line(
            record.minimum_term_months, language
        )
        notice_period_line = _render_notice_period_line(
            record.notice_period_months, language
        )

        return {
            "offer": offer_dict,
            "labels": labels,
            "language": language,
            "currency_symbol": currency_symbol,
            "offer_number": record.offer_number,
            "tax_rate": record.tax_rate,
            "vat_sentence": vat_sentence,
            "free_text_after_items_html": free_text_after_items_html,
            "free_text_before_terms_html": free_text_before_terms_html,
            "minimum_term_line": minimum_term_line,
            "notice_period_line": notice_period_line,
            **template_ctx,
        }

    def _get_template_context(self) -> dict:
        """Load template settings and legal data for PDF rendering."""
        from apps.invoices.models import CompanyLegalData, InvoiceTemplate

        legal_data_obj = None
        try:
            legal_data_obj = self.tenant.legal_data
            company = legal_data_obj.to_snapshot()
        except CompanyLegalData.DoesNotExist:
            company = {
                "company_name": self.tenant.name,
                "street": "",
                "zip_code": "",
                "city": "",
                "country": "",
                "tax_number": "",
                "vat_id": "",
                "commercial_register_court": "",
                "commercial_register_number": "",
                "managing_directors": [],
                "bank_name": "",
                "iban": "",
                "bic": "",
                "phone": "",
                "email": "",
                "website": "",
                "share_capital": "",
                "default_tax_rate": "19.00",
            }

        accent_color = "#2563eb"
        header_text = ""
        footer_text = ""
        logo_url = ""
        try:
            template = InvoiceTemplate.objects.get(tenant=self.tenant)
            accent_color = template.accent_color or "#2563eb"
            header_text = template.header_text or ""
            footer_text = template.footer_text or ""
            if template.logo and template.logo.name:
                import base64
                import mimetypes
                try:
                    mime_type = mimetypes.guess_type(template.logo.name)[0] or "image/png"
                    logo_data = template.logo.read()
                    logo_url = f"data:{mime_type};base64,{base64.b64encode(logo_data).decode()}"
                except Exception:
                    logo_url = ""
        except InvoiceTemplate.DoesNotExist:
            pass

        return {
            "company": company,
            "accent_color": accent_color,
            "header_text": header_text,
            "footer_text": footer_text,
            "logo_url": logo_url,
        }
