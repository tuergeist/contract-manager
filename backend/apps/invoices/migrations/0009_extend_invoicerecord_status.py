"""Extend InvoiceRecord status choices with future-ready statuses."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0008_alter_importedinvoice_extraction_status"),
    ]

    operations = [
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
                    ("storno", "Storno"),
                    ("cancelled", "Cancelled"),
                ],
                default="draft",
                max_length=10,
            ),
        ),
    ]
