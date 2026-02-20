"""Backfill audit log entries for existing InvoiceRecords.

Creates audit entries for:
- All records: CREATE entry with timestamp = generated_at
- Records with email_sent_at: UPDATE entry for email sent
- Voided records: UPDATE entry for void action
"""

from django.db import migrations


def backfill_audit_logs(apps, schema_editor):
    AuditLog = apps.get_model("audit", "AuditLog")
    InvoiceRecord = apps.get_model("invoices", "InvoiceRecord")

    for record in InvoiceRecord.objects.iterator(chunk_size=500):
        # 1. CREATE entry for every record
        entry = AuditLog.objects.create(
            tenant_id=record.tenant_id,
            action="create",
            entity_type="invoice_record",
            entity_id=record.pk,
            entity_repr=f"Invoice {record.invoice_number}",
            user=None,
            changes={
                "invoice_number": {"old": None, "new": record.invoice_number},
                "status": {"old": None, "new": record.status},
                "total_gross": {"old": None, "new": str(record.total_gross)},
                "customer_name": {"old": None, "new": record.customer_name},
                "contract_name": {"old": None, "new": record.contract_name},
            },
        )
        # Override auto_now_add timestamp
        AuditLog.objects.filter(pk=entry.pk).update(timestamp=record.generated_at)

        # 2. UPDATE entry for email sent
        if record.email_sent_at:
            email_entry = AuditLog.objects.create(
                tenant_id=record.tenant_id,
                action="update",
                entity_type="invoice_record",
                entity_id=record.pk,
                entity_repr=f"Invoice {record.invoice_number}",
                user=None,
                changes={
                    "email_sent_to": {"old": None, "new": record.email_sent_to or []},
                    "email_sent_at": {
                        "old": None,
                        "new": record.email_sent_at.isoformat(),
                    },
                },
            )
            AuditLog.objects.filter(pk=email_entry.pk).update(
                timestamp=record.email_sent_at
            )

        # 3. UPDATE entry for voided records
        if record.status == "voided":
            void_entry = AuditLog.objects.create(
                tenant_id=record.tenant_id,
                action="update",
                entity_type="invoice_record",
                entity_id=record.pk,
                entity_repr=f"Invoice {record.invoice_number}",
                user=None,
                changes={
                    "status": {"old": "finalized", "new": "voided"},
                    "void_reason": {"old": None, "new": record.void_reason or ""},
                },
            )
            AuditLog.objects.filter(pk=void_entry.pk).update(
                timestamp=record.updated_at
            )


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0014_add_void_reason"),
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_audit_logs, migrations.RunPython.noop),
    ]
