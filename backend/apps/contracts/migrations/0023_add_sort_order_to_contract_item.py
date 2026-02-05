"""Add sort_order field to ContractItem and populate from created_at order."""

from django.db import migrations, models


def populate_sort_order(apps, schema_editor):
    """Set sort_order based on created_at order, per contract, separately for recurring/one-off."""
    ContractItem = apps.get_model("contracts", "ContractItem")
    Contract = apps.get_model("contracts", "Contract")

    for contract in Contract.objects.all():
        # Recurring items
        recurring = ContractItem.objects.filter(
            contract=contract, is_one_off=False
        ).order_by("created_at")
        for i, item in enumerate(recurring):
            item.sort_order = i
            item.save(update_fields=["sort_order"])

        # One-off items
        one_off = ContractItem.objects.filter(
            contract=contract, is_one_off=True
        ).order_by("created_at")
        for i, item in enumerate(one_off):
            item.sort_order = i
            item.save(update_fields=["sort_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0022_convert_discount_to_line_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractitem",
            name="sort_order",
            field=models.IntegerField(
                blank=True,
                help_text="Sort order within the contract (per recurring/one-off group)",
                null=True,
            ),
        ),
        migrations.AlterModelOptions(
            name="contractitem",
            options={"ordering": ["sort_order", "created_at"]},
        ),
        migrations.RunPython(populate_sort_order, migrations.RunPython.noop),
    ]
