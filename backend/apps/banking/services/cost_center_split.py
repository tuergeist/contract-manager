"""Service for auto-applying cost center split rules to transactions."""
import re
from decimal import Decimal, ROUND_HALF_UP

from apps.banking.models import (
    BankTransaction,
    CostCenterSplitRule,
    TransactionCostCenterSplit,
)


class CostCenterSplitService:
    """Finds matching split rules and creates transaction splits."""

    @staticmethod
    def find_matching_rule(transaction: BankTransaction) -> CostCenterSplitRule | None:
        """Find the best matching active split rule for a transaction.

        Priority order:
        1. Counterparty-specific rules (higher priority first)
        2. Booking text pattern rules (higher priority first)
        """
        tenant = transaction.tenant

        # First: counterparty-specific rules
        if transaction.counterparty_id:
            rule = (
                CostCenterSplitRule.objects.filter(
                    tenant=tenant,
                    is_active=True,
                    counterparty=transaction.counterparty,
                )
                .order_by("-priority", "id")
                .first()
            )
            if rule:
                return rule

        # Second: booking text pattern rules
        pattern_rules = (
            CostCenterSplitRule.objects.filter(
                tenant=tenant,
                is_active=True,
                counterparty__isnull=True,
            )
            .exclude(booking_text_pattern__isnull=True)
            .exclude(booking_text_pattern="")
            .order_by("-priority", "id")
        )

        booking_text = transaction.booking_text or ""
        for rule in pattern_rules:
            pattern = rule.booking_text_pattern
            try:
                if re.search(pattern, booking_text, re.IGNORECASE):
                    return rule
            except re.error:
                # Fall back to substring match if pattern is invalid regex
                if pattern.lower() in booking_text.lower():
                    return rule

        return None

    @staticmethod
    def apply_rule(transaction: BankTransaction) -> list[TransactionCostCenterSplit]:
        """Find matching rule and create split allocations for a transaction.

        Returns created splits, or empty list if no rule matches.
        Does NOT overwrite manual splits.
        """
        # Don't overwrite manual splits
        if TransactionCostCenterSplit.objects.filter(
            transaction=transaction, is_manual=True
        ).exists():
            return []

        rule = CostCenterSplitService.find_matching_rule(transaction)
        if not rule:
            return []

        allocations = rule.allocations.select_related("cost_center").all()
        if not allocations:
            return []

        # Remove existing auto-applied splits
        TransactionCostCenterSplit.objects.filter(
            transaction=transaction, is_manual=False
        ).delete()

        txn_amount = abs(transaction.amount)
        splits = []

        # Check if this is a percentage-based or fixed-amount rule
        has_percentage = any(a.percentage is not None for a in allocations)

        if has_percentage:
            allocated = Decimal("0")
            alloc_list = list(allocations)
            for i, alloc in enumerate(alloc_list):
                pct = alloc.percentage or Decimal("0")
                if i == len(alloc_list) - 1:
                    # Last allocation gets the remainder to avoid rounding issues
                    amount = txn_amount - allocated
                else:
                    amount = (txn_amount * pct / Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                allocated += amount
                splits.append(
                    TransactionCostCenterSplit(
                        transaction=transaction,
                        cost_center=alloc.cost_center,
                        amount=amount,
                        is_manual=False,
                        rule=rule,
                    )
                )
        else:
            # Fixed amount allocations
            allocated = Decimal("0")
            remainder_alloc = None
            for alloc in allocations:
                if alloc.fixed_amount is None:
                    remainder_alloc = alloc
                    continue
                amount = min(alloc.fixed_amount, txn_amount - allocated)
                allocated += amount
                splits.append(
                    TransactionCostCenterSplit(
                        transaction=transaction,
                        cost_center=alloc.cost_center,
                        amount=amount,
                        is_manual=False,
                        rule=rule,
                    )
                )
            if remainder_alloc and allocated < txn_amount:
                splits.append(
                    TransactionCostCenterSplit(
                        transaction=transaction,
                        cost_center=remainder_alloc.cost_center,
                        amount=txn_amount - allocated,
                        is_manual=False,
                        rule=rule,
                    )
                )

        TransactionCostCenterSplit.objects.bulk_create(splits)
        return splits
