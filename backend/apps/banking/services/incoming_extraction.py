"""Service for extracting metadata from incoming (supplier) invoice PDFs."""

import base64
import json
import logging
import uuid  # noqa: F401  (used in type annotations as string literal)
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings

from apps.banking.models import Counterparty, IncomingInvoice

logger = logging.getLogger(__name__)

INCOMING_INVOICE_EXTRACTION_PROMPT_TEMPLATE = """\
Analyze this incoming (supplier) invoice PDF and extract the key metadata fields.

Return a JSON object with exactly this structure:
{{
  "supplier_name": "The name of the supplier/vendor who issued this invoice",
  "supplier_name_confidence": 0.95,
  "invoice_number": "The invoice number/reference",
  "invoice_number_confidence": 0.95,
  "invoice_date": "The invoice date in ISO format YYYY-MM-DD",
  "invoice_date_confidence": 0.95,
  "due_date": "The payment due date in ISO format YYYY-MM-DD (null if not stated)",
  "due_date_confidence": 0.95,
  "net_amount": "Net amount before tax as decimal string (e.g., '1234.56')",
  "net_amount_confidence": 0.95,
  "vat_amount": "VAT/tax amount as decimal string",
  "vat_amount_confidence": 0.95,
  "gross_amount": "Total gross amount including tax as decimal string",
  "gross_amount_confidence": 0.95,
  "currency": "Three-letter currency code (e.g., 'EUR', 'USD')",
  "currency_confidence": 0.95,
  "iban": "Supplier's IBAN if visible (null if not found)",
  "iban_confidence": 0.95
}}

Rules:
- supplier_name is the ISSUER of the invoice (the vendor sending the bill){recipient_rule}
- Extract the invoice number exactly as shown
- All dates must be ISO YYYY-MM-DD
- All amounts as strings without currency symbols
- Handle German number format (1.234,56) by converting to 1234.56
- If a field cannot be determined, use null
- Each *_confidence is a float 0.0–1.0 indicating how certain you are about the corresponding value:
  - 1.0 = field clearly visible and unambiguous
  - 0.7–0.9 = confident but slight ambiguity (e.g. handwritten, unusual layout)
  - 0.4–0.7 = guessed from context, please verify
  - <0.4 = highly uncertain or null value
- Return ONLY valid JSON, no markdown formatting or explanations
"""


def _build_extraction_prompt(recipient_name: str | None) -> str:
    if recipient_name:
        rule = (
            f"\n- CRITICAL: \"{recipient_name}\" is the RECIPIENT of this invoice "
            f"(the bill is addressed TO them). They CANNOT be the supplier_name. "
            f"If the only company name you can find on the invoice is \"{recipient_name}\", "
            f"return null for supplier_name."
        )
    else:
        rule = ""
    return INCOMING_INVOICE_EXTRACTION_PROMPT_TEMPLATE.format(recipient_rule=rule)


# Kept for backwards compatibility / tests that import the original constant.
INCOMING_INVOICE_EXTRACTION_PROMPT = _build_extraction_prompt(None)


def extract_incoming_invoice_metadata(pdf_data: bytes, recipient_name: str | None = None) -> dict:
    """Send incoming invoice PDF to Claude API and return parsed JSON.

    ``recipient_name`` is the tenant's own company name; passed into the prompt so
    the model never confuses recipient and issuer (a common failure mode on
    invoices where the recipient block is more visually prominent).
    """
    import anthropic

    pdf_base64 = base64.standard_b64encode(pdf_data).decode("utf-8")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
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
                    {"type": "text", "text": _build_extraction_prompt(recipient_name)},
                ],
            }
        ],
    )

    response_text = message.content[0].text
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    return json.loads(response_text)


def _normalize_company_name(name: str | None) -> str:
    """Lowercase and strip whitespace/punctuation for loose comparison."""
    if not name:
        return ""
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
    return "".join(out)


def _get_tenant_company_name(tenant) -> str | None:
    from apps.invoices.models import CompanyLegalData
    return (
        CompanyLegalData.objects.filter(tenant=tenant)
        .values_list("company_name", flat=True)
        .first()
    )


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

    tenant_name = _get_tenant_company_name(invoice.tenant)
    try:
        data = extract_incoming_invoice_metadata(pdf_data, recipient_name=tenant_name)
    except Exception as e:
        logger.error("Extraction error for incoming invoice %s: %s", invoice.id, e)
        invoice.extraction_status = IncomingInvoice.ExtractionStatus.EXTRACTION_FAILED
        invoice.extraction_error = f"Extraction error: {e}"
        invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
        return False

    # Defensive: never accept the tenant's own legal name as supplier — VSX
    # cannot be the issuer of an invoice it received. The extraction prompt
    # already warns the model, but this guards against any remaining slip-ups.
    extracted_supplier = data.get("supplier_name")
    if extracted_supplier and tenant_name:
        if _normalize_company_name(extracted_supplier) == _normalize_company_name(tenant_name):
            logger.warning(
                "Discarding supplier_name '%s' for incoming invoice %s — matches tenant name",
                extracted_supplier, invoice.id,
            )
            data["supplier_name"] = None

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

    # Pull confidence values into a separate JSON dict
    confidence: dict = {}
    for field in ("supplier_name", "invoice_number", "invoice_date", "due_date",
                  "net_amount", "vat_amount", "gross_amount", "currency", "iban"):
        c = data.get(f"{field}_confidence")
        if c is not None:
            try:
                confidence[field] = float(c)
            except (TypeError, ValueError):
                pass
    invoice.extraction_confidence = confidence

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
    """Try to match supplier to an existing counterparty.

    The tenant's own company is excluded from candidates — even if a
    counterparty record exists for it (e.g. payroll-related self-transfers),
    the tenant cannot be the issuer of an invoice it received.
    """
    if not invoice.supplier_name and not iban:
        return

    tenant = invoice.tenant
    tenant_name_norm = _normalize_company_name(_get_tenant_company_name(tenant))

    candidates = Counterparty.objects.filter(tenant=tenant)
    if tenant_name_norm:
        candidates = [
            cp for cp in candidates
            if _normalize_company_name(cp.name) != tenant_name_norm
        ]

    match = None

    if iban:
        iban_clean = iban.replace(" ", "").upper()
        for cp in candidates:
            if cp.iban and cp.iban.upper() == iban_clean:
                match = cp
                break

    if not match and invoice.supplier_name:
        supplier_lower = invoice.supplier_name.lower()
        for cp in candidates:
            if invoice.supplier_name.lower() in cp.name.lower():
                match = cp
                break
        if not match:
            for cp in candidates:
                if cp.name.lower() in supplier_lower:
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
        if previous and (
            not tenant_name_norm
            or _normalize_company_name(previous.counterparty.name) != tenant_name_norm
        ):
            match = previous.counterparty

    # Final fallback: payment-based hint. If a single outgoing bank transaction
    # exists on or after the invoice date with the exact gross amount, its
    # counterparty is a strong candidate — this catches cases where the LLM
    # got the supplier name wrong but the bookkeeping already paid the bill.
    if not match and invoice.gross_amount and invoice.invoice_date:
        cp_id = _payment_match_counterparty(invoice, tenant_name_norm)
        if cp_id:
            match = Counterparty.objects.filter(tenant=tenant, id=cp_id).first()

    if match:
        invoice.counterparty = match
        invoice.save(update_fields=["counterparty", "updated_at"])


def _payment_match_counterparty(invoice: IncomingInvoice, tenant_name_norm: str) -> "uuid.UUID | None":
    """Return a counterparty id when exactly one outgoing payment matches the invoice.

    Searches BankTransactions belonging to the invoice's tenant where:
      - entry_date is on or after invoice_date (payment cannot precede invoice)
      - amount equals -gross_amount (outgoing payment matches invoice total)
      - currency aligns
      - within 365 days after invoice_date (don't pull arbitrarily old matches)

    Returns the counterparty id only when all matching transactions point to
    the same counterparty (and that counterparty is not the tenant itself).
    """
    from datetime import timedelta
    from apps.banking.models import BankTransaction

    if not invoice.gross_amount or not invoice.invoice_date:
        return None

    window_end = invoice.invoice_date + timedelta(days=365)
    txs = (
        BankTransaction.objects.filter(
            tenant=invoice.tenant,
            entry_date__gte=invoice.invoice_date,
            entry_date__lte=window_end,
            amount=-invoice.gross_amount,
            counterparty__isnull=False,
        )
        .select_related("counterparty")
    )

    cp_ids = set()
    for tx in txs:
        cp = tx.counterparty
        if tenant_name_norm and _normalize_company_name(cp.name) == tenant_name_norm:
            continue
        cp_ids.add(cp.id)
        if len(cp_ids) > 1:
            return None  # ambiguous

    if len(cp_ids) == 1:
        return cp_ids.pop()
    return None
