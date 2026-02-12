"""Service for extracting metadata from imported invoice PDFs using Claude API."""

import base64
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings

from apps.invoices.models import ImportedInvoice

logger = logging.getLogger(__name__)


IMPORTED_INVOICE_EXTRACTION_PROMPT = """\
Analyze this outgoing invoice PDF and extract the key metadata fields.

Return a JSON object with exactly this structure:
{
  "invoice_number": "The invoice number/reference (e.g., 'RE-2025-001234', 'INV-00456')",
  "invoice_date": "The invoice date in ISO format YYYY-MM-DD",
  "total_amount": "The total gross amount as a decimal string (e.g., '1234.56')",
  "currency": "Three-letter currency code (e.g., 'EUR', 'USD')",
  "customer_name": "The name of the customer/recipient (the party being invoiced)"
}

Rules:
- Extract the invoice number exactly as shown, preserving format
- invoice_date must be in ISO YYYY-MM-DD format
- total_amount should be the final total including tax (Brutto), as a string without currency symbols
- customer_name is the RECIPIENT of the invoice (Rechnungsempfänger), not the issuer
- If a field cannot be determined, use null
- Return ONLY valid JSON, no markdown formatting or explanations
"""


def extract_invoice_metadata(pdf_data: bytes) -> dict:
    """
    Send invoice PDF to Claude API and return parsed JSON with extracted metadata.

    Args:
        pdf_data: Raw PDF bytes

    Returns:
        Dict with keys: invoice_number, invoice_date, total_amount, currency, customer_name
    """
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
                    {
                        "type": "text",
                        "text": IMPORTED_INVOICE_EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    return json.loads(response_text)


def run_extraction(invoice: ImportedInvoice) -> bool:
    """
    Run extraction on an imported invoice and update its fields.

    Args:
        invoice: ImportedInvoice instance with pending extraction

    Returns:
        True if extraction succeeded, False otherwise
    """
    if not settings.ANTHROPIC_API_KEY:
        invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = "PDF analysis is not configured (missing API key)"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    # Mark as extracting
    invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTING
    invoice.save(update_fields=["extraction_status", "updated_at"])

    # Read the PDF file
    try:
        invoice.pdf_file.open("rb")
        pdf_data = invoice.pdf_file.read()
        invoice.pdf_file.close()
    except Exception as e:
        logger.error("Failed to read invoice PDF %s: %s", invoice.id, e)
        invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Failed to read PDF file: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    # Call Claude API
    try:
        data = extract_invoice_metadata(pdf_data)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse extraction result for invoice %s: %s", invoice.id, e)
        invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Failed to parse extraction result: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False
    except Exception as e:
        logger.error("Claude API error for invoice %s: %s", invoice.id, e)
        invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Claude API error: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    # Parse and store results
    try:
        _apply_extraction_results(invoice, data)
    except Exception as e:
        logger.error("Failed to apply extraction results for invoice %s: %s", invoice.id, e)
        invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Failed to apply extraction results: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTED
    invoice.extraction_error = ""
    invoice.save()

    logger.info("Successfully extracted data from invoice PDF %s", invoice.id)
    return True


def _apply_extraction_results(invoice: ImportedInvoice, data: dict) -> None:
    """Apply extracted data to invoice fields."""
    # Invoice number
    if data.get("invoice_number"):
        invoice.invoice_number = data["invoice_number"]

    # Invoice date
    if data.get("invoice_date"):
        try:
            invoice.invoice_date = datetime.strptime(data["invoice_date"], "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Invalid date format in extraction result: %s", data["invoice_date"])

    # Total amount
    if data.get("total_amount"):
        try:
            # Handle German number format (1.234,56 -> 1234.56)
            amount_str = data["total_amount"]
            if "," in amount_str and "." in amount_str:
                # German format: 1.234,56
                amount_str = amount_str.replace(".", "").replace(",", ".")
            elif "," in amount_str:
                # Simple comma decimal: 1234,56
                amount_str = amount_str.replace(",", ".")
            invoice.total_amount = Decimal(amount_str)
        except (InvalidOperation, ValueError):
            logger.warning("Invalid amount format in extraction result: %s", data["total_amount"])

    # Currency
    if data.get("currency"):
        invoice.currency = data["currency"][:3].upper()

    # Customer name
    if data.get("customer_name"):
        invoice.customer_name = data["customer_name"]
