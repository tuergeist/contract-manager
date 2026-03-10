from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("banking", "0007_counterparty_exclude_from_forecast"),
        ("banking", "0007_incoming_invoice_models"),
        ("banking", "0008_cost_center_splitting"),
    ]

    operations = []
