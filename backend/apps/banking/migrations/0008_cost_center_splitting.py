"""Add cost center split rule, allocation, and transaction split models."""
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("banking", "0007_cost_center"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CostCenterSplitRule",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("booking_text_pattern", models.CharField(blank=True, help_text="Regex or substring pattern to match booking text", max_length=255, null=True)),
                ("priority", models.IntegerField(default=0, help_text="Higher priority rules are evaluated first")),
                ("is_active", models.BooleanField(default=True)),
                ("counterparty", models.ForeignKey(blank=True, help_text="Match transactions with this counterparty", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="split_rules", to="banking.counterparty")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.tenant")),
            ],
            options={
                "ordering": ["-priority", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="costcentersplitrule",
            constraint=models.CheckConstraint(
                condition=~models.Q(("counterparty__isnull", True), ("booking_text_pattern__isnull", True)) & ~models.Q(("counterparty__isnull", True), ("booking_text_pattern", "")),
                name="split_rule_must_have_matcher",
            ),
        ),
        migrations.CreateModel(
            name="CostCenterSplitAllocation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("percentage", models.DecimalField(blank=True, decimal_places=4, help_text="Percentage of transaction amount (0-100)", max_digits=7, null=True)),
                ("fixed_amount", models.DecimalField(blank=True, decimal_places=2, help_text="Fixed amount to allocate", max_digits=14, null=True)),
                ("cost_center", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="split_allocations", to="banking.costcenter")),
                ("rule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="allocations", to="banking.costcentersplitrule")),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="TransactionCostCenterSplit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("is_manual", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cost_center", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transaction_splits", to="banking.costcenter")),
                ("rule", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applied_splits", to="banking.costcentersplitrule")),
                ("transaction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cost_center_splits", to="banking.banktransaction")),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
