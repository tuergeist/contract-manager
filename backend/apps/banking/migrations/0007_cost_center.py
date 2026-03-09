# Generated manually for cost centers feature

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("banking", "0006_imported_invoice"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CostCenter",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="Short code, e.g. 100, IT, MKTG",
                        max_length=20,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.AddConstraint(
            model_name="costcenter",
            constraint=models.UniqueConstraint(
                fields=("tenant", "code"),
                name="unique_cost_center_code_per_tenant",
            ),
        ),
        migrations.AddField(
            model_name="counterparty",
            name="default_cost_center",
            field=models.ForeignKey(
                blank=True,
                help_text="Default cost center for new transactions with this counterparty",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="counterparties",
                to="banking.costcenter",
            ),
        ),
        migrations.AddField(
            model_name="banktransaction",
            name="cost_center",
            field=models.ForeignKey(
                blank=True,
                help_text="Cost center assignment",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="banking.costcenter",
            ),
        ),
    ]
