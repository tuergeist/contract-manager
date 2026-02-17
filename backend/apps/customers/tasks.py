"""Celery tasks for HubSpot background sync."""

import logging
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(acks_late=True)
def sync_all_hubspot_tenants() -> int:
    """Periodic task: sync HubSpot data for all tenants with auto-sync enabled.

    Syncs customers → products → deals sequentially per tenant.
    Each sync type is isolated so a failure in one doesn't block the others.

    Returns:
        Number of tenants synced.
    """
    from apps.customers.hubspot import HubSpotService
    from apps.tenants.models import Tenant

    tenants = Tenant.objects.filter(is_active=True)
    synced = 0

    for tenant in tenants:
        config = tenant.hubspot_config or {}
        if not config.get("api_key") or not config.get("auto_sync_enabled"):
            continue

        logger.info("Auto-syncing HubSpot for tenant %s", tenant.id)
        _sync_tenant_hubspot(tenant)
        synced += 1

    logger.info("HubSpot auto-sync complete: %d tenants synced", synced)
    return synced


def _sync_tenant_hubspot(tenant) -> None:
    """Run all three HubSpot syncs for a single tenant, storing timestamps."""
    from apps.customers.hubspot import HubSpotService

    service = HubSpotService(tenant)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Customers
    try:
        result = service.sync_companies()
        tenant.hubspot_config["last_auto_sync_customers"] = now_iso
        logger.info(
            "Tenant %s customers: created=%s, updated=%s",
            tenant.id,
            result.get("created", 0),
            result.get("updated", 0),
        )
    except Exception:
        logger.exception("HubSpot customer sync failed for tenant %s", tenant.id)

    # Products
    try:
        result = service.sync_products()
        tenant.hubspot_config["last_auto_sync_products"] = now_iso
        logger.info(
            "Tenant %s products: created=%s, updated=%s",
            tenant.id,
            result.get("created", 0),
            result.get("updated", 0),
        )
    except Exception:
        logger.exception("HubSpot product sync failed for tenant %s", tenant.id)

    # Deals
    try:
        result = service.sync_deals()
        tenant.hubspot_config["last_auto_sync_deals"] = now_iso
        logger.info(
            "Tenant %s deals: created=%s, skipped=%s",
            tenant.id,
            result.get("created", 0),
            result.get("skipped", 0),
        )
    except Exception:
        logger.exception("HubSpot deal sync failed for tenant %s", tenant.id)

    tenant.save(update_fields=["hubspot_config"])
