"""Backfill: treat invoice_date as the sent date.

Any non-voided, non-credit-note ImportedInvoice that has an invoice_date
and is currently in EXTRACTED or CONFIRMED state should be promoted to
SENT, since the invoice_date represents the date the invoice was issued
to the customer (an imported invoice with a date was, by definition,
already sent).

PAID rows already imply SENT and are left alone. VOIDED and credit notes
are excluded.

Reverse migration: SENT rows without a payment match are returned to
CONFIRMED. The original EXTRACTED vs CONFIRMED distinction is lost on
reverse (acceptable: confirmed is a strict superset of extracted in the
review lifecycle).
"""

from django.db import migrations


def backfill_sent_status(apps, schema_editor):
    ImportedInvoice = apps.get_model("invoices", "ImportedInvoice")
    ImportedInvoice.objects.filter(
        extraction_status__in=["extracted", "confirmed"],
        invoice_date__isnull=False,
        document_type="invoice",
    ).update(extraction_status="sent")


def reverse_backfill_sent_status(apps, schema_editor):
    ImportedInvoice = apps.get_model("invoices", "ImportedInvoice")
    ImportedInvoice.objects.filter(
        extraction_status="sent",
        invoice_date__isnull=False,
        payment_matches__isnull=True,
    ).update(extraction_status="confirmed")


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0028_importedinvoice_document_type_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_sent_status,
            reverse_code=reverse_backfill_sent_status,
        ),
    ]
