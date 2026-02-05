"""Convert Contract.discount_amount into ContractItem line items and remove the field."""

from django.db import migrations


def convert_discounts_to_line_items(apps, schema_editor):
    """For each contract with a discount_amount, create a ContractItem with negative unit_price."""
    Contract = apps.get_model("contracts", "Contract")
    ContractItem = apps.get_model("contracts", "ContractItem")

    contracts = Contract.objects.exclude(discount_amount__isnull=True).exclude(discount_amount=0)
    for contract in contracts:
        ContractItem.objects.create(
            tenant=contract.tenant,
            contract=contract,
            product=None,
            description="Discount",
            quantity=1,
            unit_price=contract.discount_amount,  # already negative
            price_period="monthly",
            price_source="custom",
            is_one_off=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0021_add_time_tracking_project_mapping"),
    ]

    operations = [
        migrations.RunPython(
            convert_discounts_to_line_items,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="contract",
            name="discount_amount",
        ),
    ]
