"""Service for moving contract line items between contracts."""
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Max

from apps.contracts.models import (
    Contract,
    ContractAmendment,
    ContractItem,
    ContractItemPrice,
    calculate_arr_value,
)

logger = logging.getLogger(__name__)


def validate_move(item: ContractItem, target_contract: Contract, effective_date: date) -> list[str]:
    """Validate preconditions for moving a line item. Returns list of error messages."""
    errors = []

    if item.is_one_off:
        errors.append("One-off items cannot be moved.")

    if item.moved_to_id is not None:
        errors.append("This item has already been moved.")

    if item.contract_id == target_contract.id:
        errors.append("Source and target contract must be different.")

    if item.contract.customer_id != target_contract.customer_id:
        errors.append("Target contract must belong to the same customer.")

    blocked_statuses = {Contract.Status.DELETED, Contract.Status.CANCELLED, Contract.Status.ENDED}
    if target_contract.status in blocked_statuses:
        errors.append("Target contract is not active.")

    if effective_date < date.today():
        errors.append("Effective date must be today or in the future.")

    if item.billing_end_date and effective_date > item.billing_end_date:
        errors.append("Effective date must be on or before the item's existing billing end date.")

    return errors


def execute_move(
    item: ContractItem,
    target_contract: Contract,
    effective_date: date,
) -> tuple[ContractItem, ContractItem]:
    """Move a line item: end it on source contract, create copy on target.

    Returns (source_item, new_item).
    """
    with transaction.atomic():
        # Re-fetch with lock
        item = ContractItem.objects.select_related("contract", "product").select_for_update().get(pk=item.pk)
        target_contract = Contract.objects.select_for_update().get(pk=target_contract.pk)

        errors = validate_move(item, target_contract, effective_date)
        if errors:
            raise ValueError(errors[0])

        billing_start = effective_date + timedelta(days=1)
        item_name = item.product.name if item.product else (item.description or f"Item #{item.pk}")

        # --- End on source ---
        item.billing_end_date = effective_date
        item.save(update_fields=["billing_end_date", "updated_at"])

        # --- Create copy on target ---
        next_sort = (
            ContractItem.objects.filter(contract=target_contract, is_one_off=False)
            .aggregate(m=Max("sort_order"))["m"]
        )
        next_sort = (next_sort or 0) + 1

        new_item = ContractItem.objects.create(
            tenant=item.tenant,
            contract=target_contract,
            product=item.product,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            price_period=item.price_period,
            price_source=item.price_source,
            start_date=billing_start,
            billing_start_date=billing_start,
            billing_end_date=None,
            align_to_contract_at=None,
            is_one_off=False,
            revenue_type=item.revenue_type,
            order_confirmation_number=item.order_confirmation_number,
            price_locked=item.price_locked,
            price_locked_until=item.price_locked_until,
            sort_order=next_sort,
            depends_on=None,
            delivery_status=None,
        )

        # --- Link ---
        item.moved_to = new_item
        item.save(update_fields=["moved_to", "updated_at"])

        # --- Copy future price periods ---
        for pp in ContractItemPrice.objects.filter(item=item):
            # Skip periods that end before the move
            if pp.valid_to and pp.valid_to <= effective_date:
                continue
            ContractItemPrice.objects.create(
                tenant=pp.tenant,
                item=new_item,
                valid_from=max(pp.valid_from, billing_start),
                valid_to=pp.valid_to,
                unit_price=pp.unit_price,
                price_period=pp.price_period,
                source=pp.source,
                increase_type=pp.increase_type,
            )

        # --- Amendments ---
        arr = calculate_arr_value(item.unit_price, item.quantity, item.price_period, False)

        source_contract = item.contract
        if source_contract.status != Contract.Status.DRAFT:
            ContractAmendment.objects.create(
                tenant=item.tenant,
                contract=source_contract,
                effective_date=effective_date,
                type=ContractAmendment.AmendmentType.PRODUCT_REMOVED,
                description=f"{item_name} moved to {target_contract.name}",
                changes={"moved_to_contract_id": target_contract.id, "item_id": item.id},
                arr_delta=-arr,
            )

        if target_contract.status != Contract.Status.DRAFT:
            amendment = ContractAmendment.objects.create(
                tenant=item.tenant,
                contract=target_contract,
                effective_date=billing_start,
                type=ContractAmendment.AmendmentType.PRODUCT_ADDED,
                description=f"{item_name} moved from {source_contract.name}",
                changes={"moved_from_contract_id": source_contract.id, "item_id": new_item.id},
                arr_delta=arr,
            )
            new_item.added_by_amendment = amendment
            new_item.save(update_fields=["added_by_amendment", "updated_at"])

        logger.info(
            "Moved item %s from contract %s to %s (effective %s)",
            item.pk, source_contract.pk, target_contract.pk, effective_date,
        )

        return item, new_item
