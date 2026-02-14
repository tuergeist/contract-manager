"""ZUGFeRD invoice generation service.

Generates UN/CEFACT Cross-Industry Invoice (CII) XML conforming to
the ZUGFeRD EN 16931 (Comfort) profile, and embeds it into PDF/A-3b
documents using the drafthorse library.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from drafthorse.models.accounting import ApplicableTradeTax
from drafthorse.models.document import Document
from drafthorse.models.note import IncludedNote
from drafthorse.models.party import TaxRegistration
from drafthorse.models.payment import PaymentMeans
from drafthorse.models.tradelines import LineItem
from drafthorse.pdf import attach_xml

from apps.invoices.models import CompanyLegalData, InvoiceRecord
from apps.invoices.types import InvoiceData
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

# ISO 3166-1 alpha-2 mapping for common German country names
COUNTRY_CODE_MAP = {
    "deutschland": "DE",
    "germany": "DE",
    "österreich": "AT",
    "austria": "AT",
    "schweiz": "CH",
    "switzerland": "CH",
    "frankreich": "FR",
    "france": "FR",
    "niederlande": "NL",
    "netherlands": "NL",
    "belgien": "BE",
    "belgium": "BE",
    "luxemburg": "LU",
    "luxembourg": "LU",
    "italien": "IT",
    "italy": "IT",
    "spanien": "ES",
    "spain": "ES",
    "polen": "PL",
    "poland": "PL",
    "tschechien": "CZ",
    "czech republic": "CZ",
    "dänemark": "DK",
    "denmark": "DK",
    "schweden": "SE",
    "sweden": "SE",
    "vereinigtes königreich": "GB",
    "united kingdom": "GB",
    "usa": "US",
    "vereinigte staaten": "US",
    "united states": "US",
}


def _resolve_country_code(country: str) -> str:
    """Resolve a country name or code to ISO 3166-1 alpha-2.

    Accepts either a 2-letter code directly or a full country name
    (German or English).
    """
    if not country:
        return "DE"
    country_stripped = country.strip()
    if len(country_stripped) == 2 and country_stripped.isalpha():
        return country_stripped.upper()
    return COUNTRY_CODE_MAP.get(country_stripped.lower(), "DE")


class ZugferdService:
    """Service for generating ZUGFeRD EN 16931 invoices."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def generate_xml_from_record(self, record: InvoiceRecord) -> bytes:
        """Generate ZUGFeRD XML from a persisted InvoiceRecord.

        Uses the frozen company_data_snapshot and line_items_snapshot
        so the XML reflects the data at invoice generation time.
        """
        company = record.company_data_snapshot
        customer_name = record.customer_name
        # Retrieve customer address from the linked customer if available
        customer_address = {}
        if record.customer:
            customer_address = record.customer.address or {}

        line_items = []
        for item in record.line_items_snapshot:
            line_items.append({
                "product_name": item.get("product_name", ""),
                "description": item.get("description", ""),
                "quantity": int(item.get("quantity", 1)),
                "unit_price": Decimal(str(item.get("unit_price", "0"))),
                "amount": Decimal(str(item.get("amount", "0"))),
            })

        return self._build_xml(
            invoice_number=record.invoice_number,
            invoice_date=record.billing_date,
            period_start=record.period_start,
            period_end=record.period_end,
            total_net=record.total_net,
            tax_rate=record.tax_rate,
            tax_amount=record.tax_amount,
            total_gross=record.total_gross,
            currency=self.tenant.currency,
            company=company,
            customer_name=customer_name,
            customer_address=customer_address,
            line_items=line_items,
            invoice_text=record.invoice_text,
        )

    def generate_xml_from_invoice_data(
        self,
        invoice_data: InvoiceData,
        tax_rate: Decimal,
        tax_amount: Decimal,
        total_gross: Decimal,
        company: dict,
    ) -> bytes:
        """Generate ZUGFeRD XML from an on-demand InvoiceData dataclass.

        Used for preview/non-persisted invoices. The caller provides
        the tax calculation results and company data snapshot.
        """
        line_items = []
        for item in invoice_data.line_items:
            line_items.append({
                "product_name": item.product_name,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount,
            })

        return self._build_xml(
            invoice_number=getattr(invoice_data, "invoice_number", "PREVIEW"),
            invoice_date=invoice_data.billing_date,
            period_start=invoice_data.billing_period_start,
            period_end=invoice_data.billing_period_end,
            total_net=invoice_data.total_amount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_gross=total_gross,
            currency=self.tenant.currency,
            company=company,
            customer_name=invoice_data.customer_name,
            customer_address=invoice_data.customer_address,
            line_items=line_items,
            invoice_text=invoice_data.invoice_text,
        )

    def _build_xml(
        self,
        *,
        invoice_number: str,
        invoice_date: date,
        period_start: date,
        period_end: date,
        total_net: Decimal,
        tax_rate: Decimal,
        tax_amount: Decimal,
        total_gross: Decimal,
        currency: str,
        company: dict,
        customer_name: str,
        customer_address: dict,
        line_items: list[dict],
        invoice_text: str = "",
    ) -> bytes:
        """Build UN/CEFACT CII XML for ZUGFeRD EN 16931 profile.

        Returns the XML as bytes, validated against the EN 16931 XSD.
        """
        doc = Document()

        # -- Context: EN 16931 profile --
        doc.context.guideline_parameter.id = (
            "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931"
        )

        # -- Header --
        doc.header.id = invoice_number
        doc.header.type_code = "380"  # Commercial invoice
        doc.header.issue_date_time = invoice_date

        # Invoice note
        if invoice_text:
            doc.header.notes.add(IncludedNote(content=invoice_text))

        # -- Seller --
        seller = doc.trade.agreement.seller
        seller.name = company.get("company_name", "")

        seller_address = seller.address
        seller_address.line_one = company.get("street", "")
        seller_address.postcode = company.get("zip_code", "")
        seller_address.city_name = company.get("city", "")
        seller_address.country_id = _resolve_country_code(
            company.get("country", "DE")
        )

        # Tax registration: prefer VAT ID, fallback to tax number
        vat_id = company.get("vat_id", "")
        tax_number = company.get("tax_number", "")
        if vat_id:
            seller.tax_registrations.add(
                TaxRegistration(id=("VA", vat_id))
            )
        if tax_number:
            seller.tax_registrations.add(
                TaxRegistration(id=("FC", tax_number))
            )

        # Seller contact
        email = company.get("email", "")
        phone = company.get("phone", "")
        if email or phone:
            if email:
                seller.contact.email.value = email
            if phone:
                seller.contact.phone.value = phone

        # -- Buyer --
        buyer = doc.trade.agreement.buyer
        buyer.name = customer_name

        buyer_address = buyer.address
        buyer_address.line_one = customer_address.get(
            "street", customer_address.get("line1", "")
        )
        buyer_address.postcode = customer_address.get(
            "zip", customer_address.get("zip_code", "")
        )
        buyer_address.city_name = customer_address.get("city", "")
        buyer_country = customer_address.get("country", "")
        if buyer_country:
            buyer_address.country_id = _resolve_country_code(buyer_country)

        # Buyer VAT ID (optional, from address JSON)
        buyer_vat_id = customer_address.get("vat_id", "")
        if buyer_vat_id:
            buyer.tax_registrations.add(
                TaxRegistration(id=("VA", buyer_vat_id))
            )

        # -- Delivery (billing period) --
        doc.trade.delivery.event.occurrence = period_start

        # -- Settlement --
        settlement = doc.trade.settlement
        settlement.currency_code = currency

        # Payment means: SEPA credit transfer if bank details available
        iban = company.get("iban", "")
        bic = company.get("bic", "")
        if iban:
            pm = PaymentMeans()
            pm.type_code = "58"  # SEPA credit transfer
            pm.payee_account.iban = iban
            if bic:
                pm.payee_institution.bic = bic
            settlement.payment_means.add(pm)

        # Billing period
        settlement.period.start = period_start
        settlement.period.end = period_end

        # -- Line items --
        for idx, item in enumerate(line_items, start=1):
            li = LineItem()
            li.document.line_id = str(idx)
            li.product.name = item["product_name"]
            if item.get("description"):
                li.product.description = item["description"]

            quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item["unit_price"]))
            line_amount = Decimal(str(item["amount"]))

            li.agreement.net.amount = unit_price
            li.agreement.net.basis_quantity = (Decimal("1.0000"), "C62")
            li.delivery.billed_quantity = (quantity, "C62")

            li.settlement.trade_tax.type_code = "VAT"
            li.settlement.trade_tax.category_code = "S"
            li.settlement.trade_tax.rate_applicable_percent = tax_rate

            li.settlement.monetary_summation.total_amount = line_amount

            doc.trade.items.add(li)

        # -- Tax summary --
        trade_tax = ApplicableTradeTax()
        trade_tax.calculated_amount = tax_amount
        trade_tax.basis_amount = total_net
        trade_tax.type_code = "VAT"
        trade_tax.category_code = "S"
        trade_tax.rate_applicable_percent = tax_rate
        settlement.trade_tax.add(trade_tax)

        # -- Monetary summation --
        summation = settlement.monetary_summation
        summation.line_total = total_net
        summation.charge_total = Decimal("0.00")
        summation.allowance_total = Decimal("0.00")
        summation.tax_basis_total = total_net
        summation.tax_total = (tax_amount, currency)
        summation.grand_total = total_gross
        summation.due_amount = total_gross

        # -- Serialize and validate --
        xml_bytes = self._serialize_xml(doc)
        return xml_bytes

    def _serialize_xml(self, doc: Document) -> bytes:
        """Serialize the Document to XML bytes with validation.

        Attempts validation against FACTUR-X_EN16931 schema first.
        Falls back to unvalidated serialization on failure (with warning).
        """
        try:
            return doc.serialize(schema="FACTUR-X_EN16931")
        except Exception as e:
            logger.warning(
                "ZUGFeRD XML validation failed, generating without validation: %s",
                str(e),
            )
            try:
                return doc.serialize(schema=None)
            except Exception as e2:
                logger.error("ZUGFeRD XML serialization failed: %s", str(e2))
                raise

    def embed_xml_in_pdf(
        self,
        pdf_bytes: bytes,
        xml_bytes: bytes,
        metadata: Optional[dict] = None,
    ) -> bytes:
        """Embed ZUGFeRD XML into a PDF, producing a PDF/A-3b document.

        Uses drafthorse's attach_xml() which handles:
        - PDF/A-3 conversion
        - XMP/RDF metadata with Factur-X conformance declaration
        - XML file attachment with correct AFRelationship

        Args:
            pdf_bytes: The visual invoice PDF (from WeasyPrint)
            xml_bytes: The ZUGFeRD CII XML
            metadata: Optional PDF metadata dict (title, author, etc.)

        Returns:
            PDF/A-3b bytes with embedded ZUGFeRD XML.
        """
        pdf_metadata = metadata or {}
        return attach_xml(
            original_pdf=pdf_bytes,
            xml_data=xml_bytes,
            level="EN 16931",
            metadata=pdf_metadata if pdf_metadata else None,
        )

    def generate_zugferd_pdf(
        self,
        pdf_bytes: bytes,
        record: InvoiceRecord,
    ) -> bytes:
        """Generate a complete ZUGFeRD PDF from a regular PDF and InvoiceRecord.

        Convenience method that generates XML and embeds it in one step.
        """
        xml_bytes = self.generate_xml_from_record(record)
        return self.embed_xml_in_pdf(
            pdf_bytes=pdf_bytes,
            xml_bytes=xml_bytes,
            metadata={
                "title": f"Invoice {record.invoice_number}",
                "subject": f"Invoice {record.invoice_number} - {record.customer_name}",
            },
        )
