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
        if config.get("sync_mode") == "webhooks":
            logger.info("Skipping tenant %s (webhook sync mode)", tenant.id)
            continue

        logger.info("Auto-syncing HubSpot for tenant %s", tenant.id)
        _sync_tenant_hubspot(tenant)
        synced += 1

    logger.info("HubSpot auto-sync complete: %d tenants synced", synced)
    return synced


def _sync_tenant_hubspot(tenant) -> None:
    """Run all three HubSpot syncs for a single tenant, storing timestamps."""
    from apps.core.notifications import notify
    from apps.customers.hubspot import HubSpotService
    from apps.tenants.models import User

    service = HubSpotService(tenant)
    now_iso = datetime.now(timezone.utc).isoformat()

    results = {}
    errors = {}

    # Customers
    try:
        result = service.sync_companies()
        tenant.hubspot_config["last_auto_sync_customers"] = now_iso
        results["customers"] = {
            "created": result.get("created", 0),
            "updated": result.get("updated", 0),
        }
        logger.info(
            "Tenant %s customers: created=%s, updated=%s",
            tenant.id,
            result.get("created", 0),
            result.get("updated", 0),
        )
    except Exception as e:
        errors["customers"] = str(e)
        logger.exception("HubSpot customer sync failed for tenant %s", tenant.id)

    # Products
    try:
        result = service.sync_products()
        tenant.hubspot_config["last_auto_sync_products"] = now_iso
        results["products"] = {
            "created": result.get("created", 0),
            "updated": result.get("updated", 0),
        }
        logger.info(
            "Tenant %s products: created=%s, updated=%s",
            tenant.id,
            result.get("created", 0),
            result.get("updated", 0),
        )
    except Exception as e:
        errors["products"] = str(e)
        logger.exception("HubSpot product sync failed for tenant %s", tenant.id)

    # Deals
    try:
        result = service.sync_deals()
        tenant.hubspot_config["last_auto_sync_deals"] = now_iso
        results["deals"] = {
            "created": result.get("created", 0),
            "skipped": result.get("skipped", 0),
        }
        logger.info(
            "Tenant %s deals: created=%s, skipped=%s",
            tenant.id,
            result.get("created", 0),
            result.get("skipped", 0),
        )
    except Exception as e:
        errors["deals"] = str(e)
        logger.exception("HubSpot deal sync failed for tenant %s", tenant.id)

    tenant.save(update_fields=["hubspot_config"])

    # Notify admin users
    admins = list(
        User.objects.filter(tenant=tenant, is_active=True, is_admin=True)
    )
    if admins:
        notify(
            tenant,
            "hubspot_sync_completed",
            recipients=admins,
            results=results,
            errors=errors,
        )


# Supported webhook event types and their object kind
_EVENT_TYPE_MAP = {
    "company.creation": "company",
    "company.propertyChange": "company",
    "company.deletion": "company",
    "company.merge": "company",
    "company.associationChange": "company_association",
    "product.creation": "product",
    "product.propertyChange": "product",
    "product.deletion": "product",
    "deal.creation": "deal",
    "deal.propertyChange": "deal",
    "deal.deletion": "deal",
}


@shared_task(
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def process_hubspot_webhook_event(event: dict, tenant_id: int) -> str:
    """Process a single HubSpot webhook event.

    Fetches the full record from HubSpot and upserts it locally.
    """
    from apps.customers.hubspot import HubSpotError, HubSpotService
    from apps.customers.models import Customer, WebhookEventLog
    from apps.products.models import Product
    from apps.tenants.models import Tenant

    subscription_type = event.get("subscriptionType", "")
    object_id = str(event.get("objectId", ""))
    received_at = datetime.now(timezone.utc)

    object_kind = _EVENT_TYPE_MAP.get(subscription_type)
    if not object_kind:
        logger.debug("Ignoring unsupported webhook event type: %s", subscription_type)
        # Log ignored events if we can find the tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id, is_active=True)
            WebhookEventLog.objects.create(
                tenant=tenant,
                subscription_type=subscription_type,
                object_id=object_id,
                object_kind="",
                status=WebhookEventLog.Status.IGNORED,
                result="ignored",
                received_at=received_at,
            )
        except Tenant.DoesNotExist:
            pass
        return "ignored"

    try:
        tenant = Tenant.objects.get(id=tenant_id, is_active=True)
    except Tenant.DoesNotExist:
        logger.warning("Tenant %s not found for webhook event", tenant_id)
        return "tenant_not_found"

    service = HubSpotService(tenant)

    is_deletion = subscription_type.endswith(".deletion")

    try:
        result = _process_event(
            service, tenant, subscription_type, object_id, object_kind, is_deletion
        )
        WebhookEventLog.objects.create(
            tenant=tenant,
            subscription_type=subscription_type,
            object_id=object_id,
            object_kind=object_kind,
            status=WebhookEventLog.Status.PROCESSED,
            result=result,
            received_at=received_at,
        )
        return result
    except Exception as e:
        WebhookEventLog.objects.create(
            tenant=tenant,
            subscription_type=subscription_type,
            object_id=object_id,
            object_kind=object_kind,
            status=WebhookEventLog.Status.FAILED,
            result="error",
            error_message=str(e),
            received_at=received_at,
        )
        raise


def _process_event(service, tenant, subscription_type, object_id, object_kind, is_deletion):
    """Process a single webhook event and return a result string."""
    from apps.customers.models import Customer
    from apps.products.models import Product

    if object_kind == "company":
        if is_deletion:
            customer = Customer.objects.filter(
                tenant=tenant, hubspot_id=object_id
            ).first()
            if customer:
                customer.is_active = False
                customer.hubspot_deleted_at = datetime.now(timezone.utc)
                customer.save(update_fields=["is_active", "hubspot_deleted_at"])
                logger.info("Marked customer %s as deleted (hubspot %s)", customer.id, object_id)
            return "company_deleted"

        company_data = service.fetch_company(object_id)
        if company_data is None:
            customer = Customer.objects.filter(
                tenant=tenant, hubspot_id=object_id
            ).first()
            if customer:
                customer.is_active = False
                customer.hubspot_deleted_at = datetime.now(timezone.utc)
                customer.save(update_fields=["is_active", "hubspot_deleted_at"])
            logger.warning("Company %s not found in HubSpot (404)", object_id)
            return "company_not_found"

        properties = company_data.get("properties", {})
        is_active = service._company_matches_filters(properties)
        service._sync_company(company_data, is_active=is_active)
        return "company_synced"

    elif object_kind == "company_association":
        # Association change on a company — re-sync billing contacts
        billing_label = service.config.get("billing_contact_label")
        if not billing_label:
            return "no_billing_label_configured"

        customer = Customer.objects.filter(
            tenant=tenant, hubspot_id=object_id
        ).first()
        if not customer:
            return "customer_not_found"

        import httpx
        with httpx.Client() as client:
            service._sync_billing_contacts_for_customer(client, customer, billing_label)
        return "billing_contacts_synced"

    elif object_kind == "product":
        if is_deletion:
            product = Product.objects.filter(
                tenant=tenant, hubspot_id=object_id
            ).first()
            if product:
                product.is_active = False
                product.save(update_fields=["is_active"])
                logger.info("Marked product %s as deleted (hubspot %s)", product.id, object_id)
            return "product_deleted"

        product_data = service.fetch_product(object_id)
        if product_data is None:
            product = Product.objects.filter(
                tenant=tenant, hubspot_id=object_id
            ).first()
            if product:
                product.is_active = False
                product.save(update_fields=["is_active"])
            logger.warning("Product %s not found in HubSpot (404)", object_id)
            return "product_not_found"

        service._sync_product(product_data)
        return "product_synced"

    elif object_kind == "deal":
        if is_deletion:
            logger.info("Deal deletion event for %s — no local action", object_id)
            return "deal_deleted"

        deal_data = service.fetch_deal(object_id)
        if deal_data is None:
            logger.warning("Deal %s not found in HubSpot (404)", object_id)
            return "deal_not_found"

        import httpx
        with httpx.Client() as client:
            service._sync_deal(deal_data, client)
        return "deal_synced"

    return "unhandled"
