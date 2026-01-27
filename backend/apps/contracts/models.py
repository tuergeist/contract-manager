"""Contract models."""
from django.db import models

from apps.core.models import TenantModel


class Contract(TenantModel):
    """A contract with a customer."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        ENDED = "ended", "Ended"

    class BillingInterval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-annual"
        ANNUAL = "annual", "Annual"

    class NoticePeriodAnchor(models.TextChoices):
        END_OF_DURATION = "end_of_duration", "End of minimum duration"
        END_OF_MONTH = "end_of_month", "End of month"
        END_OF_QUARTER = "end_of_quarter", "End of quarter"

    hubspot_deal_id = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
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
    billing_start_date = models.DateField()
    billing_interval = models.CharField(
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
    )
    billing_anchor_day = models.PositiveSmallIntegerField(default=1)
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

    def get_interval_months(self):
        """Return the billing interval in months."""
        return {
            self.BillingInterval.MONTHLY: 1,
            self.BillingInterval.QUARTERLY: 3,
            self.BillingInterval.SEMI_ANNUAL: 6,
            self.BillingInterval.ANNUAL: 12,
        }.get(self.billing_interval, 12)

    def get_billing_schedule(self, from_date=None, to_date=None, include_history=False):
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

        interval_months = self.get_interval_months()
        events = defaultdict(lambda: {"items": [], "total": Decimal("0")})

        # Get all active items
        items = self.items.select_related("product").all()

        for item in items:
            # Determine item's billing period
            item_billing_start = item.billing_start_date or self.billing_start_date
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
                    events, item, item_billing_start, from_date, to_date
                )
                continue

            # Calculate billing dates for this item
            align_date = item.align_to_contract_at

            if align_date:
                # Item has alignment - generate dates before and after alignment
                self._add_pre_alignment_events(
                    events, item, item_billing_start, align_date,
                    from_date, to_date, interval_months
                )
                self._add_post_alignment_events(
                    events, item, align_date, item_billing_end,
                    from_date, to_date, interval_months
                )
            else:
                # No alignment - item follows contract cycle from its start
                self._add_regular_billing_events(
                    events, item, item_billing_start, item_billing_end,
                    from_date, to_date, interval_months
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

    def _add_regular_billing_events(
        self, events, item, start_date, end_date, from_date, to_date, interval_months
    ):
        """Add billing events for an item following the regular contract cycle."""
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        # Find the first billing date on or after item start
        billing_date = self.billing_start_date
        while billing_date < start_date:
            billing_date += relativedelta(months=interval_months)

        # Generate billing events
        while billing_date <= to_date:
            if billing_date >= from_date:
                if end_date is None or billing_date <= end_date:
                    # Use get_price_at() for date-aware pricing (falls back to unit_price)
                    price_at_date = item.get_price_at(billing_date)
                    # unit_price is monthly, multiply by interval for billing amount
                    amount = item.quantity * price_at_date * interval_months
                    events[billing_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": False,
                        "prorate_factor": None,
                    })
                    events[billing_date]["total"] += amount
            billing_date += relativedelta(months=interval_months)

    def _add_pre_alignment_events(
        self, events, item, start_date, align_date, from_date, to_date, interval_months
    ):
        """Add billing events before alignment (pro-rated first period)."""
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        # First billing is at start_date (pro-rated period until align_date)
        if start_date >= from_date and start_date <= to_date:
            # Calculate proration factor
            days_in_period = (align_date - start_date).days
            full_period_days = interval_months * 30  # Approximate
            prorate_factor = Decimal(days_in_period) / Decimal(full_period_days)

            # Use get_price_at() for date-aware pricing (falls back to unit_price)
            price_at_date = item.get_price_at(start_date)
            # unit_price is monthly, multiply by interval for billing amount
            amount = item.quantity * price_at_date * interval_months * prorate_factor
            events[start_date]["items"].append({
                "item_id": item.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": price_at_date,
                "amount": amount.quantize(Decimal("0.01")),
                "is_prorated": True,
                "prorate_factor": prorate_factor.quantize(Decimal("0.0001")),
            })
            events[start_date]["total"] += amount.quantize(Decimal("0.01"))

    def _add_post_alignment_events(
        self, events, item, align_date, end_date, from_date, to_date, interval_months
    ):
        """Add billing events after alignment (regular cycle)."""
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        billing_date = align_date
        while billing_date <= to_date:
            if billing_date >= from_date:
                if end_date is None or billing_date <= end_date:
                    # Use get_price_at() for date-aware pricing (falls back to unit_price)
                    price_at_date = item.get_price_at(billing_date)
                    # unit_price is monthly, multiply by interval for billing amount
                    amount = item.quantity * price_at_date * interval_months
                    events[billing_date]["items"].append({
                        "item_id": item.id,
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "unit_price": price_at_date,
                        "amount": amount,
                        "is_prorated": False,
                        "prorate_factor": None,
                    })
                    events[billing_date]["total"] += amount
            billing_date += relativedelta(months=interval_months)

    def _add_one_off_billing_event(
        self, events, item, billing_start, from_date, to_date
    ):
        """Add a single billing event for a one-off item."""
        from decimal import Decimal

        # One-off items are billed once at their billing start date
        billing_date = billing_start

        # Only include if within our date range
        if billing_date >= from_date and billing_date <= to_date:
            # Use get_price_at() for date-aware pricing (falls back to unit_price)
            price_at_date = item.get_price_at(billing_date)
            # One-off items use the raw price (not multiplied by interval)
            amount = item.quantity * price_at_date
            events[billing_date]["items"].append({
                "item_id": item.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": price_at_date,
                "amount": amount,
                "is_prorated": False,
                "prorate_factor": None,
                "is_one_off": True,
            })
            events[billing_date]["total"] += amount


class ContractItem(TenantModel):
    """A line item in a contract."""

    class PriceSource(models.TextChoices):
        LIST = "list", "From price list"
        CUSTOM = "custom", "Custom price"
        CUSTOMER_AGREEMENT = "customer_agreement", "Customer agreement"

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="contract_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
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
    price_locked = models.BooleanField(
        default=False,
        help_text="If True, price cannot be changed until price_locked_until.",
    )
    price_locked_until = models.DateField(
        null=True,
        blank=True,
        help_text="Date until price is locked. After this date, price_locked becomes False.",
    )
    added_by_amendment = models.ForeignKey(
        "ContractAmendment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_items",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def get_price_at(self, target_date):
        """
        Get the price for this item at a specific date.

        Looks up price from ContractItemPrice records if any exist.
        Falls back to unit_price if no price_periods defined.
        This ensures backward compatibility for existing contracts.

        Args:
            target_date: The date for which to get the price

        Returns:
            Decimal: The unit price at the given date
        """
        # Check for a price period that covers this date
        price_period = self.price_periods.filter(
            valid_from__lte=target_date,
        ).filter(
            models.Q(valid_to__gte=target_date) | models.Q(valid_to__isnull=True)
        ).order_by("-valid_from").first()

        if price_period:
            return price_period.unit_price

        # FALLBACK: Return the item's unit_price (existing behavior)
        return self.unit_price

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

    class Meta:
        ordering = ["-effective_date"]

    def __str__(self):
        return f"Amendment {self.id} - {self.get_type_display()}"


class ContractItemPrice(TenantModel):
    """Price for a contract item during a specific period.

    Enables year-specific pricing for contracts.
    Example: Year 1: €100/month, Year 2: €120/month, Year 3+: list price.
    """

    class PriceSource(models.TextChoices):
        FIXED = "fixed", "Fixed Agreement"
        LIST = "list", "List Price"
        NEGOTIATED = "negotiated", "To Be Negotiated"

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
        help_text="Monthly unit price during this period",
    )
    source = models.CharField(
        max_length=20,
        choices=PriceSource.choices,
        default=PriceSource.FIXED,
    )

    class Meta:
        ordering = ["valid_from"]

    def __str__(self):
        if self.valid_to:
            return f"{self.item.product.name}: €{self.unit_price} ({self.valid_from} - {self.valid_to})"
        return f"{self.item.product.name}: €{self.unit_price} (from {self.valid_from})"
