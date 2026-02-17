"""Celery tasks for time tracking data sync."""

import logging
import time

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

    Paces requests with a 5-second gap between each mapping to avoid
    hitting Clockodo's rate limits.

    Returns:
        Number of mappings synced.
    """
    from apps.contracts.models import TimeTrackingProjectMapping
    from apps.contracts.services.time_tracking import sync_mapping_data

    mapping_ids = list(
        TimeTrackingProjectMapping.objects.filter(
            tenant__is_active=True,
        ).values_list("id", flat=True)
    )

    logger.info("Refreshing time tracking data for %d mappings", len(mapping_ids))

    synced = 0
    for mapping_id in mapping_ids:
        try:
            if sync_mapping_data(mapping_id):
                synced += 1
        except Exception:
            logger.exception("Failed to sync mapping %s", mapping_id)
        time.sleep(5)  # Pace between mappings

    logger.info("Finished refreshing time tracking data: %d/%d synced", synced, len(mapping_ids))
    return synced
