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


class OfferService:
    """Service for generating offers from contract billing schedules."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

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

        return {
            "offer": offer_dict,
            "labels": labels,
            "language": language,
            "currency_symbol": currency_symbol,
            "offer_number": record.offer_number,
            "tax_rate": record.tax_rate,
            "vat_sentence": vat_sentence,
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
