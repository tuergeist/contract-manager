"""Service for capturing FTE distribution snapshots."""

import calendar
import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def compute_fte_distribution(tenant, year_month: str) -> list[dict] | None:
    """Compute FTE distribution for a given month.

    Returns a list of dicts:
        {department, cost_center, fte_percentage, monthly_income_total, hours_total}

    Returns None if no departments have linked cost centers.
    """
    from apps.contracts.models import Department, DepartmentServiceMapping, UserCostProfile
    from apps.contracts.services.time_tracking import get_provider

    # Get departments with linked cost centers
    departments = Department.objects.filter(
        tenant=tenant, cost_center__isnull=False
    ).select_related("cost_center")

    if not departments.exists():
        return None

    dept_map = {d.id: d for d in departments}

    # Parse year/month
    year, month = int(year_month[:4]), int(year_month[5:7])
    date_from = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    date_to = date(year, month, last_day)

    # Try Clockodo time data first
    provider = get_provider(tenant)
    dept_hours: dict[int, float] = defaultdict(float)
    has_time_data = False

    if provider:
        try:
            raw_data = provider.get_department_time_data(date_from, date_to)
            if raw_data:
                # Map service_id → department via DepartmentServiceMapping
                mappings = DepartmentServiceMapping.objects.filter(
                    tenant=tenant
                ).select_related("department")
                service_to_dept_id: dict[str, int] = {}
                for m in mappings:
                    if m.department_id in dept_map:
                        service_to_dept_id[m.external_service_id] = m.department_id

                for entry in raw_data:
                    dept_id = service_to_dept_id.get(entry["service_id"])
                    if dept_id:
                        dept_hours[dept_id] += entry["hours"]
                        has_time_data = True
        except Exception:
            logger.exception("Failed to fetch Clockodo data for FTE snapshot")

    # Fallback: use UserCostProfile FTE percentages as static weights
    if not has_time_data:
        profiles = UserCostProfile.objects.filter(
            tenant=tenant,
            default_department__isnull=False,
        ).select_related("default_department")
        for p in profiles:
            if p.default_department_id in dept_map:
                dept_hours[p.default_department_id] += float(p.fte_percentage)

    total_hours = sum(dept_hours.values())
    if total_hours == 0:
        return None

    # Compute income totals per department
    profiles = UserCostProfile.objects.filter(
        tenant=tenant,
        default_department__isnull=False,
    ).select_related("default_department")
    dept_income: dict[int, Decimal] = defaultdict(Decimal)
    for p in profiles:
        if p.default_department_id in dept_map:
            dept_income[p.default_department_id] += p.monthly_income or Decimal("0")

    # Build distribution
    result = []
    for dept in departments:
        hours = dept_hours.get(dept.id, 0)
        pct = Decimal(str(hours / total_hours * 100)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        result.append({
            "department": dept,
            "cost_center": dept.cost_center,
            "fte_percentage": pct,
            "monthly_income_total": dept_income.get(dept.id, Decimal("0")),
            "hours_total": Decimal(str(hours)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        })

    return result


@transaction.atomic
def capture_snapshot(tenant, year_month: str, user=None):
    """Capture an FTE distribution snapshot for the given month.

    Args:
        tenant: The tenant to capture for
        year_month: "YYYY-MM" string
        user: Optional user who triggered the capture

    Returns:
        The created FteDistributionSnapshot, or raises ValueError.
    """
    from apps.banking.models import (
        FteDistributionSnapshot,
        FteDistributionEntry,
        CostCenterSplitRule,
        TransactionCostCenterSplit,
        BankTransaction,
    )

    # Validate month is not in the future
    today = date.today()
    year, month = int(year_month[:4]), int(year_month[5:7])
    if date(year, month, 1) > today.replace(day=1):
        raise ValueError("Cannot capture snapshot for a future month")

    # Check uniqueness
    if FteDistributionSnapshot.objects.filter(tenant=tenant, year_month=year_month).exists():
        raise ValueError(f"Snapshot already exists for {year_month}")

    # Compute distribution
    distribution = compute_fte_distribution(tenant, year_month)
    if not distribution:
        raise ValueError("No departments have linked cost centers or no data available")

    # Create snapshot
    snapshot = FteDistributionSnapshot.objects.create(
        tenant=tenant,
        year_month=year_month,
        captured_by=user,
    )

    # Create entries
    for entry_data in distribution:
        FteDistributionEntry.objects.create(
            snapshot=snapshot,
            department=entry_data["department"],
            department_name=entry_data["department"].name,
            cost_center=entry_data["cost_center"],
            cost_center_code=entry_data["cost_center"].code,
            fte_percentage=entry_data["fte_percentage"],
            monthly_income_total=entry_data["monthly_income_total"],
            hours_total=entry_data["hours_total"],
        )

    # Re-apply FTE-based splits for transactions in this month
    _reapply_fte_splits(tenant, year_month, snapshot)

    # Send notification if configured
    notification_email = (tenant.settings or {}).get("fte_snapshot_notification_email")
    if notification_email:
        _send_snapshot_notification(tenant, snapshot, notification_email)

    return snapshot


def _reapply_fte_splits(tenant, year_month: str, snapshot):
    """Re-apply FTE-based splits for all transactions in the given month."""
    from apps.banking.models import (
        BankTransaction,
        CostCenterSplitRule,
        TransactionCostCenterSplit,
    )

    year, month = int(year_month[:4]), int(year_month[5:7])
    last_day = calendar.monthrange(year, month)[1]
    date_from = date(year, month, 1)
    date_to = date(year, month, last_day)

    # Find FTE-based split rules for this tenant
    fte_rules = CostCenterSplitRule.objects.filter(
        tenant=tenant,
        mode=CostCenterSplitRule.Mode.FTE_DISTRIBUTION,
        is_active=True,
    )
    fte_rule_ids = set(fte_rules.values_list("id", flat=True))

    if not fte_rule_ids:
        return

    # Find transactions in this month that have auto-applied FTE splits
    splits_to_replace = TransactionCostCenterSplit.objects.filter(
        transaction__tenant=tenant,
        transaction__entry_date__gte=date_from,
        transaction__entry_date__lte=date_to,
        is_manual=False,
        rule_id__in=fte_rule_ids,
    ).select_related("transaction")

    # Group by transaction
    txn_ids = set(splits_to_replace.values_list("transaction_id", flat=True))

    # Get snapshot entries for computing new splits
    entries = list(snapshot.entries.select_related("cost_center").all())
    total_pct = sum(e.fte_percentage for e in entries)

    if total_pct == 0:
        return

    for txn_id in txn_ids:
        txn = BankTransaction.objects.get(id=txn_id)
        amount = abs(txn.amount)

        # Delete existing auto FTE splits for this transaction
        TransactionCostCenterSplit.objects.filter(
            transaction_id=txn_id,
            is_manual=False,
            rule_id__in=fte_rule_ids,
        ).delete()

        # Create new splits from snapshot
        rule = fte_rules.filter(counterparty=txn.counterparty).first() or fte_rules.first()
        remaining = amount
        sorted_entries = sorted(entries, key=lambda e: e.fte_percentage, reverse=True)

        for i, entry in enumerate(sorted_entries):
            if entry.cost_center is None:
                continue
            if i == len(sorted_entries) - 1:
                split_amount = remaining
            else:
                split_amount = (amount * entry.fte_percentage / total_pct).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                remaining -= split_amount

            if split_amount > 0:
                TransactionCostCenterSplit.objects.create(
                    transaction=txn,
                    cost_center=entry.cost_center,
                    amount=split_amount,
                    is_manual=False,
                    rule=rule,
                )


def _send_snapshot_notification(tenant, snapshot, email):
    """Send email notification about captured snapshot."""
    from apps.invoices.services.email_service import send_email

    entries = snapshot.entries.all()
    lines = [f"FTE Distribution Snapshot for {snapshot.year_month}\n"]
    lines.append(f"Captured at: {snapshot.captured_at.strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("Department | Cost Center | FTE % | Income | Hours")
    lines.append("-" * 60)
    for e in entries:
        lines.append(
            f"{e.department_name} | {e.cost_center_code} | "
            f"{e.fte_percentage}% | {e.monthly_income_total} | {e.hours_total}"
        )

    body = "\n".join(lines)
    subject = f"FTE Snapshot captured: {snapshot.year_month}"

    try:
        send_email(
            tenant=tenant,
            to_emails=[email],
            subject=subject,
            body=body,
        )
    except Exception:
        logger.exception("Failed to send FTE snapshot notification")
