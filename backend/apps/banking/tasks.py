"""Celery tasks for banking app."""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def poll_invoice_inboxes():
    """Poll all active invoice inboxes for new emails with PDF attachments."""
    from apps.banking.models import InvoiceInbox
    from apps.banking.services.inbox_polling import InboxPollingService
    from apps.banking.services.incoming_extraction import run_incoming_extraction

    service = InboxPollingService()
    now = timezone.now()

    for inbox in InvoiceInbox.objects.filter(is_active=True):
        if inbox.last_polled_at:
            minutes_since = (now - inbox.last_polled_at).total_seconds() / 60
            if minutes_since < inbox.poll_interval_minutes:
                continue

        logger.info("Polling inbox %s (%s)", inbox.name, inbox.id)
        try:
            created = service.poll_inbox(inbox)
            inbox.last_polled_at = now
            inbox.save(update_fields=["last_polled_at", "updated_at"])

            for invoice in created:
                try:
                    run_incoming_extraction(invoice)
                except Exception as e:
                    logger.error("Extraction failed for invoice %s: %s", invoice.id, e)

            logger.info("Inbox %s: created %d invoices", inbox.name, len(created))
        except Exception as e:
            logger.error("Error polling inbox %s: %s", inbox.id, e)
