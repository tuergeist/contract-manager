"""Abstract time tracking provider interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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


def get_provider(tenant) -> TimeTrackingProvider | None:
    """Factory: returns the configured provider for this tenant."""
    config = tenant.time_tracking_config or {}
    provider_type = config.get("provider")
    if provider_type == "clockodo":
        from .clockodo_provider import ClockodoProvider
        return ClockodoProvider(config)
    return None
