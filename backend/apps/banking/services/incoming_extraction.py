"""Service for extracting metadata from incoming (supplier) invoice PDFs."""

import base64
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings

from apps.banking.models import Counterparty, IncomingInvoice

logger = logging.getLogger(__name__)

INCOMING_INVOICE_EXTRACTION_PROMPT = """\
Analyze this incoming (supplier) invoice PDF and extract the key metadata fields.

Return a JSON object with exactly this structure:
{
  "supplier_name": "The name of the supplier/vendor who issued this invoice",
  "invoice_number": "The invoice number/reference",
  "invoice_date": "The invoice date in ISO format YYYY-MM-DD",
  "due_date": "The payment due date in ISO format YYYY-MM-DD (null if not stated)",
  "net_amount": "Net amount before tax as decimal string (e.g., '1234.56')",
  "vat_amount": "VAT/tax amount as decimal string",
  "gross_amount": "Total gross amount including tax as decimal string",
  "currency": "Three-letter currency code (e.g., 'EUR', 'USD')",
  "iban": "Supplier's IBAN if visible (null if not found)"
}

Rules:
- supplier_name is the ISSUER of the invoice (the vendor sending the bill)
- Extract the invoice number exactly as shown
- All dates must be ISO YYYY-MM-DD
- All amounts as strings without currency symbols
- Handle German number format (1.234,56) by converting to 1234.56
- If a field cannot be determined, use null
- Return ONLY valid JSON, no markdown formatting or explanations
"""


def extract_incoming_invoice_metadata(pdf_data: bytes) -> dict:
    """Send incoming invoice PDF to Claude API and return parsed JSON."""
    import anthropic

    pdf_base64 = base64.standard_b64encode(pdf_data).decode("utf-8")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64,
                        },
                    },
                    {"type": "text", "text": INCOMING_INVOICE_EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    response_text = message.content[0].text
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    return json.loads(response_text)


def _parse_amount(value) -> Decimal | None:
    if not value:
        return None
    try:
        s = str(value)
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def run_incoming_extraction(invoice: IncomingInvoice) -> bool:
    """Run extraction on an incoming invoice. Returns True on success."""
    if not settings.ANTHROPIC_API_KEY:
        invoice.extraction_status = IncomingInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = "PDF analysis not configured (missing API key)"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    invoice.extraction_status = IncomingInvoice.ExtractionStatus.EXTRACTING
    invoice.save(update_fields=["extraction_status", "updated_at"])

    try:
        invoice.pdf_file.open("rb")
        pdf_data = invoice.pdf_file.read()
        invoice.pdf_file.close()
    except Exception as e:
        logger.error("Failed to read incoming invoice PDF %s: %s", invoice.id, e)
        invoice.extraction_status = IncomingInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Failed to read PDF: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    try:
        data = extract_incoming_invoice_metadata(pdf_data)
    except Exception as e:
        logger.error("Extraction error for incoming invoice %s: %s", invoice.id, e)
        invoice.extraction_status = IncomingInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Extraction error: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    if data.get("supplier_name"):
        invoice.supplier_name = data["supplier_name"]
    if data.get("invoice_number"):
        invoice.invoice_number = data["invoice_number"]
    invoice.invoice_date = _parse_date(data.get("invoice_date"))
    invoice.due_date = _parse_date(data.get("due_date"))
    invoice.net_amount = _parse_amount(data.get("net_amount"))
    invoice.vat_amount = _parse_amount(data.get("vat_amount"))
    invoice.gross_amount = _parse_amount(data.get("gross_amount"))
    if data.get("currency"):
        invoice.currency = data["currency"][:3].upper()

    # Check for duplicate by extracted fields before saving
    if invoice.invoice_number and invoice.gross_amount is not None:
        duplicate = IncomingInvoice.objects.filter(
            tenant=invoice.tenant,
            invoice_number=invoice.invoice_number,
            gross_amount=invoice.gross_amount,
            invoice_date=invoice.invoice_date,
        ).exclude(id=invoice.id).first()
        if duplicate:
            logger.info(
                "Duplicate incoming invoice %s matches %s (invoice_number=%s)",
                invoice.id, duplicate.id, invoice.invoice_number,
            )
            # Delete the duplicate upload
            if invoice.pdf_file:
                invoice.pdf_file.delete(save=False)
            invoice.delete()
            return False

    invoice.extraction_status = IncomingInvoice.ExtractionStatus.EXTRACTED
    invoice.extraction_error = ""
    invoice.save()

    _auto_assign_counterparty(invoice, data.get("iban"))
    logger.info("Successfully extracted incoming invoice %s", invoice.id)
    return True


def _auto_assign_counterparty(invoice: IncomingInvoice, iban: str | None = None):
    """Try to match supplier to an existing counterparty."""
    if not invoice.supplier_name and not iban:
        return

    tenant = invoice.tenant
    match = None

    if iban:
        iban_clean = iban.replace(" ", "").upper()
        match = Counterparty.objects.filter(tenant=tenant, iban__iexact=iban_clean).first()

    if not match and invoice.supplier_name:
        match = Counterparty.objects.filter(tenant=tenant, name__icontains=invoice.supplier_name).first()
        if not match:
            for cp in Counterparty.objects.filter(tenant=tenant):
                if cp.name.lower() in invoice.supplier_name.lower():
                    match = cp
                    break

    # Check if a previous incoming invoice with the same supplier was already
    # linked to a counterparty (user-confirmed mapping)
    if not match and invoice.supplier_name:
        previous = (
            IncomingInvoice.objects.filter(
                tenant=tenant,
                supplier_name__iexact=invoice.supplier_name,
                counterparty__isnull=False,
            )
            .exclude(id=invoice.id)
            .select_related("counterparty")
            .first()
        )
        if previous:
            match = previous.counterparty

    if match:
        invoice.counterparty = match
        invoice.save(update_fields=["counterparty", "updated_at"])
