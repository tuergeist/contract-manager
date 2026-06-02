"""Backfill due_date for existing invoices.

Sets due_date = invoice_date + default payment term for every InvoiceRecord
that has an invoice_date but no due_date yet. Uses a single flat default;
per-customer / per-contract terms only apply to invoices created afterwards.
"""
from datetime import timedelta

from django.db import migrations

DEFAULT_PAYMENT_TERM_DAYS = 14


def backfill_due_date(apps, schema_editor):
    InvoiceRecord = apps.get_model("invoices", "InvoiceRecord")

    records = InvoiceRecord.objects.filter(
        due_date__isnull=True, invoice_date__isnull=False
    )
    to_update = []
    for record in records.iterator():
        record.due_date = record.invoice_date + timedelta(
            days=DEFAULT_PAYMENT_TERM_DAYS
        )
        to_update.append(record)
        if len(to_update) >= 500:
            InvoiceRecord.objects.bulk_update(to_update, ["due_date"])
            to_update = []
    if to_update:
        InvoiceRecord.objects.bulk_update(to_update, ["due_date"])


def noop(apps, schema_editor):
    """Reverse: leave due_date as-is (harmless)."""


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0025_invoicerecord_due_date_paymentreminder"),
    ]

    operations = [
        migrations.RunPython(backfill_due_date, noop),
    ]
