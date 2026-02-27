"""Signal handlers for forecast cache invalidation."""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.contracts.forecast_cache import invalidate_tenant_forecast

logger = logging.getLogger(__name__)


@receiver(post_save, sender="contracts.Contract")
@receiver(post_delete, sender="contracts.Contract")
def invalidate_on_contract_change(sender, instance, **kwargs):
    invalidate_tenant_forecast(instance.tenant_id)


@receiver(post_save, sender="contracts.ContractItem")
@receiver(post_delete, sender="contracts.ContractItem")
def invalidate_on_contract_item_change(sender, instance, **kwargs):
    invalidate_tenant_forecast(instance.tenant_id)


@receiver(post_save, sender="contracts.ContractItemPrice")
@receiver(post_delete, sender="contracts.ContractItemPrice")
def invalidate_on_contract_item_price_change(sender, instance, **kwargs):
    invalidate_tenant_forecast(instance.tenant_id)


@receiver(post_save, sender="invoices.InvoiceRecord")
@receiver(post_delete, sender="invoices.InvoiceRecord")
def invalidate_on_invoice_record_change(sender, instance, **kwargs):
    invalidate_tenant_forecast(instance.tenant_id)


@receiver(post_save, sender="invoices.ImportedInvoice")
def invalidate_on_imported_invoice_change(sender, instance, **kwargs):
    invalidate_tenant_forecast(instance.tenant_id)
