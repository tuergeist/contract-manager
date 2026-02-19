from django.db import migrations, models


def migrate_statuses_forward(apps, schema_editor):
    InvoiceRecord = apps.get_model("invoices", "InvoiceRecord")
    InvoiceRecord.objects.filter(status__in=["storno", "cancelled"]).update(
        status="voided"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0012_invoicerecord_invoice_date"),
    ]

    operations = [
        # First migrate data while old choices still exist
        migrations.RunPython(migrate_statuses_forward, migrations.RunPython.noop),
        # Then update the field choices
        migrations.AlterField(
            model_name="invoicerecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("finalized", "Finalized"),
                    ("sent", "Sent"),
                    ("paid", "Paid"),
                    ("dunning", "Dunning"),
                    ("voided", "Voided"),
                ],
                default="draft",
                max_length=10,
            ),
        ),
    ]
