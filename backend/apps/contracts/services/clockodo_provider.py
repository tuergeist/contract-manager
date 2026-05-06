"""Clockodo time tracking provider implementation."""
import logging
import time
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

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request with exponential backoff retry on 429 and 5xx.

        Clockodo's quota window is on the order of minutes, so the initial
        backoff starts high (30s) and doubles on each retry. Total worst-case
        wait across 6 attempts: 30+60+120+240+480 = 15.5 minutes.

        On 4xx errors, the response body is logged and embedded in the raised
        exception so callers can surface a meaningful message to the user.
        """
        url = f"{self.API_BASE}/{endpoint}"
        max_attempts = 6
        initial_wait = 30  # seconds — Clockodo recovers slowly from 429
        for attempt in range(max_attempts):
            response = httpx.request(method, url, headers=self._get_headers(), timeout=30, **kwargs)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_attempts - 1:
                    self._raise_with_body(response, method, endpoint)
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = int(retry_after)
                else:
                    wait = initial_wait * (2 ** attempt)
                logger.warning("Clockodo %s on %s %s, retrying in %ss (attempt %d/%d)",
                               response.status_code, method, endpoint, wait, attempt + 1, max_attempts)
                time.sleep(wait)
                continue
            if response.status_code >= 400:
                self._raise_with_body(response, method, endpoint)
            return response.json()
        self._raise_with_body(response, method, endpoint)
        return response.json()

    def _raise_with_body(self, response, method: str, endpoint: str):
        """Log Clockodo response body and raise HTTPStatusError with body in message."""
        try:
            body = response.json()
        except Exception:
            body = response.text[:500]
        logger.error(
            "Clockodo %s %s -> %s: %r",
            method, endpoint, response.status_code, body,
        )
        # Build an HTTPStatusError whose str() includes the body so callers
        # using str(e) (e.g. UI error display) see the actual reason.
        message = f"Clockodo {method} /{endpoint} returned {response.status_code}: {body}"
        raise httpx.HTTPStatusError(message, request=response.request, response=response)

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, data: dict) -> dict:
        return self._request("POST", endpoint, json=data)

    def _put(self, endpoint: str, data: dict) -> dict:
        return self._request("PUT", endpoint, json=data)

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

    def get_services(self) -> list[dict]:
        """Fetch all services from Clockodo."""
        try:
            services = self._get_all_pages("services", "services")
            return [{"id": str(s["id"]), "name": s.get("name", "")} for s in services]
        except Exception as e:
            logger.error("Failed to fetch Clockodo services: %s", e)
            return []

    def get_users(self) -> list[dict]:
        """Fetch all users from Clockodo."""
        try:
            users = self._get_all_pages("users", "users")
            return [{"id": str(u["id"]), "name": u.get("name", "")} for u in users]
        except Exception as e:
            logger.error("Failed to fetch Clockodo users: %s", e)
            return []

    def get_absences(self, year: int) -> list[dict]:
        """Fetch absences for a given year from Clockodo."""
        try:
            data = self._get("absences", {"year": year})
            absences = data.get("absences", [])
            return [
                {
                    "user_id": str(a["users_id"]),
                    "date_since": a.get("date_since", ""),
                    "date_until": a.get("date_until", ""),
                    "count_days": float(a.get("count_days", 0) or 0),
                    "type": a.get("type", 0),
                    "status": a.get("status", 0),
                }
                for a in absences
            ]
        except Exception as e:
            logger.error("Failed to fetch Clockodo absences: %s", e)
            return []

    # Clockodo absence type codes → internal AbsenceType values
    # See: https://www.clockodo.com/en/api/absences/
    ABSENCE_TYPE_MAP = {
        1: "vacation",             # Regular holiday / vacation
        2: "special_leave",        # Special leave
        3: "overtime_reduction",   # Reduction of overtime
        4: "sick",                 # Sick day
        5: "sick_child",           # Sick day of a child
        6: "education",            # School / further education
        7: "other",                # Maternity protection
        8: "other",                # Home office (typically filtered out)
        9: "other",                # Work out of office
        10: "special_leave",       # Special leaves (company-specific)
        11: "sick_certificate",    # Sick with certificate
        12: "sick",                # Sick without pay
        13: "other",               # Parental leave
        14: "other",               # Sabbatical
    }

    def normalize_absence_type(self, raw_type: int) -> str:
        """Map Clockodo absence type code to internal AbsenceType value."""
        return self.ABSENCE_TYPE_MAP.get(raw_type, "other")

    def get_department_time_data(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        """Get time entries grouped by user AND service.

        Uses entrygroups with double grouping (users_id, services_id)
        for a single efficient API call.
        """
        # Fetch users for name lookup
        users_by_id: dict[int, str] = {}
        try:
            users = self._get_all_pages("users", "users")
            for u in users:
                users_by_id[u["id"]] = u.get("name", "")
        except Exception as e:
            logger.warning("Failed to fetch Clockodo users: %s", e)

        # Fetch services for name lookup
        services_by_id: dict[int, str] = {}
        try:
            services = self._get_all_pages("services", "services")
            for s in services:
                services_by_id[s["id"]] = s.get("name", "")
        except Exception as e:
            logger.warning("Failed to fetch Clockodo services: %s", e)

        time_since = f"{date_from.isoformat()}T00:00:00Z" if date_from else "2000-01-01T00:00:00Z"
        time_until = f"{date_to.isoformat()}T23:59:59Z" if date_to else f"{date.today().isoformat()}T23:59:59Z"

        try:
            params = {
                "time_since": time_since,
                "time_until": time_until,
                "grouping[]": ["users_id", "services_id"],
            }
            data = self._get("entrygroups", params)
        except Exception as e:
            logger.error("Failed to fetch entrygroups for department time data: %s", e)
            return []

        result = []
        for user_group in data.get("groups", []):
            user_id = user_group.get("group")
            user_name = user_group.get("name") or users_by_id.get(int(user_id) if user_id else 0, "")

            for service_group in user_group.get("sub_groups", []):
                service_id = service_group.get("group")
                service_name = service_group.get("name") or services_by_id.get(int(service_id) if service_id else 0, "")
                duration_seconds = service_group.get("duration", 0) or 0
                hours = round(duration_seconds / 3600.0, 2)

                result.append({
                    "user_id": str(user_id),
                    "user_name": user_name,
                    "service_id": str(service_id),
                    "service_name": service_name,
                    "hours": hours,
                })

        return result

    def get_time_summary(
        self,
        project_ids: list[str],
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TimeTrackingSummary:
        """Get aggregated time data from Clockodo for the given projects.

        Uses the entrygroups endpoint with a comma-separated project filter
        and chunking — fetches data for *all* projects in just two calls per
        chunk (one grouped by service, one by month) instead of two calls
        per project. Clockodo's API documentation explicitly recommends this
        pattern over per-project polling, which is what was producing 429s.
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

        # Chunk project IDs to keep URLs reasonable (~25 IDs ≈ 250 chars in
        # query string). Clockodo accepts comma-separated values for filters.
        CHUNK_SIZE = 25
        SLEEP_BETWEEN_CALLS = 2.0  # seconds — paces the calls without holding the worker too long

        chunks = [
            project_ids[i:i + CHUNK_SIZE]
            for i in range(0, len(project_ids), CHUNK_SIZE)
        ]

        for chunk_idx, chunk in enumerate(chunks):
            project_filter = ",".join(str(p) for p in chunk)
            try:
                # 1. Breakdown by service (across all projects in this chunk)
                data_by_service = self._get("entrygroups", {
                    "time_since": time_since,
                    "time_until": time_until,
                    "filter[projects_id]": project_filter,
                    "grouping[]": "services_id",
                })
                for group in data_by_service.get("groups", []):
                    service_id = group.get("group")
                    service_name = services_by_id.get(
                        int(service_id) if service_id else 0, ""
                    ) or group.get("name", "") or "Other"
                    duration_hours = (group.get("duration", 0) or 0) / 3600.0
                    revenue = float(group.get("revenue", 0) or 0)
                    service_data[service_name]["hours"] += duration_hours
                    service_data[service_name]["revenue"] += revenue

                time.sleep(SLEEP_BETWEEN_CALLS)

                # 2. Breakdown by month (across all projects in this chunk)
                data_by_month = self._get("entrygroups", {
                    "time_since": time_since,
                    "time_until": time_until,
                    "filter[projects_id]": project_filter,
                    "grouping[]": "month",
                })
                for group in data_by_month.get("groups", []):
                    month_key = group.get("group", "")
                    duration_hours = (group.get("duration", 0) or 0) / 3600.0
                    revenue = float(group.get("revenue", 0) or 0)
                    month_data[month_key]["hours"] += duration_hours
                    month_data[month_key]["revenue"] += revenue

                # Pace before next chunk
                if chunk_idx < len(chunks) - 1:
                    time.sleep(SLEEP_BETWEEN_CALLS)

            except Exception as e:
                logger.error(
                    "Failed to fetch entrygroups for project chunk %s: %s",
                    project_filter, e,
                )
                continue

        by_service = [
            {"service_name": k, "hours": round(v["hours"], 2), "revenue": round(v["revenue"], 2)}
            for k, v in sorted(service_data.items())
        ]
        by_month = [
            {"month": k, "hours": round(v["hours"], 2), "revenue": round(v["revenue"], 2)}
            for k, v in sorted(month_data.items())
        ]

        # Derive totals from month breakdown so all views are always consistent
        total_hours = sum(v["hours"] for v in month_data.values())
        total_revenue = sum(v["revenue"] for v in month_data.values())

        return TimeTrackingSummary(
            total_hours=round(total_hours, 2),
            total_revenue=round(total_revenue, 2),
            by_service=by_service,
            by_month=by_month,
        )

    # --- Write operations ---

    def create_customer(self, name: str) -> dict:
        """Create a customer in Clockodo.

        Returns:
            dict with 'id' (int) and 'name' (str)
        """
        data = self._post("customers", {"name": name})
        customer = data.get("customer", data)
        return {"id": str(customer["id"]), "name": customer.get("name", name)}

    def create_project(self, customer_id: str, name: str, active: bool = True) -> dict:
        """Create a project in Clockodo under a specific customer.

        Returns:
            dict with 'id' (int) and 'name' (str)
        """
        data = self._post("projects", {
            "name": name,
            "customers_id": int(customer_id),
            "active": active,
        })
        project = data.get("project", data)
        return {"id": str(project["id"]), "name": project.get("name", name)}

    def get_customer_projects(self, customer_id: str) -> list[TimeTrackingProject]:
        """Fetch all projects for a specific Clockodo customer."""
        try:
            projects = self._get_all_pages("projects", "projects", {
                "filter[customers_id]": customer_id,
            })
            return [
                TimeTrackingProject(
                    id=str(p["id"]),
                    name=p.get("name", ""),
                    customer_name="",
                    active=p.get("active", True),
                )
                for p in projects
            ]
        except Exception as e:
            logger.error("Failed to fetch projects for customer %s: %s", customer_id, e)
            return []

    def get_customers(self, active_only: bool = True) -> list[dict]:
        """Fetch customers from Clockodo, optionally filtering out archived ones."""
        try:
            customers = self._get_all_pages("customers", "customers")
            if active_only:
                customers = [c for c in customers if c.get("active", True)]
            return [{"id": str(c["id"]), "name": c.get("name", "")} for c in customers]
        except Exception as e:
            logger.error("Failed to fetch Clockodo customers: %s", e)
            return []

    def deactivate_project(self, project_id: str) -> bool:
        """Deactivate (close) a project in Clockodo."""
        try:
            self._put(f"projects/{project_id}", {"active": False})
            return True
        except Exception as e:
            logger.error("Failed to deactivate project %s: %s", project_id, e)
            return False
