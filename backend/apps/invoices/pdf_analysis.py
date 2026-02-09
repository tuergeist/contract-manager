"""Service for analyzing reference invoice PDFs using the Claude API."""

import base64
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


INVOICE_EXTRACTION_PROMPT = """\
Analyze this invoice PDF and extract all company legal data, visual design elements, \
and layout information from the issuing company (the sender, NOT the recipient).

Return a JSON object with exactly this structure:
{
  "legal_data": {
    "company_name": "Full legal company name including legal form (e.g., 'Muster GmbH')",
    "street": "Street address",
    "zip_code": "Postal code",
    "city": "City",
    "country": "Country (e.g., 'Deutschland')",
    "tax_number": "Steuernummer (e.g., '123/456/78901')",
    "vat_id": "USt-IdNr. (e.g., 'DE123456789')",
    "commercial_register_court": "Register court (e.g., 'Amtsgericht München')",
    "commercial_register_number": "Register number (e.g., 'HRB 12345')",
    "managing_directors": ["List of Geschäftsführer names"],
    "bank_name": "Bank name",
    "iban": "IBAN",
    "bic": "BIC/SWIFT",
    "phone": "Phone number",
    "email": "Email address",
    "website": "Website URL",
    "share_capital": "Stammkapital (e.g., '25.000,00 EUR')",
    "default_tax_rate": "Tax rate as decimal string (e.g., '19.00')"
  },
  "design": {
    "accent_color": "Primary brand/accent color as hex (e.g., '#2563eb')",
    "header_text": "Any tagline or subtitle text below the company name in the header",
    "footer_text": "Payment terms or custom footer text (not the legal footer)"
  },
  "layout": {
    "logo_position": "top-left, top-right, or top-center",
    "footer_columns": 2,
    "description": "Brief description of the overall invoice layout"
  }
}

Rules:
- Extract data from the ISSUING company (sender), not the billing recipient
- If a field is not found in the document, use null
- managing_directors must be an array of strings (names only)
- accent_color should be the most prominent non-black color used for headings, lines, or accents
- default_tax_rate: look for "MwSt.", "USt.", or tax percentage applied to line items
- Support both English and German invoices
- Return ONLY valid JSON, no markdown formatting
"""


def extract_from_invoice_pdf(pdf_data: bytes) -> dict:
    """Send invoice PDF to Claude API and return parsed JSON with extracted data."""
    import anthropic

    pdf_base64 = base64.standard_b64encode(pdf_data).decode("utf-8")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
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
                        "text": INVOICE_EXTRACTION_PROMPT,
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


def analyze_reference(reference) -> dict:
    """
    Analyze a reference invoice PDF and store extraction results.

    Args:
        reference: InvoiceTemplateReference instance

    Returns:
        The extracted data dict, or a dict with "error" key on failure.
    """
    from apps.invoices.models import InvoiceTemplateReference

    if not settings.ANTHROPIC_API_KEY:
        reference.extraction_status = InvoiceTemplateReference.ExtractionStatus.FAILED
        reference.save(update_fields=["extraction_status"])
        return {"error": "PDF analysis is not configured (missing API key)"}

    # Read the PDF file
    try:
        reference.file.open("rb")
        pdf_data = reference.file.read()
        reference.file.close()
    except Exception as e:
        logger.error("Failed to read reference PDF %s: %s", reference.id, e)
        reference.extraction_status = InvoiceTemplateReference.ExtractionStatus.FAILED
        reference.save(update_fields=["extraction_status"])
        return {"error": f"Failed to read PDF file: {e}"}

    # Call Claude API
    try:
        data = extract_from_invoice_pdf(pdf_data)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse extraction result for reference %s: %s", reference.id, e)
        reference.extraction_status = InvoiceTemplateReference.ExtractionStatus.FAILED
        reference.save(update_fields=["extraction_status"])
        return {"error": f"Failed to parse extraction result: {e}"}
    except Exception as e:
        logger.error("Claude API error for reference %s: %s", reference.id, e)
        reference.extraction_status = InvoiceTemplateReference.ExtractionStatus.FAILED
        reference.save(update_fields=["extraction_status"])
        return {"error": f"Claude API error: {e}"}

    # Store results
    reference.extracted_data = data
    reference.extraction_status = InvoiceTemplateReference.ExtractionStatus.COMPLETED
    reference.save(update_fields=["extracted_data", "extraction_status"])

    logger.info("Successfully extracted data from reference PDF %s", reference.id)
    return data
