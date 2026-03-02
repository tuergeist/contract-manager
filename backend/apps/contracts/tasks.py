"""Celery tasks for time tracking data sync."""

import logging
import time
from collections import defaultdict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
)
def sync_time_tracking_mapping_task(self, mapping_id: int) -> bool:
    """Sync cached time tracking data for a single mapping."""
    from apps.contracts.services.time_tracking import sync_mapping_data

    return sync_mapping_data(mapping_id)


@shared_task(acks_late=True)
def refresh_all_time_tracking_data() -> int:
    """Refresh cached data for all active-tenant time tracking mappings.

    Groups mappings by tenant to send per-tenant notification summaries.
    Paces requests with a 5-second gap between each mapping to avoid
    hitting Clockodo's rate limits.

    Returns:
        Number of mappings synced.
    """
    from apps.contracts.models import TimeTrackingProjectMapping
    from apps.contracts.services.time_tracking import sync_mapping_data
    from apps.core.notifications import notify
    from apps.tenants.models import User

    mappings = list(
        TimeTrackingProjectMapping.objects.filter(
            tenant__is_active=True,
        ).select_related("tenant")
    )

    logger.info("Refreshing time tracking data for %d mappings", len(mappings))

    # Group by tenant
    tenant_stats = defaultdict(lambda: {"synced": 0, "failed": 0, "total": 0})

    total_synced = 0
    for mapping in mappings:
        tenant_id = mapping.tenant_id
        tenant_stats[tenant_id]["total"] += 1
        tenant_stats[tenant_id]["tenant"] = mapping.tenant

        try:
            if sync_mapping_data(mapping.id):
                total_synced += 1
                tenant_stats[tenant_id]["synced"] += 1
        except Exception:
            logger.exception("Failed to sync mapping %s", mapping.id)
            tenant_stats[tenant_id]["failed"] += 1
        time.sleep(5)  # Pace between mappings

    # Notify admin users per tenant
    for tenant_id, stats in tenant_stats.items():
        tenant = stats["tenant"]
        admins = list(
            User.objects.filter(tenant=tenant, is_active=True, is_admin=True)
        )
        if admins:
            notify(
                tenant,
                "time_tracking_sync_completed",
                recipients=admins,
                synced=stats["synced"],
                total=stats["total"],
                failed=stats["failed"],
            )

    logger.info(
        "Finished refreshing time tracking data: %d/%d synced",
        total_synced,
        len(mappings),
    )
    return total_synced


@shared_task(acks_late=True)
def auto_link_time_tracking_projects() -> int:
    """Auto-link time tracking projects based on pattern rules.

    For each active tenant with a configured provider:
    1. Fetch all projects once
    2. Match against active auto-link rules (non-cancelled contracts)
    3. Create mappings for new matches

    Returns:
        Number of new mappings created.
    """
    from apps.contracts.models import AutoLinkRule, Contract, TimeTrackingProjectMapping
    from apps.contracts.services.time_tracking import get_provider, matches_project_name
    from apps.tenants.models import Tenant

    tenants = Tenant.objects.filter(is_active=True)
    total_created = 0

    for tenant in tenants:
        provider = get_provider(tenant)
        if not provider:
            continue

        try:
            projects = provider.get_projects()
        except Exception:
            logger.exception("Failed to fetch projects for tenant %s", tenant.id)
            continue

        rules = list(
            AutoLinkRule.objects.filter(
                tenant=tenant,
                is_active=True,
            ).exclude(
                contract__status=Contract.Status.CANCELLED,
            ).select_related("contract", "contract_item").order_by("created_at")
        )

        if not rules:
            continue

        # Get already-linked project IDs for this tenant
        linked_ids = set(
            TimeTrackingProjectMapping.objects.filter(
                tenant=tenant,
            ).values_list("external_project_id", flat=True)
        )

        for rule in rules:
            for project in projects:
                if project.id in linked_ids:
                    continue
                if not matches_project_name(rule.pattern, rule.match_type, project.name):
                    continue

                TimeTrackingProjectMapping.objects.create(
                    tenant=tenant,
                    contract=rule.contract,
                    contract_item=rule.contract_item,
                    external_project_id=project.id,
                    external_project_name=project.name,
                    external_customer_name=project.customer_name,
                    link_source=TimeTrackingProjectMapping.LinkSource.AUTO,
                    auto_link_rule=rule,
                )
                linked_ids.add(project.id)
                total_created += 1

                # Trigger async data sync for new mapping
                mapping = TimeTrackingProjectMapping.objects.get(
                    tenant=tenant, external_project_id=project.id,
                )
                sync_time_tracking_mapping_task.delay(mapping.id)

    logger.info("Auto-link created %d new mappings", total_created)
    return total_created
