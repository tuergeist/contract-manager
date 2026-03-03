"""Abstract time tracking provider interface and cache helpers."""
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from django.utils import timezone


@dataclass
class TimeTrackingProject:
    """A project from the external time tracking system."""
    id: str
    name: str
    customer_name: str
    active: bool


@dataclass
class TimeTrackingSummary:
    """Aggregated time data."""
    total_hours: float
    total_revenue: float
    by_service: list[dict] = field(default_factory=list)
    by_month: list[dict] = field(default_factory=list)


class TimeTrackingProvider(ABC):
    """Abstract base class for time tracking integrations."""

    @abstractmethod
    def test_connection(self) -> dict:
        """Test the connection to the time tracking service.

        Returns:
            dict with 'success' (bool) and optional 'error' (str)
        """
        ...

    @abstractmethod
    def get_projects(self) -> list[TimeTrackingProject]:
        """Fetch all projects from the time tracking service.

        Returns:
            List of TimeTrackingProject objects
        """
        ...

    @abstractmethod
    def get_time_summary(
        self,
        project_ids: list[str],
        date_from=None,
        date_to=None,
    ) -> TimeTrackingSummary:
        """Get aggregated time data for the given projects.

        Args:
            project_ids: List of external project IDs
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            TimeTrackingSummary with hours, revenue, and breakdowns
        """
        ...


    def get_services(self) -> list[dict]:
        """Fetch all services from the time tracking provider.

        Returns:
            List of dicts with 'id' and 'name' keys.
        """
        raise NotImplementedError

    def get_department_time_data(
        self,
        date_from=None,
        date_to=None,
    ) -> list[dict]:
        """Get time entries grouped by user and service.

        Returns:
            Flat list of dicts: {user_id, user_name, service_id, service_name, hours}
        """
        raise NotImplementedError


logger = logging.getLogger(__name__)


def matches_project_name(pattern: str, match_type: str, project_name: str) -> bool:
    """Check if a project name matches a pattern (case-insensitive)."""
    p = pattern.lower()
    name = project_name.lower()
    if match_type == "contains":
        return p in name
    elif match_type == "starts_with":
        return name.startswith(p)
    return False


def get_provider(tenant) -> TimeTrackingProvider | None:
    """Factory: returns the configured provider for this tenant."""
    config = tenant.time_tracking_config or {}
    provider_type = config.get("provider")
    if provider_type == "clockodo":
        from .clockodo_provider import ClockodoProvider
        return ClockodoProvider(config)
    return None


def sync_mapping_data(mapping_id: int) -> bool:
    """Fetch fresh time data from the provider and store in cache fields."""
    from apps.contracts.models import TimeTrackingProjectMapping

    mapping = TimeTrackingProjectMapping.objects.select_related("tenant").get(id=mapping_id)
    provider = get_provider(mapping.tenant)
    if not provider:
        logger.warning("No provider configured for tenant %s", mapping.tenant_id)
        return False

    try:
        summary = provider.get_time_summary([mapping.external_project_id])
        mapping.cached_total_hours = summary.total_hours
        mapping.cached_total_revenue = summary.total_revenue
        mapping.cached_by_service = summary.by_service
        mapping.cached_by_month = summary.by_month
        mapping.last_synced = timezone.now()
        mapping.save(update_fields=[
            "cached_total_hours", "cached_total_revenue",
            "cached_by_service", "cached_by_month",
            "last_synced", "updated_at",
        ])
        logger.info("Synced time tracking data for mapping %s", mapping_id)
        return True
    except Exception:
        logger.exception("Failed to sync mapping %s", mapping_id)
        return False


def get_cached_summary(mappings_qs) -> dict:
    """Aggregate cached data across mappings, return dict matching TimeTrackingSummary shape."""
    total_hours = 0.0
    total_revenue = 0.0
    service_data: dict[str, dict] = defaultdict(lambda: {"hours": 0.0, "revenue": 0.0})
    month_data: dict[str, dict] = defaultdict(lambda: {"hours": 0.0, "revenue": 0.0})
    oldest_sync: datetime | None = None

    for m in mappings_qs:
        total_hours += m.cached_total_hours
        total_revenue += m.cached_total_revenue

        for s in (m.cached_by_service or []):
            service_data[s["service_name"]]["hours"] += s["hours"]
            service_data[s["service_name"]]["revenue"] += s["revenue"]

        for mo in (m.cached_by_month or []):
            month_data[mo["month"]]["hours"] += mo["hours"]
            month_data[mo["month"]]["revenue"] += mo["revenue"]

        if m.last_synced:
            if oldest_sync is None or m.last_synced < oldest_sync:
                oldest_sync = m.last_synced

    return {
        "total_hours": round(total_hours, 2),
        "total_revenue": round(total_revenue, 2),
        "by_service": [
            {"service_name": k, "hours": round(v["hours"], 2), "revenue": round(v["revenue"], 2)}
            for k, v in sorted(service_data.items())
        ],
        "by_month": [
            {"month": k, "hours": round(v["hours"], 2), "revenue": round(v["revenue"], 2)}
            for k, v in sorted(month_data.items())
        ],
        "last_synced": oldest_sync,
    }
