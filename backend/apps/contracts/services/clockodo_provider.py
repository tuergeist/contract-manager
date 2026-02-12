"""Clockodo time tracking provider implementation."""
import logging
from collections import defaultdict
from datetime import date

import httpx

from .time_tracking import TimeTrackingProject, TimeTrackingProvider, TimeTrackingSummary

logger = logging.getLogger(__name__)


class ClockodoProvider(TimeTrackingProvider):
    """Clockodo API v2 integration.

    API docs: https://www.clockodo.com/en/api/
    Base URL: https://my.clockodo.com/api/v2
    """

    API_BASE = "https://my.clockodo.com/api/v2"

    def __init__(self, config: dict):
        self.api_email = config.get("api_email", "")
        self.api_key = config.get("api_key", "")

    def _get_headers(self) -> dict:
        return {
            "X-ClockodoApiUser": self.api_email,
            "X-ClockodoApiKey": self.api_key,
            "X-Clockodo-External-Application": "ContractManager;support@example.com",
            "Accept": "application/json",
        }

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a GET request to the Clockodo API.

        Args:
            endpoint: Path relative to API_BASE, e.g. "projects" or "entries"
        """
        url = f"{self.API_BASE}/{endpoint}"
        response = httpx.get(url, headers=self._get_headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get_all_pages(self, endpoint: str, key: str, params: dict | None = None) -> list:
        """Fetch all pages for a paginated endpoint.

        Args:
            endpoint: API endpoint path
            key: Response key containing the list (e.g. "projects", "entries")
            params: Query parameters
        """
        params = dict(params) if params else {}
        all_items = []
        page = 1

        while True:
            params["page"] = page
            data = self._get(endpoint, params)
            items = data.get(key, [])
            all_items.extend(items)

            paging = data.get("paging", {})
            count_pages = paging.get("count_pages", 1)
            if page >= count_pages:
                break
            page += 1

        return all_items

    def test_connection(self) -> dict:
        """Test the Clockodo API connection."""
        try:
            self._get("aggregates/users/me")
            return {"success": True}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"success": False, "error": "Invalid credentials"}
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_projects(self) -> list[TimeTrackingProject]:
        """Fetch all projects from Clockodo."""
        try:
            projects = self._get_all_pages("projects", "projects")
        except Exception as e:
            logger.error("Failed to fetch Clockodo projects: %s", e)
            return []

        # Fetch customer names
        customers_by_id: dict[int, str] = {}
        try:
            customers = self._get_all_pages("customers", "customers")
            for c in customers:
                customers_by_id[c["id"]] = c.get("name", "")
        except Exception as e:
            logger.warning("Failed to fetch Clockodo customers: %s", e)

        result = []
        for p in projects:
            result.append(
                TimeTrackingProject(
                    id=str(p["id"]),
                    name=p.get("name", ""),
                    customer_name=customers_by_id.get(p.get("customers_id", 0), ""),
                    active=p.get("active", True),
                )
            )
        return result

    def get_time_summary(
        self,
        project_ids: list[str],
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TimeTrackingSummary:
        """Get aggregated time data from Clockodo for the given projects.

        Uses the entrygroups endpoint for efficient aggregation instead of
        fetching individual entries.
        """
        if not project_ids:
            return TimeTrackingSummary(total_hours=0, total_revenue=0)

        # Build time range params (ISO 8601 UTC format required)
        # Note: Clockodo rejects far-future dates, so use today as max
        time_since = f"{date_from.isoformat()}T00:00:00Z" if date_from else "2000-01-01T00:00:00Z"
        if date_to:
            time_until = f"{date_to.isoformat()}T23:59:59Z"
        else:
            time_until = f"{date.today().isoformat()}T23:59:59Z"

        total_hours = 0.0
        total_revenue = 0.0
        service_data: dict[str, dict] = defaultdict(lambda: {"hours": 0.0, "revenue": 0.0})
        month_data: dict[str, dict] = defaultdict(lambda: {"hours": 0.0, "revenue": 0.0})

        # Fetch services for name lookup
        services_by_id: dict[int, str] = {}
        try:
            services = self._get_all_pages("services", "services")
            for s in services:
                services_by_id[s["id"]] = s.get("name", "")
        except Exception as e:
            logger.warning("Failed to fetch Clockodo services: %s", e)

        # Use entrygroups endpoint for aggregated data per project
        for project_id in project_ids:
            try:
                # Get total for this project (grouping is required)
                params = {
                    "time_since": time_since,
                    "time_until": time_until,
                    "filter[projects_id]": project_id,
                    "grouping[]": "projects_id",
                }
                data = self._get("entrygroups", params)
                groups = data.get("groups", [])

                # The response contains a single group with duration and revenue
                for group in groups:
                    duration_seconds = group.get("duration", 0) or 0
                    duration_hours = duration_seconds / 3600.0
                    revenue = float(group.get("revenue", 0) or 0)
                    total_hours += duration_hours
                    total_revenue += revenue

                # Get breakdown by service
                params_by_service = {
                    "time_since": time_since,
                    "time_until": time_until,
                    "filter[projects_id]": project_id,
                    "grouping[]": "services_id",
                }
                data_by_service = self._get("entrygroups", params_by_service)
                for group in data_by_service.get("groups", []):
                    service_id = group.get("group")  # The group value is the service ID
                    service_name = services_by_id.get(int(service_id) if service_id else 0, "") or group.get("name", "") or "Other"
                    duration_seconds = group.get("duration", 0) or 0
                    duration_hours = duration_seconds / 3600.0
                    revenue = float(group.get("revenue", 0) or 0)
                    service_data[service_name]["hours"] += duration_hours
                    service_data[service_name]["revenue"] += revenue

                # Get breakdown by month
                params_by_month = {
                    "time_since": time_since,
                    "time_until": time_until,
                    "filter[projects_id]": project_id,
                    "grouping[]": "month",
                }
                data_by_month = self._get("entrygroups", params_by_month)
                for group in data_by_month.get("groups", []):
                    month_key = group.get("group", "")  # e.g., "2024-03"
                    duration_seconds = group.get("duration", 0) or 0
                    duration_hours = duration_seconds / 3600.0
                    revenue = float(group.get("revenue", 0) or 0)
                    month_data[month_key]["hours"] += duration_hours
                    month_data[month_key]["revenue"] += revenue

            except Exception as e:
                logger.error("Failed to fetch entrygroups for project %s: %s", project_id, e)
                continue

        by_service = [
            {"service_name": k, "hours": round(v["hours"], 2), "revenue": round(v["revenue"], 2)}
            for k, v in sorted(service_data.items())
        ]
        by_month = [
            {"month": k, "hours": round(v["hours"], 2), "revenue": round(v["revenue"], 2)}
            for k, v in sorted(month_data.items())
        ]

        return TimeTrackingSummary(
            total_hours=round(total_hours, 2),
            total_revenue=round(total_revenue, 2),
            by_service=by_service,
            by_month=by_month,
        )
