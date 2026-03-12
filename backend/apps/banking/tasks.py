"""Celery tasks for banking app."""

import logging
from datetime import date

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


@shared_task(ignore_result=True)
def capture_monthly_fte_snapshots():
    """Daily task: capture FTE distribution snapshots on configured day of month.

    For each tenant, checks if today matches their configured capture day.
    If so, captures last month's snapshot (skips if already exists).
    """
    from apps.banking.services.fte_snapshot import capture_snapshot
    from apps.tenants.models import Tenant

    today = date.today()

    # Compute last month
    if today.month == 1:
        last_year_month = f"{today.year - 1}-12"
    else:
        last_year_month = f"{today.year}-{today.month - 1:02d}"

    for tenant in Tenant.objects.filter(is_active=True):
        settings = tenant.settings or {}
        capture_day = settings.get("fte_snapshot_capture_day", 7)

        if today.day != capture_day:
            continue

        try:
            snapshot = capture_snapshot(tenant, last_year_month)
            logger.info(
                "Captured FTE snapshot for tenant %s, month %s",
                tenant.name, last_year_month,
            )
        except ValueError as e:
            # Expected: snapshot already exists or no data
            logger.debug("Skipped FTE snapshot for %s: %s", tenant.name, e)
        except Exception:
            logger.exception("Error capturing FTE snapshot for %s", tenant.name)
