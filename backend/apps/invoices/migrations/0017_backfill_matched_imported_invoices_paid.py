from django.db import migrations


def backfill_matched_to_paid(apps, schema_editor):
    ImportedInvoice = apps.get_model("invoices", "ImportedInvoice")
    updated = ImportedInvoice.objects.filter(
        payment_matches__isnull=False,
    ).exclude(
        extraction_status="paid",
    ).update(extraction_status="paid")
    if updated:
        print(f"\n  Updated {updated} matched imported invoices to 'paid'")


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0016_alter_importedinvoice_extraction_status"),
    ]

    operations = [
        migrations.RunPython(backfill_matched_to_paid, migrations.RunPython.noop),
    ]
