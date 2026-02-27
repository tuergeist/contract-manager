"""Tests for revenue goals CRUD via GraphQL."""
import pytest
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import RevenueGoal
from apps.core.models import RevenueType
from apps.tenants.models import Role, Tenant, User
from apps.core.context import Context


def run_graphql(query, variables, context):
    """Helper to run GraphQL queries synchronously."""
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    """Create a proper Context object for GraphQL testing."""
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


REVENUE_GOALS_QUERY = """
    query RevenueGoals($year: Int!) {
        revenueGoals(year: $year) {
            id
            year
            revenueType
            targetAmount
        }
    }
"""

SET_REVENUE_GOAL_MUTATION = """
    mutation SetRevenueGoal($year: Int!, $revenueType: String!, $targetAmount: Decimal!) {
        setRevenueGoal(year: $year, revenueType: $revenueType, targetAmount: $targetAmount) {
            success
            error
            goal {
                id
                year
                revenueType
                targetAmount
            }
        }
    }
"""

DELETE_REVENUE_GOAL_MUTATION = """
    mutation DeleteRevenueGoal($year: Int!, $revenueType: String!) {
        deleteRevenueGoal(year: $year, revenueType: $revenueType) {
            success
            error
        }
    }
"""


class TestRevenueGoalsQuery:
    def test_returns_goals_for_year(self, user, tenant):
        RevenueGoal.objects.create(
            tenant=tenant, year=2026, revenue_type=RevenueType.RECURRING,
            target_amount=Decimal("500000.00"),
        )
        RevenueGoal.objects.create(
            tenant=tenant, year=2026, revenue_type=RevenueType.ADVANCED_DEVELOPMENT,
            target_amount=Decimal("200000.00"),
        )
        # Different year — should not appear
        RevenueGoal.objects.create(
            tenant=tenant, year=2025, revenue_type=RevenueType.RECURRING,
            target_amount=Decimal("400000.00"),
        )

        result = run_graphql(REVENUE_GOALS_QUERY, {"year": 2026}, make_context(user))
        assert result.errors is None
        goals = result.data["revenueGoals"]
        assert len(goals) == 2
        types = {g["revenueType"] for g in goals}
        assert types == {"recurring", "advanced_development"}

    def test_returns_empty_for_year_without_goals(self, user, tenant):
        result = run_graphql(REVENUE_GOALS_QUERY, {"year": 2030}, make_context(user))
        assert result.errors is None
        assert result.data["revenueGoals"] == []


class TestSetRevenueGoalMutation:
    def test_create_new_goal(self, user, tenant):
        result = run_graphql(
            SET_REVENUE_GOAL_MUTATION,
            {"year": 2026, "revenueType": "recurring", "targetAmount": "600000.00"},
            make_context(user),
        )
        assert result.errors is None
        data = result.data["setRevenueGoal"]
        assert data["success"] is True
        assert data["goal"]["year"] == 2026
        assert data["goal"]["revenueType"] == "recurring"
        assert float(data["goal"]["targetAmount"]) == 600000.00

        # Verify in DB
        assert RevenueGoal.objects.filter(tenant=tenant, year=2026).count() == 1

    def test_upsert_existing_goal(self, user, tenant):
        RevenueGoal.objects.create(
            tenant=tenant, year=2026, revenue_type=RevenueType.RECURRING,
            target_amount=Decimal("500000.00"),
        )

        result = run_graphql(
            SET_REVENUE_GOAL_MUTATION,
            {"year": 2026, "revenueType": "recurring", "targetAmount": "750000.00"},
            make_context(user),
        )
        assert result.errors is None
        data = result.data["setRevenueGoal"]
        assert data["success"] is True
        assert float(data["goal"]["targetAmount"]) == 750000.00

        # Should still be exactly 1 record (upsert, not insert)
        assert RevenueGoal.objects.filter(
            tenant=tenant, year=2026, revenue_type="recurring",
        ).count() == 1

    def test_invalid_revenue_type(self, user, tenant):
        result = run_graphql(
            SET_REVENUE_GOAL_MUTATION,
            {"year": 2026, "revenueType": "invalid_type", "targetAmount": "100000.00"},
            make_context(user),
        )
        assert result.errors is None
        data = result.data["setRevenueGoal"]
        assert data["success"] is False
        assert "Invalid revenue type" in data["error"]


class TestDeleteRevenueGoalMutation:
    def test_delete_existing_goal(self, user, tenant):
        RevenueGoal.objects.create(
            tenant=tenant, year=2026, revenue_type=RevenueType.RECURRING,
            target_amount=Decimal("500000.00"),
        )

        result = run_graphql(
            DELETE_REVENUE_GOAL_MUTATION,
            {"year": 2026, "revenueType": "recurring"},
            make_context(user),
        )
        assert result.errors is None
        data = result.data["deleteRevenueGoal"]
        assert data["success"] is True
        assert RevenueGoal.objects.filter(tenant=tenant, year=2026).count() == 0

    def test_delete_nonexistent_goal(self, user, tenant):
        result = run_graphql(
            DELETE_REVENUE_GOAL_MUTATION,
            {"year": 2026, "revenueType": "recurring"},
            make_context(user),
        )
        assert result.errors is None
        data = result.data["deleteRevenueGoal"]
        assert data["success"] is False
        assert "not found" in data["error"]
