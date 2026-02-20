"""Invoice lifecycle audit logging helpers.

Creates targeted audit entries for key invoice events (creation, email sent,
voided) rather than registering InvoiceRecord for signal-based auditing,
which would be too noisy with PDF generation, field updates, etc.
"""

import logging

from apps.audit.models import AuditLog
from apps.audit.services import get_current_user

logger = logging.getLogger(__name__)


def log_invoice_created(record, *, user=None) -> AuditLog | None:
    """Log an audit entry when an invoice record is created."""
    try:
        return AuditLog.objects.create(
            tenant=record.tenant,
            action=AuditLog.Action.CREATE,
            entity_type="invoice_record",
            entity_id=record.pk,
            entity_repr=f"Invoice {record.invoice_number}",
            user=user or get_current_user(),
            changes={
                "invoice_number": {"old": None, "new": record.invoice_number},
                "status": {"old": None, "new": record.status},
                "total_gross": {"old": None, "new": str(record.total_gross)},
                "customer_name": {"old": None, "new": record.customer_name},
                "contract_name": {"old": None, "new": record.contract_name},
            },
        )
    except Exception:
        logger.exception("Failed to log invoice creation for record %s", record.pk)
        return None


def log_invoice_email_sent(record, recipients: list[str], *, user=None) -> AuditLog | None:
    """Log an audit entry when an invoice email is sent."""
    try:
        return AuditLog.objects.create(
            tenant=record.tenant,
            action=AuditLog.Action.UPDATE,
            entity_type="invoice_record",
            entity_id=record.pk,
            entity_repr=f"Invoice {record.invoice_number}",
            user=user or get_current_user(),
            changes={
                "email_sent_to": {"old": None, "new": recipients},
                "email_sent_at": {
                    "old": None,
                    "new": record.email_sent_at.isoformat() if record.email_sent_at else None,
                },
            },
        )
    except Exception:
        logger.exception("Failed to log invoice email sent for record %s", record.pk)
        return None


def log_invoice_voided(record, *, user=None) -> AuditLog | None:
    """Log an audit entry when an invoice is voided."""
    try:
        return AuditLog.objects.create(
            tenant=record.tenant,
            action=AuditLog.Action.UPDATE,
            entity_type="invoice_record",
            entity_id=record.pk,
            entity_repr=f"Invoice {record.invoice_number}",
            user=user or get_current_user(),
            changes={
                "status": {"old": "finalized", "new": "voided"},
                "void_reason": {"old": None, "new": record.void_reason},
            },
        )
    except Exception:
        logger.exception("Failed to log invoice voided for record %s", record.pk)
        return None
