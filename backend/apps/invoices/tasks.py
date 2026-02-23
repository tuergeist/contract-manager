"""Celery tasks for invoice processing."""

import logging

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.invoices.extraction import run_extraction
from apps.invoices.models import ImportedInvoice, InvoiceRecord

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,  # 10 second delay before retry
    retry_kwargs={"max_retries": 1},  # 1 retry attempt
    acks_late=True,  # Don't ack until task completes (survives worker crash)
)
def extract_invoice_task(self, invoice_id: int) -> bool:
    """
    Background task to extract metadata from an uploaded invoice PDF.

    Args:
        invoice_id: ID of the ImportedInvoice to process

    Returns:
        True if extraction succeeded, False otherwise
    """
    try:
        invoice = ImportedInvoice.objects.get(id=invoice_id)
    except ImportedInvoice.DoesNotExist:
        logger.error("Invoice %s not found for extraction", invoice_id)
        return False

    # Skip if already extracted or confirmed
    if invoice.extraction_status in [
        ImportedInvoice.ExtractionStatus.EXTRACTED,
        ImportedInvoice.ExtractionStatus.CONFIRMED,
    ]:
        logger.info("Invoice %s already extracted, skipping", invoice_id)
        return True

    # Mark as extracting
    invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTING
    invoice.save(update_fields=["extraction_status", "updated_at"])

    logger.info("Starting extraction for invoice %s (attempt %s)", invoice_id, self.request.retries + 1)

    try:
        # run_extraction handles its own status updates for success/failure
        success = run_extraction(invoice)

        if not success and self.request.retries < self.max_retries:
            # Will be retried by Celery
            raise Exception(f"Extraction failed: {invoice.extraction_error}")

        return success

    except Exception as e:
        # On final failure, ensure status is set to failed
        if self.request.retries >= self.max_retries:
            invoice.refresh_from_db()
            if invoice.extraction_status != ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED:
                invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED
                invoice.extraction_error = str(e)
                invoice.save(update_fields=["extraction_status", "extraction_error", "updated_at"])
            logger.error("Extraction failed for invoice %s after retries: %s", invoice_id, e)
            return False
        raise  # Re-raise for Celery retry


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 1},
    acks_late=True,
)
def generate_invoice_pdf_task(self, record_id: int) -> bool:
    """
    Background task to generate a ZUGFeRD PDF for an InvoiceRecord and store it.

    Args:
        record_id: ID of the InvoiceRecord to process

    Returns:
        True if generation succeeded, False otherwise
    """
    try:
        record = InvoiceRecord.objects.select_related(
            "customer", "contract", "tenant"
        ).get(id=record_id)
    except InvoiceRecord.DoesNotExist:
        logger.error("InvoiceRecord %s not found for PDF generation", record_id)
        return False

    # Idempotent: skip if pdf_file already set
    if record.pdf_file:
        logger.info("InvoiceRecord %s already has PDF, skipping", record_id)
        return True

    logger.info(
        "Generating ZUGFeRD PDF for InvoiceRecord %s (attempt %s)",
        record_id,
        self.request.retries + 1,
    )

    try:
        from apps.invoices.services import InvoiceService, _get_company_language

        # Resolve language: customer preference > company default
        language = _get_company_language(record.tenant)
        if record.customer and getattr(record.customer, "invoice_language", None):
            language = record.customer.invoice_language

        service = InvoiceService(record.tenant)
        pdf_bytes = service.generate_zugferd_pdf_for_record(record, language=language)

        filename = f"invoice-{record.invoice_number}.pdf"
        record.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        logger.info("ZUGFeRD PDF saved for InvoiceRecord %s", record_id)
        return True

    except Exception as e:
        if self.request.retries >= self.max_retries:
            logger.error(
                "PDF generation failed for InvoiceRecord %s after retries: %s",
                record_id,
                e,
            )
            return False
        raise


EMAIL_TEMPLATES = {
    "de": {
        "subject": "Rechnung {invoice_number}",
        "body": """\
<p>Sehr geehrte Damen und Herren,</p>
<p>anbei erhalten Sie unsere Rechnung <strong>{invoice_number}</strong> \
über {total_gross} {currency} für den Zeitraum {period_start} – {period_end}.</p>
<p>Die Rechnung finden Sie als PDF im Anhang.</p>
<p>Mit freundlichen Grüßen<br>{company_name}</p>""",
    },
    "en": {
        "subject": "Invoice {invoice_number}",
        "body": """\
<p>Dear Sir or Madam,</p>
<p>Please find attached our invoice <strong>{invoice_number}</strong> \
for {total_gross} {currency} covering the period {period_start} – {period_end}.</p>
<p>The invoice is attached as a PDF.</p>
<p>Best regards,<br>{company_name}</p>""",
    },
}


def _get_email_template(tenant, lang: str) -> dict:
    """Get email template for a language, preferring tenant custom templates.

    Returns dict with 'subject' and 'body' keys.
    Falls back to hardcoded EMAIL_TEMPLATES defaults.
    """
    if lang not in EMAIL_TEMPLATES:
        lang = "de"

    custom = (tenant.settings or {}).get("invoice_email_templates", {}).get(lang, {})
    if custom.get("subject") and custom.get("body"):
        return {"subject": custom["subject"], "body": custom["body"]}

    return EMAIL_TEMPLATES[lang]


@shared_task(bind=True, acks_late=True)
def send_invoice_email_task(self, record_id: int, user_id: int | None = None) -> bool:
    """Send an invoice email via M365 Graph API.

    No automatic retry to avoid duplicate sends.
    """
    from apps.core.m365 import M365Error, send_mail

    try:
        record = InvoiceRecord.objects.select_related(
            "customer", "tenant"
        ).get(id=record_id)
    except InvoiceRecord.DoesNotExist:
        logger.error("InvoiceRecord %s not found for email sending", record_id)
        return False

    customer = record.customer
    if not customer:
        logger.error("InvoiceRecord %s has no customer", record_id)
        return False

    recipients = customer.billing_emails or []
    if not recipients:
        logger.error("Customer %s has no billing_emails", customer.id)
        return False

    if not record.pdf_file:
        logger.error("InvoiceRecord %s has no PDF file", record_id)
        return False

    # Determine language
    lang = getattr(customer, "invoice_language", "") or "en"
    if lang not in EMAIL_TEMPLATES:
        lang = "de"

    template = _get_email_template(record.tenant, lang)
    company_data = record.company_data_snapshot or {}
    company_name = company_data.get("company_name", "")
    currency = record.tenant.currency if record.tenant else "EUR"

    format_kwargs = dict(
        invoice_number=record.invoice_number,
        total_gross=f"{record.total_gross:,.2f}",
        currency=currency,
        period_start=record.period_start.strftime("%d.%m.%Y"),
        period_end=record.period_end.strftime("%d.%m.%Y"),
        company_name=company_name,
    )

    try:
        subject = template["subject"].format(**format_kwargs)
        body_html = template["body"].format(**format_kwargs)
    except (KeyError, ValueError) as e:
        logger.warning(
            "Custom email template rendering failed for record %s, falling back to default: %s",
            record_id, e,
        )
        fallback = EMAIL_TEMPLATES[lang]
        subject = fallback["subject"].format(**format_kwargs)
        body_html = fallback["body"].format(**format_kwargs)

    # Read PDF attachment
    pdf_bytes = record.pdf_file.read()
    attachments = [
        {
            "name": f"{record.invoice_number}.pdf",
            "content_type": "application/pdf",
            "content_bytes": pdf_bytes,
        }
    ]

    try:
        message_id = send_mail(
            record.tenant,
            to=recipients,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
        )
        record.email_sent_at = timezone.now()
        record.email_sent_to = recipients
        record.email_message_id = message_id or ""
        record.status = InvoiceRecord.Status.SENT
        record.save(update_fields=["email_sent_at", "email_sent_to", "email_message_id", "status"])

        from apps.invoices.audit import log_invoice_email_sent
        from apps.tenants.models import User
        triggered_by = None
        if user_id:
            triggered_by = User.objects.filter(id=user_id).first()
        log_invoice_email_sent(record, recipients, user=triggered_by)

        logger.info("Invoice email sent for record %s to %s", record_id, recipients)
        return True
    except M365Error as e:
        logger.error("Failed to send invoice email for record %s: %s", record_id, e)
        return False
