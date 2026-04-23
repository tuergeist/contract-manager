"""Contract models."""
import os
import uuid
from decimal import Decimal

from django.db import models

from apps.core.models import RevenueType, TenantModel

# Re-export order confirmation models so they're discovered by Django
from apps.contracts.order_confirmation_models import (  # noqa: F401
    OrderConfirmation,
    OrderConfirmationNumberScheme,
)


class ContractGroup(TenantModel):
    """A group for organizing contracts within a customer."""

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="contract_groups",
    )
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        unique_together = ["customer", "name"]

    def __str__(self):
        return f"{self.name} ({self.customer.name})"


def attachment_upload_path(instance, filename):
    """
    Generate upload path: uploads/{tenant_id}/contracts/{contract_id}/{uuid}_{ext}

    This structure enables:
    - Per-tenant backup/restore
    - Per-contract file organization
    - Unique filenames to prevent collisions
    - Easy S3 migration (sync with same path structure)
    """
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return f"uploads/{instance.tenant_id}/contracts/{instance.contract_id}/{unique_filename}"


class Contract(TenantModel):
    """A contract with a customer."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        ENDED = "ended", "Ended"
        DELETED = "deleted", "Deleted"

    class BillingInterval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-annual"
        ANNUAL = "annual", "Annual"
        BIENNIAL = "biennial", "2 Years"
        TRIENNIAL = "triennial", "3 Years"
        QUADRENNIAL = "quadrennial", "4 Years"
        QUINQUENNIAL = "quinquennial", "5 Years"

    class NoticePeriodAnchor(models.TextChoices):
        END_OF_DURATION = "end_of_duration", "End of minimum duration"
        END_OF_MONTH = "end_of_month", "End of month"
        END_OF_QUARTER = "end_of_quarter", "End of quarter"

    hubspot_deal_id = models.CharField(max_length=100, blank=True, null=True)
    netsuite_sales_order_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Sales Order number from NetSuite (e.g., 'SO-VSX-25-039')",
    )
    netsuite_contract_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Contract number from NetSuite (e.g., '13634_2025-01-01_2025-12-31')",
    )
    netsuite_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Link to this contract in NetSuite",
    )
    po_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Purchase Order number",
    )
    order_confirmation_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Order Confirmation number (AB Nummer)",
    )
    name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(
        blank=True,
        help_text="Internal notes (not shown on invoices)",
    )
    invoice_text = models.TextField(
        blank=True,
        help_text="Optional text to show on invoices below line items",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="contracts",
    )
    group = models.ForeignKey(
        ContractGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )
    primary_contract = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="secondary_contracts",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    deal_won_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the deal was won (from HubSpot closedate for imported deals)",
    )
    billing_start_date = models.DateField()
    billing_interval = models.CharField(
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
    )
    billing_anchor_day = models.PositiveSmallIntegerField(default=1)
    billing_alignment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when billing aligns to regular cycle. First invoice covers period from billing_start_date to this date (pro-rated).",
    )
    min_duration_months = models.PositiveIntegerField(null=True, blank=True)
    notice_period_months = models.PositiveIntegerField(default=3)
    notice_period_anchor = models.CharField(
        max_length=20,
        choices=NoticePeriodAnchor.choices,
        default=NoticePeriodAnchor.END_OF_DURATION,
    )
    notice_period_after_min_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Notice period after minimum duration ends (if different from notice_period_months)",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_effective_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["tenant", "hubspot_deal_id"]

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.customer.name})"
        return f"Contract {self.id} - {self.customer.name}"

    @property
    def is_new_business(self) -> bool:
        """A contract is new business if it was imported from HubSpot."""
        return bool(self.hubspot_deal_id)

    @property
    def effective_status(self):
        """
        Get the effective status, accounting for end date.

        If contract is 'active' but end_date is in the past, return 'ended'.
        """
        from datetime import date as date_type

        if self.status == self.Status.ACTIVE and self.end_date:
            if self.end_date < date_type.today():
                return self.Status.ENDED
        return self.status

    def get_interval_months(self):
        """Return the billing interval in months."""
        return {
            self.BillingInterval.MONTHLY: 1,
            self.BillingInterval.QUARTERLY: 3,
            self.BillingInterval.SEMI_ANNUAL: 6,
            self.BillingInterval.ANNUAL: 12,
            self.BillingInterval.BIENNIAL: 24,
            self.BillingInterval.TRIENNIAL: 36,
            self.BillingInterval.QUADRENNIAL: 48,
            self.BillingInterval.QUINQUENNIAL: 60,
        }.get(self.billing_interval, 12)

    def get_min_end_date(self):
        """
        Calculate the minimum end date based on start_date + min_duration_months.
        Returns None if no minimum duration is set.
        """
        from dateutil.relativedelta import relativedelta

        if not self.min_duration_months:
            return None
        return self.start_date + relativedelta(months=self.min_duration_months)

    def get_earliest_cancellation_date(self, from_date=None):
        """
        Calculate the earliest possible cancellation date if notice is given on from_date.

        Args:
            from_date: Date when notice is given (default: today)

        Returns:
            The earliest date the contract could end based on notice period and anchor.
        """
        from datetime import date as date_type
        from dateutil.relativedelta import relativedelta
        from calendar import monthrange

        if from_date is None:
            from_date = date_type.today()

        min_end_date = self.get_min_end_date()
        is_past_min_duration = min_end_date is None or from_date >= min_end_date

        # Use appropriate notice period
        if is_past_min_duration and self.notice_period_after_min_months is not None:
            notice_months = self.notice_period_after_min_months
        else:
            notice_months = self.notice_period_months

        # Calculate date after notice period
        notice_end = from_date + relativedelta(months=notice_months)

        # Apply anchor
        if self.notice_period_anchor == self.NoticePeriodAnchor.END_OF_MONTH:
            # End of the month after notice period
            last_day = monthrange(notice_end.year, notice_end.month)[1]
            return date_type(notice_end.year, notice_end.month, last_day)

        elif self.notice_period_anchor == self.NoticePeriodAnchor.END_OF_QUARTER:
            # End of quarter after notice period
            quarter_end_month = ((notice_end.month - 1) // 3 + 1) * 3
            if quarter_end_month > 12:
                quarter_end_month = 12
            last_day = monthrange(notice_end.year, quarter_end_month)[1]
            return date_type(notice_end.year, quarter_end_month, last_day)

        else:  # END_OF_DURATION
            # If we're still in min duration, end at min_end_date
            if min_end_date and notice_end < min_end_date:
                return min_end_date
            return notice_end

    def get_effective_end_date(self):
        """
        Calculate the effective end date for total value calculation.

        - If end_date is set: use end_date
        - If indefinite: use min_end_date or earliest cancellation date (whichever is later)

        Returns:
            The effective end date for calculating contract total value.
        """
        from datetime import date as date_type

        # If contract has explicit end date, use it
        if self.end_date:
            return self.end_date

        # If contract was cancelled, use the cancellation effective date
        if self.cancellation_effective_date:
            return self.cancellation_effective_date

        today = date_type.today()
        min_end_date = self.get_min_end_date()

        # If we haven't reached min duration yet, use min_end_date
        if min_end_date and today < min_end_date:
            return min_end_date

        # After min duration: calculate earliest possible end date
        return self.get_earliest_cancellation_date(today)

    def get_duration_months(self):
        """
        Calculate the contract duration in months for total value calculation.

        Returns:
            Number of months from start_date to effective_end_date.
        """
        effective_end = self.get_effective_end_date()
        if not effective_end:
            # Fallback: if no end date and no min duration, use 12 months (1 year)
            return 12

        # Calculate months between dates
        months = (effective_end.year - self.start_date.year) * 12
        months += effective_end.month - self.start_date.month

        # Add 1 to include the end month (start of Jan to end of Dec = 12 months)
        # But only if end date is not the start of a month
        if effective_end.day > 1:
            months += 1

        return max(1, months)  # At least 1 month

    def get_billing_schedule(self, from_date=None, to_date=None, include_history=False, items=None, include_eta_items=False):
        """
        Calculate the billing schedule for all contract items.

        Args:
            from_date: Start of the forecast period (default: today)
            to_date: End of the forecast period (default: from_date + 13 months)
            include_history: Include past billing periods (default: False)

        Returns:
            List of dicts with:
            - date: billing date
            - items: list of items being billed with amounts
            - total: total amount for this billing date
        """
        from datetime import date as date_type
        from decimal import Decimal
        from collections import defaultdict
        from dateutil.relativedelta import relativedelta

        today = date_type.today()
        if from_date is None:
            from_date = today if not include_history else self.billing_start_date
        if to_date is None:
            to_date = today + relativedelta(months=13)

        # Don't go beyond contract end date
        if self.end_date and to_date > self.end_date:
            to_date = self.end_date

        # If end_date clipping made the range invalid, no events possible
        if from_date > to_date:
            return []

        interval_months = self.get_interval_months()
        events = defaultdict(lambda: {"items": [], "total": Decimal("0")})

        # Use pre-loaded items if provided, otherwise query from DB
        if items is None:
            items = self.items.select_related("product", "depends_on").prefetch_related("price_periods").all()

        for item in items:
            # Cache the prefetched price_periods as a list for in-memory lookups
            item_price_periods = list(item.price_periods.all())

            # Skip descriptive-only items (no product, no price, and no price periods)
            if not item.product and not item.unit_price and not item_price_periods:
                continue

            # Skip items with pending delivery (unless forecast mode with ETA,
            # or item is flagged as invoice_independent)
            if item.delivery_status == "pending" and not item.invoice_independent:
                if include_eta_items and item.estimated_delivery_date:
                    pass  # Include in forecast using ETA as projected billing date
                else:
                    continue

            # Skip items whose dependency is not yet delivered
            # (invoice_independent items bypass dependency blocking too)
            if (
                not item.invoice_independent
                and item.depends_on
                and item.depends_on.delivery_status == "pending"
            ):
                if include_eta_items and item.depends_on.estimated_delivery_date:
                    pass  # Include in forecast using dependency's ETA
                else:
                    continue

            # Determine item's billing period
            # For delivered one-off items without explicit billing_start, use delivered_at
            if item.is_one_off and item.delivery_status == "delivered" and item.delivered_at and not item.billing_start_date:
                item_billing_start = item.delivered_at
            elif (
                item.is_one_off
                and item.invoice_independent
                and item.delivery_status == "pending"
                and not item.billing_start_date
            ):
                # Upfront-invoiced pending one-off: prefer ETA, else skip to avoid
                # billing at a stale contract.billing_start_date.
                if item.estimated_delivery_date:
                    item_billing_start = item.estimated_delivery_date
                else:
                    continue
            else:
                item_billing_start = item.billing_start_date or self.billing_start_date
            # In forecast mode, use ETA as projected billing start for pending items
            if include_eta_items:
                if item.delivery_status == "pending" and not item.invoice_independent and item.estimated_delivery_date:
                    item_billing_start = item.estimated_delivery_date
                elif item.depends_on and item.depends_on.delivery_status == "pending" and item.depends_on.estimated_delivery_date:
                    item_billing_start = max(item_billing_start, item.depends_on.estimated_delivery_date)
            item_billing_end = item.billing_end_date  # Can be None = ongoing

            # Skip items that haven't started billing yet
            if item_billing_start > to_date:
                continue

            # Skip items that ended before our period
            if item_billing_end and item_billing_end < from_date:
                continue

            # Handle one-off items separately (billed only once)
            if item.is_one_off:
                self._add_one_off_billing_event(
                    events, item, item_billing_start, from_date, to_date, item_price_periods
                )
                continue

            # Calculate billing dates for this item
            # Use item-level alignment, or fall back to contract-level alignment
            align_date = item.align_to_contract_at or self.billing_alignment_date

            # When dependency ETA pushes start past alignment, find next cycle date as alignment
            if include_eta_items and item.depends_on and item.depends_on.delivery_status == "pending":
                next_cycle = align_date or self.billing_start_date
                while next_cycle < item_billing_start:
                    next_cycle += relativedelta(months=interval_months)
                if next_cycle > item_billing_start:
                    align_date = next_cycle

            # Use alignment if it's on or after the item's billing start
            if align_date and align_date >= item_billing_start:
                # Item has alignment - generate dates before and after alignment
                self._add_pre_alignment_events(
                    events, item, item_billing_start, align_date,
                    from_date, to_date, interval_months, item_price_periods
                )
                self._add_post_alignment_events(
                    events, item, align_date, item_billing_end,
                    from_date, to_date, interval_months, item_price_periods
                )
            else:
                # No alignment - item follows contract cycle from its start
                self._add_regular_billing_events(
                    events, item, item_billing_start, item_billing_end,
                    from_date, to_date, interval_months, item_price_periods
                )

        # Convert to sorted list
        result = []
        for billing_date in sorted(events.keys()):
            event = events[billing_date]
            result.append({
                "date": billing_date,
                "items": event["items"],
                "total": event["total"],
            })

        return result

    def _calc_end_prorate(self, billing_date, interval_months, item_end_date):
        """Calculate pro-rate factor when contract/item ends before next billing cycle.

        Returns (is_prorated, prorate_factor, billing_months) where billing_months
        is the number of months to bill for this event.
        """
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        next_billing = billing_date + relativedelta(months=interval_months)
        # Use the earlier of item end date and contract end date
        effective_end = item_end_date
        if self.end_date:
            if effective_end is None or self.end_date < effective_end:
                effective_end = self.end_date

        if effective_end and next_billing > effective_end:
            # Contract/item ends before the next billing cycle — pro-rate
            remaining = (
                (effective_end.year - billing_date.year) * 12 +
                (effective_end.month - billing_date.month)
            )
            # If end_date is not the 1st of its month, count that month as a full month
            if effective_end.day > 1:
                remaining += 1
            if remaining <= 0:
                return True, Decimal("0"), 0
            if remaining < interval_months:
                factor = Decimal(remaining) / Decimal(interval_months)
                return True, factor, remaining
        return False, None, interval_months

    def _add_regular_billing_events(
        self, events, item, start_date, end_date, from_date, to_date, interval_months,
        price_periods_list=None
    ):
        """Add billing events for an item following the regular contract cycle."""
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        # Find the first billing date on or after item start
        billing_date = self.billing_start_date
        while billing_date < start_date:
            billing_date += relativedelta(months=interval_months)

        # If the item starts mid-cycle, generate a pro-rated first event
        # e.g. annual contract Jan-Dec, item starts April → bill Apr-Dec pro-rated
        if billing_date > start_date and start_date >= from_date and start_date <= to_date:
            if end_date is None or start_date <= end_date:
                # Effective end of this stub period
                stub_end = min(billing_date, end_date) if end_date and end_date < billing_date else billing_date
                months_in_stub = (
                    (stub_end.year - start_date.year) * 12
                    + (stub_end.month - start_date.month)
                )
                if months_in_stub > 0:
                    prorate_factor = Decimal(months_in_stub) / Decimal(interval_months)
                    if price_periods_list is not None:
                        price_at_date = item.get_price_at_cached(start_date, price_periods_list)
                    else:
                        price_at_date = item.get_price_at(start_date)
                    amount = (item.quantity * price_at_date * interval_months * prorate_factor).quantize(Decimal("0.01"))
                    events[start_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name if item.product else (item.description or "Discount"),
                        "description": item.description if item.product else "",
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": True,
                        "prorate_factor": prorate_factor.quantize(Decimal("0.0001")),
                    })
                    events[start_date]["total"] += amount

        # Generate billing events
        while billing_date <= to_date:
            if billing_date >= from_date:
                if end_date is None or billing_date <= end_date:
                    # Check if this is the last period and needs pro-rating
                    is_prorated, prorate_factor, billing_months = self._calc_end_prorate(
                        billing_date, interval_months, end_date
                    )
                    if billing_months <= 0:
                        billing_date += relativedelta(months=interval_months)
                        continue

                    # Use cached price lookup if price_periods provided, else fallback
                    if price_periods_list is not None:
                        price_at_date = item.get_price_at_cached(billing_date, price_periods_list)
                    else:
                        price_at_date = item.get_price_at(billing_date)
                    # unit_price is monthly, multiply by billing months
                    if is_prorated:
                        amount = (item.quantity * price_at_date * interval_months * prorate_factor).quantize(Decimal("0.01"))
                    else:
                        amount = item.quantity * price_at_date * interval_months
                    events[billing_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name if item.product else (item.description or "Discount"),
                        "description": item.description if item.product else "",
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": is_prorated,
                        "prorate_factor": prorate_factor.quantize(Decimal("0.0001")) if prorate_factor else None,
                    })
                    events[billing_date]["total"] += amount
            billing_date += relativedelta(months=interval_months)

    def _add_pre_alignment_events(
        self, events, item, start_date, align_date, from_date, to_date, interval_months,
        price_periods_list=None
    ):
        """Add billing events before alignment (pro-rated first period)."""
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        # First billing is at start_date (pro-rated period until align_date)
        # Skip if start_date equals align_date (no pre-alignment period)
        if start_date >= from_date and start_date <= to_date and start_date < align_date:
            # Calculate proration factor using months
            # Count full months between start_date and align_date
            months_in_period = (
                (align_date.year - start_date.year) * 12 +
                (align_date.month - start_date.month)
            )
            # If align_date.day < start_date.day, we have a partial month less
            # But for billing alignment, we typically bill for whole months
            prorate_factor = Decimal(months_in_period) / Decimal(interval_months)

            # Use cached price lookup if price_periods provided, else fallback
            if price_periods_list is not None:
                price_at_date = item.get_price_at_cached(start_date, price_periods_list)
            else:
                price_at_date = item.get_price_at(start_date)
            # unit_price is monthly, multiply by interval for billing amount
            amount = item.quantity * price_at_date * interval_months * prorate_factor
            events[start_date]["items"].append({
                "item_id": item.id,
                "product_name": item.product.name if item.product else (item.description or "Discount"),
                "description": item.description if item.product else "",
                "quantity": item.quantity,
                "unit_price": price_at_date,
                "amount": amount.quantize(Decimal("0.01")),
                "is_prorated": True,
                "prorate_factor": prorate_factor.quantize(Decimal("0.0001")),
            })
            events[start_date]["total"] += amount.quantize(Decimal("0.01"))

    def _add_post_alignment_events(
        self, events, item, align_date, end_date, from_date, to_date, interval_months,
        price_periods_list=None
    ):
        """Add billing events after alignment (synced to contract's billing cycle)."""
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        # After alignment, billing starts from the alignment date
        billing_date = align_date

        while billing_date <= to_date:
            if billing_date >= from_date:
                if end_date is None or billing_date <= end_date:
                    # Check if this is the last period and needs pro-rating
                    is_prorated, prorate_factor, billing_months = self._calc_end_prorate(
                        billing_date, interval_months, end_date
                    )
                    if billing_months <= 0:
                        billing_date += relativedelta(months=interval_months)
                        continue

                    # Use cached price lookup if price_periods provided, else fallback
                    if price_periods_list is not None:
                        price_at_date = item.get_price_at_cached(billing_date, price_periods_list)
                    else:
                        price_at_date = item.get_price_at(billing_date)
                    # unit_price is monthly, multiply by billing months
                    if is_prorated:
                        amount = (item.quantity * price_at_date * interval_months * prorate_factor).quantize(Decimal("0.01"))
                    else:
                        amount = item.quantity * price_at_date * interval_months
                    events[billing_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name if item.product else (item.description or "Discount"),
                        "description": item.description if item.product else "",
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": is_prorated,
                        "prorate_factor": prorate_factor.quantize(Decimal("0.0001")) if prorate_factor else None,
                    })
                    events[billing_date]["total"] += amount
            billing_date += relativedelta(months=interval_months)

    def _add_one_off_billing_event(
        self, events, item, billing_start, from_date, to_date, price_periods_list=None
    ):
        """Add a single billing event for a one-off item."""
        from decimal import Decimal

        # One-off items are billed once at their billing start date
        billing_date = billing_start

        # Only include if within our date range
        if billing_date >= from_date and billing_date <= to_date:
            # One-off items use the full price, not monthly-normalized
            if price_periods_list is not None:
                price_at_date = item.get_price_at_cached(billing_date, price_periods_list, normalize_to_monthly=False)
            else:
                price_at_date = item.get_price_at(billing_date, normalize_to_monthly=False)
            amount = item.quantity * price_at_date
            events[billing_date]["items"].append({
                "item_id": item.id,
                "product_name": item.product.name if item.product else (item.description or "Discount"),
                "description": item.description if item.product else "",
                "quantity": item.quantity,
                "unit_price": price_at_date,
                "amount": amount,
                "is_prorated": False,
                "prorate_factor": None,
                "is_one_off": True,
            })
            events[billing_date]["total"] += amount

    def get_recognition_schedule(self, from_date=None, to_date=None, include_history=False, items=None, include_eta_items=False):
        """
        Calculate the recognition schedule for all contract items.

        This is similar to get_billing_schedule but uses item.start_date (recognition date)
        instead of item.billing_start_date for timing. Falls back to billing_start_date
        if start_date is null.

        Args:
            from_date: Start of the forecast period (default: today)
            to_date: End of the forecast period (default: from_date + 13 months)
            include_history: Include past recognition periods (default: False)
            items: Pre-loaded items queryset (default: None, queries DB)

        Returns:
            List of dicts with:
            - date: recognition date
            - items: list of items being recognized with amounts
            - total: total amount for this recognition date
        """
        from datetime import date as date_type
        from decimal import Decimal
        from collections import defaultdict
        from dateutil.relativedelta import relativedelta

        today = date_type.today()
        if from_date is None:
            from_date = today if not include_history else self.billing_start_date
        if to_date is None:
            to_date = today + relativedelta(months=13)

        # Don't go beyond contract end date
        if self.end_date and to_date > self.end_date:
            to_date = self.end_date

        # If end_date clipping made the range invalid, no events possible
        if from_date > to_date:
            return []

        interval_months = self.get_interval_months()
        events = defaultdict(lambda: {"items": [], "total": Decimal("0")})

        # Use pre-loaded items if provided, otherwise query from DB
        if items is None:
            items = self.items.select_related("product", "depends_on").prefetch_related("price_periods").all()

        for item in items:
            # Cache the prefetched price_periods as a list for in-memory lookups
            item_price_periods = list(item.price_periods.all())

            # Skip descriptive-only items (no product, no price, and no price periods)
            if not item.product and not item.unit_price and not item_price_periods:
                continue

            # Skip items with pending delivery (unless forecast mode with ETA,
            # or item is flagged as invoice_independent)
            if item.delivery_status == "pending" and not item.invoice_independent:
                if include_eta_items and item.estimated_delivery_date:
                    pass  # Include in forecast using ETA
                else:
                    continue

            # Skip items whose dependency is not yet delivered
            # (invoice_independent items bypass dependency blocking too)
            if (
                not item.invoice_independent
                and item.depends_on
                and item.depends_on.delivery_status == "pending"
            ):
                if include_eta_items and item.depends_on.estimated_delivery_date:
                    pass  # Include in forecast using dependency's ETA
                else:
                    continue

            # For upfront-invoiced pending one-off items with no dates, prefer ETA
            # to avoid recognizing revenue at a stale contract start date.
            if (
                item.is_one_off
                and item.invoice_independent
                and item.delivery_status == "pending"
                and not item.start_date
                and not item.billing_start_date
            ):
                if item.estimated_delivery_date:
                    item_recognition_start = item.estimated_delivery_date
                else:
                    continue
            else:
                # Use start_date for recognition, fall back to billing_start_date
                item_recognition_start = item.start_date or item.billing_start_date or self.billing_start_date
            # In forecast mode, use ETA as projected recognition start for pending items
            if include_eta_items:
                if item.delivery_status == "pending" and not item.invoice_independent and item.estimated_delivery_date:
                    item_recognition_start = item.estimated_delivery_date
                elif item.depends_on and item.depends_on.delivery_status == "pending" and item.depends_on.estimated_delivery_date:
                    item_recognition_start = max(item_recognition_start, item.depends_on.estimated_delivery_date)
            item_billing_end = item.billing_end_date  # Can be None = ongoing

            # Skip items that haven't started yet
            if item_recognition_start > to_date:
                continue

            # Skip items that ended before our period
            if item_billing_end and item_billing_end < from_date:
                continue

            # Handle one-off items separately (recognized only once)
            if item.is_one_off:
                self._add_one_off_recognition_event(
                    events, item, item_recognition_start, from_date, to_date, item_price_periods
                )
                continue

            # Calculate recognition dates for this item
            # Use item-level alignment, or fall back to contract-level alignment
            align_date = item.align_to_contract_at or self.billing_alignment_date

            # When dependency ETA pushes start past alignment, find next cycle date as alignment
            if include_eta_items and item.depends_on and item.depends_on.delivery_status == "pending":
                next_cycle = align_date or self.billing_start_date
                while next_cycle < item_recognition_start:
                    next_cycle += relativedelta(months=interval_months)
                if next_cycle > item_recognition_start:
                    align_date = next_cycle

            # Use alignment if it's on or after the item's recognition start
            if align_date and align_date >= item_recognition_start:
                # Item has alignment - generate dates before and after alignment
                self._add_pre_alignment_recognition_events(
                    events, item, item_recognition_start, align_date,
                    from_date, to_date, interval_months, item_price_periods
                )
                self._add_post_alignment_recognition_events(
                    events, item, align_date, item_billing_end,
                    from_date, to_date, interval_months, item_price_periods
                )
            else:
                # No alignment - item follows contract cycle from its recognition start
                self._add_regular_recognition_events(
                    events, item, item_recognition_start, item_billing_end,
                    from_date, to_date, interval_months, item_price_periods
                )

        # Convert to sorted list
        result = []
        for recognition_date in sorted(events.keys()):
            event = events[recognition_date]
            result.append({
                "date": recognition_date,
                "items": event["items"],
                "total": event["total"],
            })

        return result

    def _add_regular_recognition_events(
        self, events, item, start_date, end_date, from_date, to_date, interval_months,
        price_periods_list=None
    ):
        """Add recognition events for an item following the regular contract cycle.

        For multi-year intervals (>12 months), revenue is recognized annually
        (every 12 months) rather than at the billing interval.
        """
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        # Recognition interval: annual for multi-year contracts
        recognition_interval = min(interval_months, 12)

        # Find the first recognition date on or after item start
        recognition_date = self.billing_start_date
        while recognition_date < start_date:
            recognition_date += relativedelta(months=recognition_interval)

        # Generate recognition events
        while recognition_date <= to_date:
            if recognition_date >= from_date:
                if end_date is None or recognition_date <= end_date:
                    # Use cached price lookup if price_periods provided, else fallback
                    if price_periods_list is not None:
                        price_at_date = item.get_price_at_cached(recognition_date, price_periods_list)
                    else:
                        price_at_date = item.get_price_at(recognition_date)
                    # unit_price is monthly, multiply by recognition interval (max 12)
                    amount = item.quantity * price_at_date * recognition_interval
                    events[recognition_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name if item.product else (item.description or "Discount"),
                        "description": item.description if item.product else "",
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": False,
                        "prorate_factor": None,
                    })
                    events[recognition_date]["total"] += amount
            recognition_date += relativedelta(months=recognition_interval)

    def _add_pre_alignment_recognition_events(
        self, events, item, start_date, align_date, from_date, to_date, interval_months,
        price_periods_list=None
    ):
        """Add recognition events before alignment (pro-rated first period).

        For multi-year intervals, recognition is capped at annual amounts.
        """
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        recognition_interval = min(interval_months, 12)

        if start_date >= from_date and start_date <= to_date and start_date < align_date:
            months_in_period = (
                (align_date.year - start_date.year) * 12 +
                (align_date.month - start_date.month)
            )
            prorate_factor = Decimal(min(months_in_period, recognition_interval)) / Decimal(recognition_interval)

            if price_periods_list is not None:
                price_at_date = item.get_price_at_cached(start_date, price_periods_list)
            else:
                price_at_date = item.get_price_at(start_date)
            amount = item.quantity * price_at_date * recognition_interval * prorate_factor
            events[start_date]["items"].append({
                "item_id": item.id,
                "product_name": item.product.name if item.product else (item.description or "Discount"),
                "description": item.description if item.product else "",
                "quantity": item.quantity,
                "unit_price": price_at_date,
                "amount": amount.quantize(Decimal("0.01")),
                "is_prorated": True,
                "prorate_factor": prorate_factor.quantize(Decimal("0.0001")),
            })
            events[start_date]["total"] += amount.quantize(Decimal("0.01"))

    def _add_post_alignment_recognition_events(
        self, events, item, align_date, end_date, from_date, to_date, interval_months,
        price_periods_list=None
    ):
        """Add recognition events after alignment (synced to contract's billing cycle).

        For multi-year intervals, revenue is recognized annually.
        """
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        recognition_interval = min(interval_months, 12)
        recognition_date = align_date

        while recognition_date <= to_date:
            if recognition_date >= from_date:
                if end_date is None or recognition_date <= end_date:
                    if price_periods_list is not None:
                        price_at_date = item.get_price_at_cached(recognition_date, price_periods_list)
                    else:
                        price_at_date = item.get_price_at(recognition_date)
                    amount = item.quantity * price_at_date * recognition_interval
                    events[recognition_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name if item.product else (item.description or "Discount"),
                        "description": item.description if item.product else "",
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": False,
                        "prorate_factor": None,
                    })
                    events[recognition_date]["total"] += amount
            recognition_date += relativedelta(months=recognition_interval)

    def _add_one_off_recognition_event(
        self, events, item, recognition_start, from_date, to_date, price_periods_list=None
    ):
        """Add a single recognition event for a one-off item."""
        from decimal import Decimal

        # One-off items are recognized once at their recognition start date
        recognition_date = recognition_start

        # Only include if within our date range
        if recognition_date >= from_date and recognition_date <= to_date:
            # One-off items use the full price, not monthly-normalized
            if price_periods_list is not None:
                price_at_date = item.get_price_at_cached(recognition_date, price_periods_list, normalize_to_monthly=False)
            else:
                price_at_date = item.get_price_at(recognition_date, normalize_to_monthly=False)
            amount = item.quantity * price_at_date
            events[recognition_date]["items"].append({
                "item_id": item.id,
                "product_name": item.product.name if item.product else (item.description or "Discount"),
                "description": item.description if item.product else "",
                "quantity": item.quantity,
                "unit_price": price_at_date,
                "amount": amount,
                "is_prorated": False,
                "prorate_factor": None,
                "is_one_off": True,
            })
            events[recognition_date]["total"] += amount


class ContractItem(TenantModel):
    """A line item in a contract."""

    class PriceSource(models.TextChoices):
        LIST = "list", "From price list"
        CUSTOM = "custom", "Custom price"
        CUSTOMER_AGREEMENT = "customer_agreement", "Customer agreement"

    class PricePeriod(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        BI_MONTHLY = "bi_monthly", "2 Months"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-annual"
        ANNUAL = "annual", "Annual"
        BIENNIAL = "biennial", "2 Years"
        TRIENNIAL = "triennial", "3 Years"
        QUADRENNIAL = "quadrennial", "4 Years"
        QUINQUENNIAL = "quinquennial", "5 Years"

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="contract_items",
        null=True,
        blank=True,
        help_text="Optional for descriptive-only line items",
    )
    description = models.TextField(
        blank=True,
        help_text="Additional description or notes for this line item",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_period = models.CharField(
        max_length=20,
        choices=PricePeriod.choices,
        default=PricePeriod.MONTHLY,
        help_text="The period this price refers to (e.g., monthly, quarterly, annual)",
    )
    price_source = models.CharField(
        max_length=20,
        choices=PriceSource.choices,
        default=PriceSource.LIST,
    )
    # When this item becomes effective (can differ from contract start)
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this item becomes effective. Defaults to today if not set.",
    )
    # Billing period for this item (can differ from contract)
    billing_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When billing starts for this item. Defaults to contract billing start.",
    )
    billing_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When billing ends for this item. Null = ongoing.",
    )
    align_to_contract_at = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this item aligns to contract billing cycle. First period is pro-rated.",
    )
    is_one_off = models.BooleanField(
        default=False,
        help_text="If True, this item is billed only once (not recurring).",
    )
    revenue_type = models.CharField(
        max_length=30,
        choices=RevenueType.choices,
        null=True,
        blank=True,
        help_text="Revenue stream override. If null, inherits from product.",
    )
    order_confirmation_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Order Confirmation number (AB Nummer) for this item",
    )
    price_locked = models.BooleanField(
        default=False,
        help_text="If True, price cannot be changed until price_locked_until.",
    )
    price_locked_until = models.DateField(
        null=True,
        blank=True,
        help_text="Date until price is locked. After this date, price_locked becomes False.",
    )
    sort_order = models.IntegerField(
        null=True,
        blank=True,
        help_text="Sort order within the contract (per recurring/one-off group)",
    )
    added_by_amendment = models.ForeignKey(
        "ContractAmendment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_items",
    )
    delivery_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[("pending", "Pending"), ("delivered", "Delivered")],
        help_text="Delivery tracking: NULL = no tracking, pending = awaiting delivery, delivered = completed.",
    )
    delivered_at = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this item was delivered.",
    )
    estimated_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Estimated delivery date for pending deliverable items. Used for revenue forecasting.",
    )
    invoice_independent = models.BooleanField(
        default=False,
        help_text="If True, this item is billed regardless of delivery status (e.g. upfront payment). Delivery tracking is kept for documentation only.",
    )
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependent_items",
        help_text="Item that must be delivered before this one can be billed.",
    )
    source_hubspot_deal_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="HubSpot deal ID from source contract when item was transferred via merge.",
    )
    deal_won_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date this specific item was won/booked. Used for new bookings reporting when different from contract deal_won_date.",
    )
    moved_to = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moved_from",
    )

    class Meta:
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        if self.product:
            return f"{self.product.name} x{self.quantity}"
        return self.description[:50] if self.description else f"Item {self.id}"

    def get_effective_revenue_type(self) -> str | None:
        """Resolve revenue type: explicit override → product → one-off default → None."""
        if self.revenue_type:
            return self.revenue_type
        if self.product and self.product.revenue_type:
            return self.product.revenue_type
        if self.is_one_off:
            return "advanced_development"
        return None

    @property
    def total_price(self):
        """Get total price normalized to monthly (quantity × monthly_unit_price)."""
        return self.quantity * self.monthly_unit_price

    @property
    def total_price_raw(self):
        """Get raw total price without normalization (quantity × unit_price)."""
        return self.quantity * self.unit_price

    @staticmethod
    def get_period_months(period: str) -> int:
        """Convert a price period to number of months."""
        return {
            "monthly": 1,
            "bi_monthly": 2,
            "quarterly": 3,
            "semi_annual": 6,
            "annual": 12,
            "biennial": 24,
            "triennial": 36,
            "quadrennial": 48,
            "quinquennial": 60,
        }.get(period, 1)

    @property
    def price_period_months(self) -> int:
        """Get the number of months for this item's price period."""
        return self.get_period_months(self.price_period)

    @property
    def monthly_unit_price(self):
        """Get the unit price normalized to monthly."""
        from decimal import Decimal
        return self.unit_price / Decimal(self.price_period_months)

    def get_price_at(self, target_date, normalize_to_monthly: bool = True):
        """
        Get the price for this item at a specific date.

        Looks up price from ContractItemPrice records if any exist.
        Falls back to unit_price if no price_periods defined.
        This ensures backward compatibility for existing contracts.

        Args:
            target_date: The date for which to get the price
            normalize_to_monthly: If True, returns the monthly equivalent price

        Returns:
            Decimal: The unit price at the given date (monthly if normalized)
        """
        from decimal import Decimal

        # Check for a price period that covers this date
        price_period_record = self.price_periods.filter(
            valid_from__lte=target_date,
        ).filter(
            models.Q(valid_to__gte=target_date) | models.Q(valid_to__isnull=True)
        ).order_by("-valid_from").first()

        if price_period_record:
            price = price_period_record.unit_price
            period = price_period_record.price_period
        else:
            # FALLBACK: Use the item's unit_price and price_period
            price = self.unit_price
            period = self.price_period

        if normalize_to_monthly:
            period_months = self.get_period_months(period)
            return price / Decimal(period_months)

        return price

    def get_price_at_cached(self, target_date, price_periods_list, normalize_to_monthly: bool = True):
        """
        Get the price for this item at a specific date using pre-loaded price_periods.

        This method avoids N+1 queries by accepting a pre-fetched list of price periods
        instead of querying the database. Use this in batch operations where items
        and their price_periods have been prefetched.

        Args:
            target_date: The date for which to get the price
            price_periods_list: List of ContractItemPrice objects (pre-fetched)
            normalize_to_monthly: If True, returns the monthly equivalent price

        Returns:
            Decimal: The unit price at the given date (monthly if normalized)
        """
        from decimal import Decimal

        # Find matching price period from in-memory list
        matching = None
        for pp in price_periods_list:
            if pp.valid_from <= target_date:
                if pp.valid_to is None or pp.valid_to >= target_date:
                    if matching is None or pp.valid_from > matching.valid_from:
                        matching = pp

        if matching:
            price = matching.unit_price
            period = matching.price_period
        else:
            # FALLBACK: Use the item's unit_price and price_period
            price = self.unit_price
            period = self.price_period

        if normalize_to_monthly:
            period_months = self.get_period_months(period)
            return price / Decimal(period_months)

        return price

    def get_effective_price_info(self, target_date):
        """
        Get the effective price and period for this item at a specific date.

        Returns the price and its period without normalization.
        Uses period-specific pricing if available, otherwise falls back to base price.

        Args:
            target_date: The date for which to get the price info

        Returns:
            tuple: (price: Decimal, period: str) - The effective price and its period
        """
        # Check for a price period that covers this date
        price_period_record = self.price_periods.filter(
            valid_from__lte=target_date,
        ).filter(
            models.Q(valid_to__gte=target_date) | models.Q(valid_to__isnull=True)
        ).order_by("-valid_from").first()

        if price_period_record:
            return price_period_record.unit_price, price_period_record.price_period

        # FALLBACK: Use the item's unit_price and price_period
        return self.unit_price, self.price_period

    def get_suggested_alignment_date(self, from_date=None):
        """
        Calculate suggested alignment date based on contract billing cycle.

        Example: Item added 4.5.26, contract bills annually from 1.1.
        -> Suggests 1.1.27 as alignment date.
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta

        if from_date is None:
            from_date = self.billing_start_date or date.today()

        contract = self.contract
        anchor_day = contract.billing_anchor_day

        # Calculate interval in months
        interval_months = {
            Contract.BillingInterval.MONTHLY: 1,
            Contract.BillingInterval.QUARTERLY: 3,
            Contract.BillingInterval.SEMI_ANNUAL: 6,
            Contract.BillingInterval.ANNUAL: 12,
            Contract.BillingInterval.BIENNIAL: 24,
            Contract.BillingInterval.TRIENNIAL: 36,
            Contract.BillingInterval.QUADRENNIAL: 48,
            Contract.BillingInterval.QUINQUENNIAL: 60,
        }.get(contract.billing_interval, 12)

        # Find next billing cycle start after from_date
        # Start from contract billing start and step forward
        cycle_start = contract.billing_start_date
        while cycle_start <= from_date:
            cycle_start += relativedelta(months=interval_months)

        return cycle_start


class ContractAmendment(TenantModel):
    """An amendment/change to a contract."""

    class AmendmentType(models.TextChoices):
        PRODUCT_ADDED = "product_added", "Product added"
        PRODUCT_REMOVED = "product_removed", "Product removed"
        QUANTITY_CHANGED = "quantity_changed", "Quantity changed"
        PRICE_CHANGED = "price_changed", "Price changed"
        TERMS_CHANGED = "terms_changed", "Terms changed"

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="amendments",
    )
    effective_date = models.DateField()
    type = models.CharField(
        max_length=20,
        choices=AmendmentType.choices,
    )
    description = models.TextField(blank=True)
    changes = models.JSONField(default=dict)
    arr_delta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annualized revenue delta caused by this amendment",
    )

    class Meta:
        ordering = ["-effective_date"]

    def __str__(self):
        return f"Amendment {self.id} - {self.get_type_display()}"


def calculate_arr_value(unit_price, quantity, price_period, is_one_off):
    """Calculate annualized recurring revenue for a contract item."""
    if is_one_off:
        return Decimal("0")
    multipliers = {
        "monthly": 12,
        "quarterly": 4,
        "semi_annual": 2,
        "annual": 1,
        "biennial": Decimal("0.5"),
        "triennial": Decimal("1") / 3,
        "quadrennial": Decimal("0.25"),
        "quinquennial": Decimal("0.2"),
    }
    period = price_period or "monthly"
    return Decimal(str(unit_price)) * Decimal(str(quantity)) * multipliers.get(period, 12)


class ContractItemPrice(TenantModel):
    """Price for a contract item during a specific period.

    Enables year-specific pricing for contracts.
    Example: Year 1: €100/month, Year 2: €120/month, Year 3+: list price.
    """

    class PriceSource(models.TextChoices):
        FIXED = "fixed", "Fixed Agreement"
        LIST = "list", "List Price"
        NEGOTIATED = "negotiated", "To Be Negotiated"

    class IncreaseType(models.TextChoices):
        INFLATION = "inflation", "Inflation"
        NEGOTIATED = "negotiated", "Negotiated"

    # Reuse PricePeriod from ContractItem
    PricePeriod = ContractItem.PricePeriod

    item = models.ForeignKey(
        ContractItem,
        on_delete=models.CASCADE,
        related_name="price_periods",
    )
    valid_from = models.DateField(
        help_text="Start date for this price period",
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="End date for this price period. Null = ongoing.",
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Unit price during this period",
    )
    price_period = models.CharField(
        max_length=20,
        choices=ContractItem.PricePeriod.choices,
        default=ContractItem.PricePeriod.MONTHLY,
        help_text="The period this price refers to (e.g., monthly, quarterly, annual)",
    )
    source = models.CharField(
        max_length=20,
        choices=PriceSource.choices,
        default=PriceSource.FIXED,
    )
    increase_type = models.CharField(
        max_length=20,
        choices=IncreaseType.choices,
        null=True,
        blank=True,
        help_text="Reason for price change (inflation or negotiated)",
    )

    class Meta:
        ordering = ["valid_from"]

    def __str__(self):
        item_name = self.item.product.name if self.item.product else (self.item.description or f"Item #{self.item_id}")
        if self.valid_to:
            return f"{item_name}: €{self.unit_price} ({self.valid_from} - {self.valid_to})"
        return f"{item_name}: €{self.unit_price} (from {self.valid_from})"


class ContractAttachment(TenantModel):
    """A file attachment for a contract."""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to=attachment_upload_path)
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by user",
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes",
    )
    content_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file",
    )
    uploaded_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_attachments",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the attachment",
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Document category: order, contract, offer, other",
    )
    extracted_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Cached AI extraction result (line items + metadata). Persisted to avoid repeated API calls.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.contract})"

    def delete(self, *args, **kwargs):
        """Delete the file from storage when the model is deleted."""
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)


class AutoLinkRule(TenantModel):
    """Pattern-based rule for auto-linking time tracking projects to a contract."""

    class MatchType(models.TextChoices):
        CONTAINS = "contains", "Contains"
        STARTS_WITH = "starts_with", "Starts with"

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="auto_link_rules",
    )
    contract_item = models.ForeignKey(
        ContractItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_link_rules",
    )
    pattern = models.CharField(max_length=255)
    match_type = models.CharField(
        max_length=20,
        choices=MatchType.choices,
        default=MatchType.CONTAINS,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_match_type_display()} '{self.pattern}' -> {self.contract}"


class TimeTrackingProjectMapping(TenantModel):
    """Maps an external time tracking project to a contract."""

    class LinkSource(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTO = "auto", "Auto"

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="time_tracking_mappings",
    )
    contract_item = models.ForeignKey(
        ContractItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_tracking_mappings",
    )
    external_project_id = models.CharField(max_length=100)
    external_project_name = models.CharField(max_length=255)
    external_customer_name = models.CharField(max_length=255, blank=True, default="")
    link_source = models.CharField(
        max_length=10,
        choices=LinkSource.choices,
        default=LinkSource.MANUAL,
    )
    auto_link_rule = models.ForeignKey(
        AutoLinkRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mappings",
    )

    # Cached time tracking data (refreshed by Celery Beat)
    cached_total_hours = models.FloatField(default=0)
    cached_total_revenue = models.FloatField(default=0)
    cached_by_service = models.JSONField(default=list)  # [{service_name, hours, revenue}]
    cached_by_month = models.JSONField(default=list)  # [{month, hours, revenue}]
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["external_customer_name", "external_project_name"]
        unique_together = ["tenant", "external_project_id"]

    def __str__(self):
        return f"{self.external_project_name} -> {self.contract}"


class ContractLink(TenantModel):
    """A named link attached to a contract."""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="links",
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name for the link",
    )
    url = models.URLField(
        max_length=2000,
        help_text="URL of the link",
    )
    created_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_contract_links",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.contract})"


class RevenueGoal(TenantModel):
    """Yearly revenue target per revenue stream."""

    year = models.IntegerField()
    revenue_type = models.CharField(
        max_length=30,
        choices=RevenueType.choices,
    )
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ["tenant", "year", "revenue_type"]
        ordering = ["year", "revenue_type"]

    def __str__(self):
        return f"{self.year} {self.get_revenue_type_display()}: {self.target_amount}"


class NewBusinessGoalType(models.TextChoices):
    NEW_ARR = "new_arr", "Won New ARR"
    BACK_TO_BASE_ARR = "back_to_base_arr", "Back-to-Base ARR"
    NEW_DEVELOPMENT = "new_development", "Won Development Revenue"
    NEW_DEAL_COUNT = "new_deal_count", "Won Deal Count"


class NewBusinessGoal(TenantModel):
    """Yearly target for new business metrics (won deals)."""

    year = models.IntegerField()
    goal_type = models.CharField(
        max_length=30,
        choices=NewBusinessGoalType.choices,
    )
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ["tenant", "year", "goal_type"]
        ordering = ["year", "goal_type"]

    def __str__(self):
        return f"{self.year} {self.get_goal_type_display()}: {self.target_amount}"


class ContractComment(TenantModel):
    """A comment on a contract."""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField()
    author = models.ForeignKey(
        "tenants.User",
        on_delete=models.CASCADE,
        related_name="contract_comments",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.contract}"


class Department(TenantModel):
    """A department for grouping time tracking services."""

    name = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    cost_center = models.ForeignKey(
        "banking.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departments",
    )

    class Meta:
        unique_together = ["tenant", "name"]
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class DepartmentServiceMapping(TenantModel):
    """Maps an external time tracking service to a department."""

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="service_mappings",
    )
    external_service_id = models.CharField(max_length=50)
    external_service_name = models.CharField(max_length=255)

    class Meta:
        unique_together = ["tenant", "external_service_id"]

    def __str__(self):
        return f"{self.external_service_name} → {self.department.name}"


class UserCostProfile(TenantModel):
    """Per-user cost profile for department cost analysis."""

    external_user_id = models.CharField(max_length=50)
    external_user_name = models.CharField(max_length=255)
    fte_percentage = models.IntegerField(default=100)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    default_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cost_profiles",
    )

    class Meta:
        unique_together = ["tenant", "external_user_id"]

    def __str__(self):
        return f"{self.external_user_name} (FTE {self.fte_percentage}%)"


class AbsenceReport(TenantModel):
    """Monthly absence report snapshot."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"

    class AbsenceType(models.TextChoices):
        SICK = "sick", "Sick"
        SICK_CHILD = "sick_child", "Sick (child)"
        SICK_CERTIFICATE = "sick_certificate", "Sick (with certificate)"
        VACATION = "vacation", "Vacation"
        SPECIAL_LEAVE = "special_leave", "Special leave"
        EDUCATION = "education", "Education/Training"
        OVERTIME_REDUCTION = "overtime_reduction", "Overtime reduction"
        OTHER = "other", "Other"

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_absence_reports",
    )
    pdf_file = models.FileField(
        upload_to="absence_reports/",
        blank=True,
    )

    class Meta:
        unique_together = ["tenant", "year", "month"]
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"Absence Report {self.year}-{self.month:02d} ({self.get_status_display()})"


class AbsenceReportEntry(TenantModel):
    """Individual absence entry within a report."""

    report = models.ForeignKey(
        AbsenceReport,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    user_name = models.CharField(max_length=255)
    external_user_id = models.CharField(max_length=100)
    absence_type = models.CharField(
        max_length=30,
        choices=AbsenceReport.AbsenceType.choices,
    )
    date_from = models.DateField()
    date_to = models.DateField()
    days_count = models.DecimalField(max_digits=5, decimal_places=2)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["user_name", "date_from"]

    def __str__(self):
        return f"{self.user_name}: {self.get_absence_type_display()} ({self.date_from} - {self.date_to})"
