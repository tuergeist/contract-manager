"""Contract merge service — transfer all items from a source contract to a target contract."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max

from apps.contracts.models import (
    Contract,
    ContractAmendment,
    ContractItem,
    TimeTrackingProjectMapping,
    calculate_arr_value,
)


def validate_merge_preconditions(source: Contract, target: Contract) -> list[str]:
    """Validate that two contracts can be merged. Returns list of error messages (empty = valid)."""
    errors = []

    if source.id == target.id:
        errors.append("Cannot merge a contract into itself")

    if source.customer_id != target.customer_id:
        errors.append("Contracts must belong to the same customer")

    if source.status not in (Contract.Status.DRAFT, Contract.Status.ACTIVE):
        errors.append("Only draft or active contracts can be merged")

    if target.status in (
        Contract.Status.DELETED,
        Contract.Status.CANCELLED,
        Contract.Status.ENDED,
    ):
        errors.append("Target contract is not in a mergeable state")

    # Check for invoices on source
    if source.invoice_records.exists() or source.imported_invoices.exists():
        errors.append("Source contract has invoices and cannot be merged")

    return errors


def preview_merge(source: Contract, target: Contract) -> dict:
    """Preview what a merge would do. Returns structured preview data.

    Assumes preconditions have already been validated.
    """
    items = list(source.items.select_related("product").all())

    items_preview = []
    for item in items:
        items_preview.append({
            "id": item.id,
            "product_name": item.product.name if item.product else None,
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "price_period": item.price_period,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "billing_start_date": item.billing_start_date.isoformat() if item.billing_start_date else None,
            "is_one_off": item.is_one_off,
        })

    # Amendment info
    will_create_amendments = target.status != Contract.Status.DRAFT

    # Clockodo preview
    clockodo_preview = None
    try:
        from apps.contracts.services.clockodo_provisioning import preview_activation
        from apps.contracts.services.time_tracking import get_provider

        provider = get_provider(target.tenant)
        if provider and target.time_tracking_mappings.exists():
            # Show what new projects would be needed for transferred items
            has_new_recurring = any(not item.is_one_off for item in items)
            new_one_offs = [
                {"id": item.id, "description": item.description}
                for item in items
                if item.is_one_off
            ]
            clockodo_preview = {
                "has_new_recurring_items": has_new_recurring,
                "new_one_off_items": new_one_offs,
                "source_mappings_will_be_deleted": source.time_tracking_mappings.count(),
            }
    except Exception:
        pass

    return {
        "items": items_preview,
        "will_create_amendments": will_create_amendments,
        "clockodo_preview": clockodo_preview,
        "source_contract_name": source.name,
        "target_contract_name": target.name,
    }


def execute_merge(
    source: Contract,
    target: Contract,
    item_overrides: dict[int, dict] | None = None,
    user=None,
) -> Contract:
    """Execute the merge: transfer all items from source to target.

    Args:
        source: The contract whose items will be transferred.
        target: The contract that receives the items.
        item_overrides: Optional dict mapping item_id -> {start_date?, billing_start_date?}
        user: The user performing the merge (for tenant on amendments).

    Returns:
        The updated target contract.

    Raises:
        ValueError: If preconditions are not met.
    """
    item_overrides = item_overrides or {}
    tenant = source.tenant

    with transaction.atomic():
        # Re-validate inside transaction to prevent race conditions
        errors = validate_merge_preconditions(source, target)
        if errors:
            raise ValueError("; ".join(errors))

        items = list(source.items.select_related("product").all())

        # Compute max sort_order for recurring and one-off items on target
        target_recurring_max = (
            target.items.filter(is_one_off=False)
            .aggregate(max_order=Max("sort_order"))["max_order"]
        ) or 0
        target_oneoff_max = (
            target.items.filter(is_one_off=True)
            .aggregate(max_order=Max("sort_order"))["max_order"]
        ) or 0

        recurring_counter = target_recurring_max + 1
        oneoff_counter = target_oneoff_max + 1

        source_deal_id = source.hubspot_deal_id

        for item in items:
            # Apply date overrides if provided
            overrides = item_overrides.get(item.id, {})
            if "start_date" in overrides:
                item.start_date = overrides["start_date"]
            if "billing_start_date" in overrides:
                item.billing_start_date = overrides["billing_start_date"]

            # Assign sort_order
            if item.is_one_off:
                item.sort_order = oneoff_counter
                oneoff_counter += 1
            else:
                item.sort_order = recurring_counter
                recurring_counter += 1

            # Preserve HubSpot deal ID
            if source_deal_id:
                item.source_hubspot_deal_id = source_deal_id

            # Clear dependency references (they're contract-scoped)
            item.depends_on = None

            # Transfer to target
            item.contract = target

            # Create amendment for active target
            if target.status != Contract.Status.DRAFT:
                item_name = item.product.name if item.product else (item.description[:50] if item.description else f"Item {item.id}")
                arr_delta = calculate_arr_value(
                    item.unit_price,
                    item.quantity,
                    item.price_period,
                    item.is_one_off,
                )
                amendment = ContractAmendment.objects.create(
                    tenant=tenant,
                    contract=target,
                    effective_date=item.start_date or date.today(),
                    type=ContractAmendment.AmendmentType.PRODUCT_ADDED,
                    description=f"Merged {item_name} x{item.quantity} from {source.name}",
                    changes={
                        "product_id": str(item.product_id) if item.product_id else None,
                        "product_name": item.product.name if item.product else None,
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "price_period": item.price_period,
                        "is_one_off": item.is_one_off,
                        "merged_from_contract_id": str(source.id),
                    },
                    arr_delta=arr_delta,
                )
                item.added_by_amendment = amendment

            item.save()

        # Delete source Clockodo mappings
        TimeTrackingProjectMapping.objects.filter(contract=source).delete()

        # Set source to DELETED
        source.status = Contract.Status.DELETED
        source.save(update_fields=["status", "updated_at"])

    # Refresh target from DB
    target.refresh_from_db()
    return target
