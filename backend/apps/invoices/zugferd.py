"""ZUGFeRD invoice generation service.

Generates UN/CEFACT Cross-Industry Invoice (CII) XML conforming to
the ZUGFeRD EN 16931 (Comfort) profile, and embeds it into PDF/A-3b
documents using the drafthorse library.
"""
import hashlib
import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Optional

from drafthorse.models.accounting import ApplicableTradeTax, CategoryTradeTax
from drafthorse.models.document import Document
from drafthorse.models.note import IncludedNote
from drafthorse.models.party import TaxRegistration
from drafthorse.models.payment import PaymentMeans, PaymentTerms
from drafthorse.models.trade import TradeAllowanceCharge
from drafthorse.models.tradelines import LineItem
from drafthorse.pdf import attach_xml
from PIL import ImageCms
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    create_string_object,
)

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


def _fix_image_interpolation(writer: PdfWriter) -> None:
    """Set Interpolate=false on all image XObjects for PDF/A-3 compliance.

    ISO 19005-3:2012 rule 6.2.8 requires image Interpolate to be false.
    """
    for page in writer.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        xobjects = resources.get("/XObject")
        if not xobjects:
            continue
        for key in xobjects:
            xobj = xobjects[key].get_object()
            subtype = xobj.get("/Subtype")
            if subtype == "/Image" and xobj.get("/Interpolate"):
                xobj[NameObject("/Interpolate")] = BooleanObject(False)


def _add_pdfa_output_intent(pdf_bytes: bytes) -> bytes:
    """Add sRGB OutputIntent and fix PDF/A-3b compliance issues.

    drafthorse's attach_xml() only preserves existing OutputIntents from the
    input PDF. Since WeasyPrint produces regular PDFs without OutputIntents,
    the resulting document lacks the ICC color profile that PDF/A-3b requires.
    This function also fixes image Interpolate flags and ensures a file ID
    exists in the trailer (ISO 19005-3:2012 rule 6.1.3).
    """
    reader = PdfReader(BytesIO(pdf_bytes))

    has_output_intents = False
    try:
        root = reader.trailer["/Root"]
        if "/OutputIntents" in root:
            has_output_intents = True
    except KeyError:
        pass

    writer = PdfWriter(clone_from=reader)

    # Fix image Interpolate flags (ISO 19005-3:2012 rule 6.2.8)
    _fix_image_interpolation(writer)

    if not has_output_intents:
        # Generate sRGB ICC profile via Pillow
        srgb_profile = ImageCms.createProfile("sRGB")
        icc_data = ImageCms.ImageCmsProfile(srgb_profile).tobytes()

        icc_stream = DecodedStreamObject()
        icc_stream.set_data(icc_data)
        icc_stream.update({
            NameObject("/N"): NumberObject(3),  # RGB = 3 components
        })
        icc_ref = writer._add_object(icc_stream)

        output_intent = DictionaryObject({
            NameObject("/Type"): NameObject("/OutputIntent"),
            NameObject("/S"): NameObject("/GTS_PDFA1"),
            NameObject("/OutputConditionIdentifier"): create_string_object(
                "sRGB IEC61966-2.1"
            ),
            NameObject("/RegistryName"): create_string_object(
                "http://www.color.org"
            ),
            NameObject("/Info"): create_string_object("sRGB IEC61966-2.1"),
            NameObject("/DestOutputProfile"): icc_ref,
        })
        output_intent_ref = writer._add_object(output_intent)

        writer._root_object[NameObject("/OutputIntents")] = ArrayObject(
            [output_intent_ref]
        )

    # Ensure file ID in trailer (ISO 32000-1:2008 §14.4, required by PDF/A-3)
    # PDF 2.0 required for /AF and /AFRelationship used by ZUGFeRD/Factur-X
    writer.pdf_header = b"%PDF-2.0"
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    pdf_out = buf.read()

    # pypdf may not write an /ID entry; patch it in via a second pass
    reader2 = PdfReader(BytesIO(pdf_out))
    if "/ID" not in reader2.trailer:
        writer2 = PdfWriter(clone_from=reader2)
        file_id = hashlib.md5(uuid.uuid4().bytes).hexdigest().encode("ascii")
        writer2._ID = ArrayObject(
            [create_string_object(file_id), create_string_object(file_id)]
        )
        buf2 = BytesIO()
        writer2.write(buf2)
        buf2.seek(0)
        return buf2.read()

    return pdf_out


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

        po_number = ""
        if record.contract:
            po_number = record.contract.po_number or ""

        customer_vat_id = ""
        if record.customer:
            customer_vat_id = record.customer.vat_id or ""

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
            po_number=po_number,
            customer_vat_id=customer_vat_id,
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
            po_number=invoice_data.po_number,
            customer_vat_id=invoice_data.customer_vat_id,
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
        po_number: str = "",
        customer_vat_id: str = "",
    ) -> bytes:
        """Build UN/CEFACT CII XML for ZUGFeRD EN 16931 profile.

        Returns the XML as bytes, validated against the EN 16931 XSD.
        """
        TWO_PLACES = Decimal("0.01")
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

        # Place of issue (Ausstellungsort) from seller city
        seller_city = company.get("city", "")
        if seller_city:
            doc.header.notes.add(
                IncludedNote(content=f"Ausstellungsort: {seller_city}")
            )

        # -- Buyer reference (BT-10, optional in Factur-X EN16931) --
        if po_number:
            doc.trade.agreement.buyer_reference = po_number

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

        # Seller contact (BT-41 contact point required by BR-DE-5)
        email = company.get("email", "")
        phone = company.get("phone", "")
        managing_directors = company.get("managing_directors", [])
        seller.contact.person_name = (
            managing_directors[0] if managing_directors
            else company.get("company_name", "")
        )
        if email:
            seller.contact.email.address = email
        if phone:
            seller.contact.telephone.number = phone

        # Seller electronic address (BT-34, required by PEPPOL-EN16931-R020)
        if email:
            seller.electronic_address.uri_ID = ("EM", email)

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

        # Buyer VAT ID (optional)
        buyer_vat_id = customer_vat_id
        if buyer_vat_id:
            buyer.tax_registrations.add(
                TaxRegistration(id=("VA", buyer_vat_id))
            )

        # Buyer electronic address (BT-49, required by PEPPOL-EN16931-R010)
        buyer_email = customer_address.get("email", "")
        if buyer_email:
            buyer.electronic_address.uri_ID = ("EM", buyer_email)

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

        # Payment terms (BT-20, required by BR-CO-25 when amount > 0)
        pt = PaymentTerms()
        due_date = invoice_date + timedelta(days=30)
        pt.description = "Net 30 days"
        pt.due = due_date
        settlement.terms.add(pt)

        # Billing period
        settlement.period.start = period_start
        settlement.period.end = period_end

        # -- Line items and allowances --
        # Separate positive items (line items) from negative items (allowances).
        # BR-27: Item net price (BT-146) shall NOT be negative.
        # Negative amounts are represented as document-level allowances.
        # BR-DEC-23: All amounts quantized to 2 decimal places.
        positive_line_total = Decimal("0.00")
        allowance_total = Decimal("0.00")
        line_idx = 0

        for item in line_items:
            line_amount = Decimal(str(item["amount"])).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )

            if line_amount < 0:
                # Negative item → document-level allowance
                tac = TradeAllowanceCharge()
                tac.indicator = False  # False = allowance
                tac.actual_amount = abs(line_amount)
                tac.reason = item.get("product_name", "Discount")
                ct = CategoryTradeTax()
                ct.type_code = "VAT"
                ct.category_code = "S"
                ct.rate_applicable_percent = tax_rate
                tac.trade_tax.add(ct)
                settlement.allowance_charge.add(tac)
                allowance_total += abs(line_amount)
                continue

            line_idx += 1
            li = LineItem()
            li.document.line_id = str(line_idx)
            li.product.name = item["product_name"]
            if item.get("description"):
                li.product.description = item["description"]

            quantity = Decimal(str(item["quantity"]))
            if quantity == 0:
                quantity = Decimal("1")

            # BT-146 net price = line_amount / quantity so that
            # net_price * qty = line_amount (arithmetic consistency)
            net_price = (line_amount / quantity).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )

            li.agreement.net.amount = net_price
            li.agreement.net.basis_quantity = (Decimal("1.0000"), "C62")
            li.delivery.billed_quantity = (quantity, "C62")

            li.settlement.trade_tax.type_code = "VAT"
            li.settlement.trade_tax.category_code = "S"
            li.settlement.trade_tax.rate_applicable_percent = tax_rate

            li.settlement.monetary_summation.total_amount = line_amount
            positive_line_total += line_amount

            doc.trade.items.add(li)

        # -- Tax summary --
        # tax_basis = line_total - allowance_total
        tax_basis = (positive_line_total - allowance_total).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        computed_tax = (tax_basis * tax_rate / Decimal("100")).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        computed_gross = tax_basis + computed_tax

        trade_tax = ApplicableTradeTax()
        trade_tax.calculated_amount = computed_tax
        trade_tax.basis_amount = tax_basis
        trade_tax.type_code = "VAT"
        trade_tax.category_code = "S"
        trade_tax.rate_applicable_percent = tax_rate
        settlement.trade_tax.add(trade_tax)

        # -- Monetary summation --
        # BT-106 line_total = sum of positive line items
        # BT-107 allowance_total = sum of allowances
        # BT-109 tax_basis = line_total - allowance_total + charge_total
        summation = settlement.monetary_summation
        summation.line_total = positive_line_total
        summation.charge_total = Decimal("0.00")
        summation.allowance_total = allowance_total
        summation.tax_basis_total = tax_basis
        summation.tax_total = (computed_tax, currency)
        summation.grand_total = computed_gross
        summation.due_amount = computed_gross

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
        result = attach_xml(
            original_pdf=pdf_bytes,
            xml_data=xml_bytes,
            level="EN 16931",
            metadata=pdf_metadata if pdf_metadata else None,
        )
        return _add_pdfa_output_intent(result)

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
