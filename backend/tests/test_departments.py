"""Tests for department time analysis: CRUD, service mapping, and analysis query."""
import pytest
from datetime import date
from unittest.mock import Mock, patch

from apps.contracts.models import Department, DepartmentServiceMapping
from apps.core.context import Context
from config.schema import schema


# --- Helpers ---


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


# --- Fixtures ---


@pytest.fixture
def department(db, tenant):
    return Department.objects.create(tenant=tenant, name="Engineering", sort_order=0)


@pytest.fixture
def department2(db, tenant):
    return Department.objects.create(tenant=tenant, name="Sales & Marketing", sort_order=1)


# --- Department CRUD mutation tests ---


CREATE_DEPT = """
mutation($name: String!) {
  createDepartment(name: $name) { success error }
}
"""

UPDATE_DEPT = """
mutation($id: ID!, $name: String!) {
  updateDepartment(id: $id, name: $name) { success error }
}
"""

DELETE_DEPT = """
mutation($id: ID!) {
  deleteDepartment(id: $id) { success error }
}
"""


@pytest.mark.django_db
class TestDepartmentCrud:

    def test_create_department(self, user):
        result = run_graphql(CREATE_DEPT, {"name": "G&A"}, make_context(user))
        assert result.errors is None
        assert result.data["createDepartment"]["success"] is True
        assert Department.objects.filter(tenant=user.tenant, name="G&A").exists()

    def test_create_rejects_duplicate(self, user, department):
        result = run_graphql(CREATE_DEPT, {"name": "Engineering"}, make_context(user))
        assert result.data["createDepartment"]["success"] is False
        assert "already exists" in result.data["createDepartment"]["error"]

    def test_create_rejects_empty_name(self, user):
        result = run_graphql(CREATE_DEPT, {"name": "  "}, make_context(user))
        assert result.data["createDepartment"]["success"] is False
        assert "required" in result.data["createDepartment"]["error"].lower()

    def test_rename_department(self, user, department):
        result = run_graphql(UPDATE_DEPT, {
            "id": str(department.id), "name": "R&D"
        }, make_context(user))
        assert result.errors is None
        assert result.data["updateDepartment"]["success"] is True
        department.refresh_from_db()
        assert department.name == "R&D"

    def test_rename_rejects_duplicate(self, user, department, department2):
        result = run_graphql(UPDATE_DEPT, {
            "id": str(department.id), "name": "Sales & Marketing"
        }, make_context(user))
        assert result.data["updateDepartment"]["success"] is False
        assert "already exists" in result.data["updateDepartment"]["error"]

    def test_delete_department(self, user, department):
        dept_id = department.id
        result = run_graphql(DELETE_DEPT, {"id": str(dept_id)}, make_context(user))
        assert result.errors is None
        assert result.data["deleteDepartment"]["success"] is True
        assert not Department.objects.filter(id=dept_id).exists()

    def test_delete_cascades_service_mappings(self, user, tenant, department):
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        dept_id = department.id
        run_graphql(DELETE_DEPT, {"id": str(dept_id)}, make_context(user))
        assert not DepartmentServiceMapping.objects.filter(department_id=dept_id).exists()


# --- Service mapping tests ---


SAVE_MAPPINGS = """
mutation($mappings: [DepartmentServiceMappingInput!]!) {
  saveDepartmentServiceMappings(mappings: $mappings) { success error }
}
"""

QUERY_MAPPINGS = """
query {
  departmentServiceMappings {
    id externalServiceId externalServiceName departmentId
  }
}
"""


@pytest.mark.django_db
class TestDepartmentServiceMappings:

    def test_save_mappings(self, user, tenant, department):
        result = run_graphql(SAVE_MAPPINGS, {
            "mappings": [
                {"externalServiceId": "s1", "externalServiceName": "Dev", "departmentId": str(department.id)},
                {"externalServiceId": "s2", "externalServiceName": "Consulting", "departmentId": str(department.id)},
            ]
        }, make_context(user))
        assert result.errors is None
        assert result.data["saveDepartmentServiceMappings"]["success"] is True
        assert DepartmentServiceMapping.objects.filter(tenant=tenant).count() == 2

    def test_save_replaces_existing(self, user, tenant, department, department2):
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Old",
        )
        result = run_graphql(SAVE_MAPPINGS, {
            "mappings": [
                {"externalServiceId": "s3", "externalServiceName": "New", "departmentId": str(department2.id)},
            ]
        }, make_context(user))
        assert result.data["saveDepartmentServiceMappings"]["success"] is True
        assert DepartmentServiceMapping.objects.filter(tenant=tenant).count() == 1
        m = DepartmentServiceMapping.objects.get(tenant=tenant)
        assert m.external_service_id == "s3"
        assert m.department == department2

    def test_save_rejects_invalid_department(self, user):
        result = run_graphql(SAVE_MAPPINGS, {
            "mappings": [
                {"externalServiceId": "s1", "externalServiceName": "Dev", "departmentId": "99999"},
            ]
        }, make_context(user))
        assert result.data["saveDepartmentServiceMappings"]["success"] is False
        assert "Invalid" in result.data["saveDepartmentServiceMappings"]["error"]

    def test_query_mappings(self, user, tenant, department):
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        result = run_graphql(QUERY_MAPPINGS, {}, make_context(user))
        assert result.errors is None
        assert len(result.data["departmentServiceMappings"]) == 1
        assert result.data["departmentServiceMappings"][0]["externalServiceId"] == "s1"


# --- clockodoServices query tests ---


CLOCKODO_SERVICES_QUERY = """
query { clockodoServices { id name } }
"""


@pytest.mark.django_db
class TestClockodoServicesQuery:

    def test_returns_services(self, user):
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_services.return_value = [
                {"id": "1", "name": "Development"},
                {"id": "2", "name": "Consulting"},
            ]
            mock_prov.return_value = provider

            result = run_graphql(CLOCKODO_SERVICES_QUERY, {}, make_context(user))

        assert result.errors is None
        services = result.data["clockodoServices"]
        assert len(services) == 2
        assert services[0]["name"] == "Development"

    def test_returns_empty_when_no_provider(self, user):
        with patch("apps.contracts.services.time_tracking.get_provider", return_value=None):
            result = run_graphql(CLOCKODO_SERVICES_QUERY, {}, make_context(user))
        assert result.errors is None
        assert result.data["clockodoServices"] == []


# --- Department time analysis query tests ---


ANALYSIS_QUERY = """
query($dateFrom: Date!, $dateTo: Date!) {
  departmentTimeAnalysis(dateFrom: $dateFrom, dateTo: $dateTo) {
    totalHours
    distribution { departmentName hours percentage }
    userMatrix {
      userName
      totalHours
      departments { departmentName hours percentage }
    }
  }
}
"""

MOCK_TIME_DATA = [
    {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 100},
    {"user_id": "u1", "user_name": "Alice", "service_id": "s2", "service_name": "Sales", "hours": 20},
    {"user_id": "u2", "user_name": "Bob", "service_id": "s1", "service_name": "Dev", "hours": 60},
    {"user_id": "u2", "user_name": "Bob", "service_id": "s3", "service_name": "Admin", "hours": 40},
]


@pytest.mark.django_db
class TestDepartmentTimeAnalysis:

    def setup_method(self):
        from django.core.cache import cache
        cache.clear()

    def test_distribution_percentages(self, user, tenant, department, department2):
        # s1 (Dev) → Engineering, s2 (Sales) → Sales & Marketing, s3 (Admin) → Unassigned
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department2,
            external_service_id="s2", external_service_name="Sales",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = MOCK_TIME_DATA
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-12-31",
            }, make_context(user))

        assert result.errors is None
        data = result.data["departmentTimeAnalysis"]
        assert data["totalHours"] == 220

        dist = {d["departmentName"]: d for d in data["distribution"]}
        assert dist["Engineering"]["hours"] == 160  # Alice 100 + Bob 60
        assert dist["Sales & Marketing"]["hours"] == 20
        assert dist["Unassigned"]["hours"] == 40  # Bob's admin

        # Percentages should sum to ~100%
        total_pct = sum(d["percentage"] for d in data["distribution"])
        assert 99.5 <= total_pct <= 100.5

    def test_user_matrix(self, user, tenant, department):
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = MOCK_TIME_DATA
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-12-31",
            }, make_context(user))

        matrix = result.data["departmentTimeAnalysis"]["userMatrix"]
        alice = next(r for r in matrix if r["userName"] == "Alice")
        assert alice["totalHours"] == 120  # 100 + 20

        bob = next(r for r in matrix if r["userName"] == "Bob")
        assert bob["totalHours"] == 100  # 60 + 40

    def test_unassigned_services(self, user, tenant):
        # No department mappings at all — everything unassigned
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = [
                {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 50},
            ]
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-12-31",
            }, make_context(user))

        dist = result.data["departmentTimeAnalysis"]["distribution"]
        assert len(dist) == 1
        assert dist[0]["departmentName"] == "Unassigned"
        assert dist[0]["percentage"] == 100.0

    def test_empty_state(self, user):
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = []
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-12-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        assert data["totalHours"] == 0
        assert data["distribution"] == []
        assert data["userMatrix"] == []


# --- Clockodo provider method tests ---


class TestClockodoGetServices:

    def test_get_services(self):
        from apps.contracts.services.clockodo_provider import ClockodoProvider

        provider = ClockodoProvider({"api_email": "test@test.com", "api_key": "key"})
        with patch.object(provider, "_get_all_pages") as mock_pages:
            mock_pages.return_value = [
                {"id": 1, "name": "Development"},
                {"id": 2, "name": "Consulting"},
            ]
            services = provider.get_services()

        assert len(services) == 2
        assert services[0] == {"id": "1", "name": "Development"}
        assert services[1] == {"id": "2", "name": "Consulting"}


class TestClockodoGetDepartmentTimeData:

    def test_returns_user_service_data(self):
        from apps.contracts.services.clockodo_provider import ClockodoProvider

        provider = ClockodoProvider({"api_email": "test@test.com", "api_key": "key"})

        def mock_get(endpoint, params=None):
            if endpoint == "entrygroups":
                return {
                    "groups": [
                        {
                            "group": "101",  # user_id (string in real API)
                            "name": "Alice",
                            "sub_groups": [
                                {"group": "1", "name": "Development", "duration": 36000},  # 10h
                                {"group": "2", "name": "Sales", "duration": 7200},  # 2h
                            ],
                        },
                        {
                            "group": "102",
                            "name": "Bob",
                            "sub_groups": [
                                {"group": "1", "name": "Development", "duration": 18000},  # 5h
                            ],
                        },
                    ]
                }
            return {}

        def mock_get_all_pages(endpoint, key, params=None):
            if endpoint == "users":
                return [{"id": 101, "name": "Alice"}, {"id": 102, "name": "Bob"}]
            if endpoint == "services":
                return [{"id": 1, "name": "Development"}, {"id": 2, "name": "Sales"}]
            return []

        with patch.object(provider, "_get", side_effect=mock_get), \
             patch.object(provider, "_get_all_pages", side_effect=mock_get_all_pages):
            data = provider.get_department_time_data(date(2026, 1, 1), date(2026, 12, 31))

        assert len(data) == 3
        alice_dev = next(d for d in data if d["user_name"] == "Alice" and d["service_name"] == "Development")
        assert alice_dev["hours"] == 10.0

        bob_dev = next(d for d in data if d["user_name"] == "Bob" and d["service_name"] == "Development")
        assert bob_dev["hours"] == 5.0
