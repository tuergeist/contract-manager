"""Tests for department time analysis: CRUD, service mapping, and analysis query."""
import pytest
from datetime import date
from unittest.mock import Mock, patch

from apps.contracts.models import Department, DepartmentServiceMapping, UserCostProfile
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


# --- UserCostProfile model tests ---


@pytest.mark.django_db
class TestUserCostProfileModel:

    def test_create_cost_profile(self, tenant, department):
        profile = UserCostProfile.objects.create(
            tenant=tenant,
            external_user_id="u1",
            external_user_name="Alice",
            fte_percentage=100,
            monthly_income=5000,
            default_department=department,
        )
        assert profile.external_user_id == "u1"
        assert profile.fte_percentage == 100
        assert float(profile.monthly_income) == 5000.0
        assert profile.default_department == department

    def test_unique_constraint(self, tenant):
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
        )
        with pytest.raises(Exception):
            UserCostProfile.objects.create(
                tenant=tenant, external_user_id="u1", external_user_name="Alice Dup",
            )

    def test_default_department_set_null(self, tenant, department):
        profile = UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            default_department=department,
        )
        department.delete()
        profile.refresh_from_db()
        assert profile.default_department is None


# --- clockodoUsers query and saveUserCostProfiles mutation tests ---


CLOCKODO_USERS_QUERY = """
query { clockodoUsers { id name } }
"""

USER_COST_PROFILES_QUERY = """
query { userCostProfiles { id externalUserId externalUserName ftePercentage monthlyIncome defaultDepartmentId } }
"""

SAVE_COST_PROFILES = """
mutation($profiles: [UserCostProfileInput!]!) {
  saveUserCostProfiles(profiles: $profiles) { success error }
}
"""


@pytest.mark.django_db
class TestClockodoUsersQuery:

    def test_returns_users(self, user):
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_users.return_value = [
                {"id": "101", "name": "Alice"},
                {"id": "102", "name": "Bob"},
            ]
            mock_prov.return_value = provider

            result = run_graphql(CLOCKODO_USERS_QUERY, {}, make_context(user))

        assert result.errors is None
        users = result.data["clockodoUsers"]
        assert len(users) == 2
        assert users[0]["name"] == "Alice"

    def test_returns_empty_when_no_provider(self, user):
        with patch("apps.contracts.services.time_tracking.get_provider", return_value=None):
            result = run_graphql(CLOCKODO_USERS_QUERY, {}, make_context(user))
        assert result.errors is None
        assert result.data["clockodoUsers"] == []


@pytest.mark.django_db
class TestUserCostProfilesMutation:

    def test_save_profiles(self, user, tenant, department):
        result = run_graphql(SAVE_COST_PROFILES, {
            "profiles": [
                {
                    "externalUserId": "u1",
                    "externalUserName": "Alice",
                    "ftePercentage": 100,
                    "monthlyIncome": 5000.0,
                    "defaultDepartmentId": str(department.id),
                },
                {
                    "externalUserId": "u2",
                    "externalUserName": "Bob",
                    "ftePercentage": 50,
                    "monthlyIncome": 2500.0,
                },
            ]
        }, make_context(user))
        assert result.errors is None
        assert result.data["saveUserCostProfiles"]["success"] is True
        assert UserCostProfile.objects.filter(tenant=tenant).count() == 2

    def test_save_replaces_existing(self, user, tenant, department):
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Old",
        )
        result = run_graphql(SAVE_COST_PROFILES, {
            "profiles": [
                {
                    "externalUserId": "u2",
                    "externalUserName": "New",
                    "ftePercentage": 80,
                    "monthlyIncome": 4000.0,
                },
            ]
        }, make_context(user))
        assert result.data["saveUserCostProfiles"]["success"] is True
        assert UserCostProfile.objects.filter(tenant=tenant).count() == 1
        p = UserCostProfile.objects.get(tenant=tenant)
        assert p.external_user_id == "u2"

    def test_save_rejects_invalid_department(self, user):
        result = run_graphql(SAVE_COST_PROFILES, {
            "profiles": [
                {
                    "externalUserId": "u1",
                    "externalUserName": "Alice",
                    "ftePercentage": 100,
                    "monthlyIncome": 5000.0,
                    "defaultDepartmentId": "99999",
                },
            ]
        }, make_context(user))
        assert result.data["saveUserCostProfiles"]["success"] is False
        assert "Invalid" in result.data["saveUserCostProfiles"]["error"]

    def test_query_profiles(self, user, tenant, department):
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=5000, default_department=department,
        )
        result = run_graphql(USER_COST_PROFILES_QUERY, {}, make_context(user))
        assert result.errors is None
        profiles = result.data["userCostProfiles"]
        assert len(profiles) == 1
        assert profiles[0]["externalUserId"] == "u1"
        assert profiles[0]["ftePercentage"] == 100
        assert profiles[0]["monthlyIncome"] == 5000.0
        assert profiles[0]["defaultDepartmentId"] == str(department.id)


# --- Hour backfilling and cost analysis tests ---


ANALYSIS_WITH_COST_QUERY = """
query($dateFrom: Date!, $dateTo: Date!) {
  departmentTimeAnalysis(dateFrom: $dateFrom, dateTo: $dateTo) {
    totalHours
    totalHoursFilled
    distribution { departmentName hours percentage }
    distributionFilled { departmentName hours percentage }
    userMatrix {
      userName
      totalHours
      absenceDays
      departments { departmentName hours percentage }
    }
    userMatrixFilled {
      userName
      totalHours
      absenceDays
      departments { departmentName hours percentage }
    }
    costDistribution { departmentName cost percentage ftes }
    totalCost
  }
}
"""


@pytest.mark.django_db
class TestHourBackfilling:

    def setup_method(self):
        from django.core.cache import cache
        cache.clear()

    def test_backfill_partial_hours(self, user, tenant, department, department2):
        """User with FTE 100% and 100h logged → 68h backfilled to default dept."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=5000,
            default_department=department2,  # Sales & Marketing
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 100},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        assert result.errors is None
        data = result.data["departmentTimeAnalysis"]
        # Unfilled total shows raw logged hours
        assert data["totalHours"] == 100.0
        # Filled total includes backfilled hours
        assert data["totalHoursFilled"] == 168.0

        # Unfilled distribution shows only logged hours
        dist = {d["departmentName"]: d for d in data["distribution"]}
        assert dist["Engineering"]["hours"] == 100.0
        assert dist["Sales & Marketing"]["hours"] == 0.0  # no logged hours in S&M

        # Filled distribution includes backfilled hours
        dist_filled = {d["departmentName"]: d for d in data["distributionFilled"]}
        assert dist_filled["Engineering"]["hours"] == 100.0
        assert dist_filled["Sales & Marketing"]["hours"] == 68.0

        # Unfilled user matrix shows raw logged hours
        alice = next(r for r in data["userMatrix"] if r["userName"] == "Alice")
        assert alice["totalHours"] == 100.0

        # Filled user matrix shows backfilled hours
        alice_filled = next(r for r in data["userMatrixFilled"] if r["userName"] == "Alice")
        assert alice_filled["totalHours"] == 168.0

    def test_no_backfill_when_hours_exceed_target(self, user, tenant, department):
        """User with FTE 100% and 180h logged → no backfill, keep actual 180h."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=5000, default_department=department,
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 180},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        assert data["totalHours"] == 180.0  # No backfill

    def test_no_backfill_without_default_department(self, user, tenant, department):
        """User with cost profile but no default dept → no backfill."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=5000,
            # No default_department
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 100},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        assert data["totalHours"] == 100.0  # No backfill

    def test_no_backfill_without_profile(self, user, tenant, department):
        """User without any cost profile → no backfill (backwards compatible)."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        # No UserCostProfile created

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 80},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        assert data["totalHours"] == 80.0

    def test_backfill_part_time_user(self, user, tenant, department):
        """User with FTE 50% and 60h logged → 24h backfilled (target=84h)."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=50, monthly_income=2500, default_department=department,
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 60},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        assert data["totalHours"] == 60.0  # raw logged
        assert data["totalHoursFilled"] == 84.0  # 60 + 24 backfilled


@pytest.mark.django_db
class TestCostComputation:

    def setup_method(self):
        from django.core.cache import cache
        cache.clear()

    def test_cost_distribution(self, user, tenant, department, department2):
        """Two users with different incomes → cost differs from hour share."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department2,
            external_service_id="s2", external_service_name="Sales",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=8400, default_department=department,
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u2", external_user_name="Bob",
            fte_percentage=100, monthly_income=4200, default_department=department2,
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 168},
            {"user_id": "u2", "user_name": "Bob", "service_id": "s2", "service_name": "Sales", "hours": 168},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        assert result.errors is None
        data = result.data["departmentTimeAnalysis"]

        # Alice: 8400/168 = 50/h * 168h = 8400
        # Bob: 4200/168 = 25/h * 168h = 4200
        assert data["totalCost"] == 12600.0

        cost_dist = {d["departmentName"]: d for d in data["costDistribution"]}
        # Engineering (Alice): 8400 / 12600 = 66.7%
        assert abs(cost_dist["Engineering"]["cost"] - 8400.0) < 0.01
        assert abs(cost_dist["Engineering"]["percentage"] - 66.7) < 0.1
        # Sales & Marketing (Bob): 4200 / 12600 = 33.3%
        assert abs(cost_dist["Sales & Marketing"]["cost"] - 4200.0) < 0.01
        assert abs(cost_dist["Sales & Marketing"]["percentage"] - 33.3) < 0.1

        # FTE: Alice 100% all in Engineering, Bob 100% all in Sales
        assert cost_dist["Engineering"]["ftes"] == 1.0
        assert cost_dist["Sales & Marketing"]["ftes"] == 1.0

    def test_zero_income_excluded(self, user, tenant, department):
        """User with zero income → excluded from cost analysis."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=0, default_department=department,
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 168},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        assert data["costDistribution"] is None
        assert data["totalCost"] is None

    def test_cost_with_backfilled_hours(self, user, tenant, department, department2):
        """Cost computed on backfilled hours, not just logged hours."""
        DepartmentServiceMapping.objects.create(
            tenant=tenant, department=department,
            external_service_id="s1", external_service_name="Dev",
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="Alice",
            fte_percentage=100, monthly_income=8400,
            default_department=department2,  # backfill to Sales & Marketing
        )

        mock_data = [
            {"user_id": "u1", "user_name": "Alice", "service_id": "s1", "service_name": "Dev", "hours": 100},
        ]

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_prov:
            provider = Mock()
            provider.get_department_time_data.return_value = mock_data
            mock_prov.return_value = provider

            result = run_graphql(ANALYSIS_WITH_COST_QUERY, {
                "dateFrom": "2026-01-01", "dateTo": "2026-01-31",
            }, make_context(user))

        data = result.data["departmentTimeAnalysis"]
        # hourly cost = 8400 / 168 = 50/h
        # Engineering: 50 * 100 = 5000
        # Sales & Marketing (backfill): 50 * 68 = 3400
        assert data["totalCost"] == 8400.0
        cost_dist = {d["departmentName"]: d for d in data["costDistribution"]}
        assert abs(cost_dist["Engineering"]["cost"] - 5000.0) < 0.01
        assert abs(cost_dist["Sales & Marketing"]["cost"] - 3400.0) < 0.01


# --- Clockodo get_users provider test ---


class TestClockodoGetUsers:

    def test_get_users(self):
        from apps.contracts.services.clockodo_provider import ClockodoProvider

        provider = ClockodoProvider({"api_email": "test@test.com", "api_key": "key"})
        with patch.object(provider, "_get_all_pages") as mock_pages:
            mock_pages.return_value = [
                {"id": 101, "name": "Alice"},
                {"id": 102, "name": "Bob"},
            ]
            users = provider.get_users()

        assert len(users) == 2
        assert users[0] == {"id": "101", "name": "Alice"}
        assert users[1] == {"id": "102", "name": "Bob"}
