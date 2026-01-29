"""Product models."""
from django.db import models

from apps.core.models import TenantModel


class ProductCategory(TenantModel):
    """Category for grouping products."""

    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Product categories"
        ordering = ["name"]
        unique_together = ["tenant", "name"]

    def __str__(self):
        return self.name


class Product(TenantModel):
    """A product that can be added to contracts."""

    class ProductType(models.TextChoices):
        SUBSCRIPTION = "subscription", "Subscription"
        ONE_OFF = "one_off", "One-off"

    class BillingFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-annual"
        ANNUAL = "annual", "Annual"

    hubspot_id = models.CharField(max_length=100, blank=True, null=True)
    netsuite_item_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Item name from NetSuite (e.g., 'Hosting + Maintenance : Software Maintenance')",
    )
    sku = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.SUBSCRIPTION,
    )
    billing_frequency = models.CharField(
        max_length=20,
        choices=BillingFrequency.choices,
        null=True,
        blank=True,
        help_text="Default billing frequency for this product",
    )
    is_active = models.BooleanField(default=True)
    successor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predecessors",
    )
    synced_at = models.DateTimeField(null=True, blank=True)
    hubspot_deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["tenant", "hubspot_id"]

    def __str__(self):
        return self.name


class ProductPrice(TenantModel):
    """Price for a product with validity period."""

    class PriceModel(models.TextChoices):
        UNIT = "unit", "Per Unit"
        TIERED = "tiered", "Tiered"
        PER_UNIT = "per_unit", "Per Unit (usage)"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_model = models.CharField(
        max_length=20,
        choices=PriceModel.choices,
        default=PriceModel.UNIT,
    )
    tiers = models.JSONField(default=list, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-valid_from"]

    def __str__(self):
        return f"{self.product.name}: {self.price}"
