"""Celery tasks for invoice processing."""

import logging

from celery import shared_task

from apps.invoices.extraction import run_extraction
from apps.invoices.models import ImportedInvoice

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
