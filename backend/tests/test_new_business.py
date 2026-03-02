"""Tests for deal won date, new business metrics, and new business goals."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import Contract, ContractItem, NewBusinessGoal
from apps.contracts.schema import calculate_new_business_metrics
from apps.customers.models import Customer
from apps.products.models import Product
from apps.tenants.models import Role, Tenant, User
from apps.core.context import Context


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
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


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(tenant=tenant, name="Test Customer", is_active=True)


@pytest.fixture
def won_contract(tenant, customer):
    """A HubSpot-imported contract won in 2026."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Won Deal 2026",
        hubspot_deal_id="hs-123",
        deal_won_date=date(2026, 3, 15),
        start_date=date(2026, 4, 1),
        billing_start_date=date(2026, 4, 1),
        status=Contract.Status.ACTIVE,
    )


@pytest.fixture
def existing_contract(tenant, customer):
    """A manually created contract (no HubSpot)."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Existing Contract",
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        status=Contract.Status.ACTIVE,
    )


@pytest.mark.django_db
class TestDealWonDate:
    def test_is_new_business_with_hubspot(self, won_contract):
        assert won_contract.is_new_business is True

    def test_is_new_business_without_hubspot(self, existing_contract):
        assert existing_contract.is_new_business is False

    def test_deal_won_date_stored(self, won_contract):
        assert won_contract.deal_won_date == date(2026, 3, 15)

    def test_deal_won_date_nullable(self, existing_contract):
        assert existing_contract.deal_won_date is None


@pytest.mark.django_db
class TestDealWonDateGraphQL:
    QUERY = """
        query Contract($id: ID!) {
            contract(id: $id) {
                id
                dealWonDate
                isNewBusiness
            }
        }
    """

    def test_query_returns_deal_won_date(self, user, won_contract):
        ctx = make_context(user)
        result = run_graphql(self.QUERY, {"id": str(won_contract.id)}, ctx)
        assert result.errors is None
        assert result.data["contract"]["dealWonDate"] == "2026-03-15"
        assert result.data["contract"]["isNewBusiness"] is True

    def test_query_returns_null_for_existing(self, user, existing_contract):
        ctx = make_context(user)
        result = run_graphql(self.QUERY, {"id": str(existing_contract.id)}, ctx)
        assert result.errors is None
        assert result.data["contract"]["dealWonDate"] is None
        assert result.data["contract"]["isNewBusiness"] is False

    def test_update_deal_won_date(self, user, won_contract):
        mutation = """
            mutation UpdateContract($input: UpdateContractInput!) {
                updateContract(input: $input) {
                    success
                    contract { dealWonDate }
                }
            }
        """
        ctx = make_context(user)
        result = run_graphql(mutation, {
            "input": {"id": str(won_contract.id), "dealWonDate": "2026-06-01"}
        }, ctx)
        assert result.errors is None
        assert result.data["updateContract"]["success"] is True
        assert result.data["updateContract"]["contract"]["dealWonDate"] == "2026-06-01"


@pytest.mark.django_db
class TestCalculateNewBusinessMetrics:
    def test_won_new_arr(self, tenant, won_contract):
        ContractItem.objects.create(
            tenant=tenant,
            contract=won_contract,
            description="Monthly SaaS",
            quantity=1,
            unit_price=Decimal("1000"),
            price_period="monthly",
            is_one_off=False,
        )
        metrics = calculate_new_business_metrics(tenant, 2026)
        assert metrics["won_new_arr"] == Decimal("12000")
        assert metrics["won_deal_count"] == 1

    def test_won_development_revenue(self, tenant, customer):
        product = Product.objects.create(
            tenant=tenant,
            name="Dev Project",
            revenue_type="advanced_development",
        )
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Dev Deal",
            hubspot_deal_id="hs-dev",
            deal_won_date=date(2026, 5, 1),
            start_date=date(2026, 5, 1),
            billing_start_date=date(2026, 5, 1),
            status=Contract.Status.ACTIVE,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            description="Development work",
            quantity=1,
            unit_price=Decimal("50000"),
            price_period="monthly",
            is_one_off=True,
        )
        metrics = calculate_new_business_metrics(tenant, 2026)
        assert metrics["won_development_revenue"] == Decimal("50000")

    def test_excludes_draft_contracts(self, tenant, customer):
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Draft Deal",
            hubspot_deal_id="hs-draft",
            deal_won_date=date(2026, 2, 1),
            start_date=date(2026, 2, 1),
            billing_start_date=date(2026, 2, 1),
            status=Contract.Status.DRAFT,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Item",
            quantity=1,
            unit_price=Decimal("5000"),
            price_period="monthly",
        )
        metrics = calculate_new_business_metrics(tenant, 2026)
        assert metrics["won_deal_count"] == 0
        assert metrics["won_new_arr"] == Decimal("0")

    def test_excludes_cancelled_contracts(self, tenant, customer):
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Cancelled Deal",
            hubspot_deal_id="hs-cancel",
            deal_won_date=date(2026, 2, 1),
            start_date=date(2026, 2, 1),
            billing_start_date=date(2026, 2, 1),
            status=Contract.Status.CANCELLED,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Item",
            quantity=1,
            unit_price=Decimal("5000"),
            price_period="monthly",
        )
        metrics = calculate_new_business_metrics(tenant, 2026)
        assert metrics["won_deal_count"] == 0
        assert metrics["won_new_arr"] == Decimal("0")

    def test_excludes_non_hubspot(self, tenant, existing_contract):
        ContractItem.objects.create(
            tenant=tenant,
            contract=existing_contract,
            description="Item",
            quantity=1,
            unit_price=Decimal("5000"),
            price_period="monthly",
        )
        metrics = calculate_new_business_metrics(tenant, 2026)
        assert metrics["won_deal_count"] == 0

    def test_excludes_wrong_year(self, tenant, customer):
        Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Old Deal",
            hubspot_deal_id="hs-old",
            deal_won_date=date(2025, 6, 1),
            start_date=date(2025, 6, 1),
            billing_start_date=date(2025, 6, 1),
            status=Contract.Status.ACTIVE,
        )
        metrics = calculate_new_business_metrics(tenant, 2026)
        assert metrics["won_deal_count"] == 0


@pytest.mark.django_db
class TestNewBusinessGoalsGraphQL:
    SET_MUTATION = """
        mutation SetNewBusinessGoal($year: Int!, $goalType: String!, $targetAmount: Decimal!) {
            setNewBusinessGoal(year: $year, goalType: $goalType, targetAmount: $targetAmount) {
                success
                error
                goal { id year goalType targetAmount }
            }
        }
    """

    DELETE_MUTATION = """
        mutation DeleteNewBusinessGoal($year: Int!, $goalType: String!) {
            deleteNewBusinessGoal(year: $year, goalType: $goalType) {
                success
                error
            }
        }
    """

    QUERY = """
        query NewBusinessGoals($year: Int!) {
            newBusinessGoals(year: $year) {
                id year goalType targetAmount
            }
        }
    """

    def test_create_goal(self, user):
        ctx = make_context(user)
        result = run_graphql(self.SET_MUTATION, {
            "year": 2026, "goalType": "new_arr", "targetAmount": "200000"
        }, ctx)
        assert result.errors is None
        assert result.data["setNewBusinessGoal"]["success"] is True
        assert result.data["setNewBusinessGoal"]["goal"]["goalType"] == "new_arr"

    def test_upsert_goal(self, user, tenant):
        NewBusinessGoal.objects.create(
            tenant=tenant, year=2026, goal_type="new_arr", target_amount=Decimal("100000")
        )
        ctx = make_context(user)
        result = run_graphql(self.SET_MUTATION, {
            "year": 2026, "goalType": "new_arr", "targetAmount": "200000"
        }, ctx)
        assert result.errors is None
        assert result.data["setNewBusinessGoal"]["success"] is True
        assert Decimal(result.data["setNewBusinessGoal"]["goal"]["targetAmount"]) == Decimal("200000")
        assert NewBusinessGoal.objects.filter(tenant=tenant, year=2026, goal_type="new_arr").count() == 1

    def test_invalid_goal_type(self, user):
        ctx = make_context(user)
        result = run_graphql(self.SET_MUTATION, {
            "year": 2026, "goalType": "invalid", "targetAmount": "100000"
        }, ctx)
        assert result.errors is None
        assert result.data["setNewBusinessGoal"]["success"] is False
        assert "Invalid goal type" in result.data["setNewBusinessGoal"]["error"]

    def test_delete_goal(self, user, tenant):
        NewBusinessGoal.objects.create(
            tenant=tenant, year=2026, goal_type="new_arr", target_amount=Decimal("100000")
        )
        ctx = make_context(user)
        result = run_graphql(self.DELETE_MUTATION, {
            "year": 2026, "goalType": "new_arr"
        }, ctx)
        assert result.errors is None
        assert result.data["deleteNewBusinessGoal"]["success"] is True
        assert not NewBusinessGoal.objects.filter(tenant=tenant, year=2026, goal_type="new_arr").exists()

    def test_query_goals(self, user, tenant):
        NewBusinessGoal.objects.create(
            tenant=tenant, year=2026, goal_type="new_arr", target_amount=Decimal("200000")
        )
        NewBusinessGoal.objects.create(
            tenant=tenant, year=2026, goal_type="new_deal_count", target_amount=Decimal("10")
        )
        ctx = make_context(user)
        result = run_graphql(self.QUERY, {"year": 2026}, ctx)
        assert result.errors is None
        assert len(result.data["newBusinessGoals"]) == 2


@pytest.mark.django_db
class TestNewBusinessMetricsQuery:
    QUERY = """
        query NewBusinessMetrics($year: Int!) {
            newBusinessMetrics(year: $year) {
                wonNewArr
                wonDevelopmentRevenue
                wonDealCount
            }
        }
    """

    def test_query_returns_metrics(self, user, tenant, won_contract):
        ContractItem.objects.create(
            tenant=tenant,
            contract=won_contract,
            description="Monthly",
            quantity=1,
            unit_price=Decimal("500"),
            price_period="monthly",
        )
        ctx = make_context(user)
        result = run_graphql(self.QUERY, {"year": 2026}, ctx)
        assert result.errors is None
        data = result.data["newBusinessMetrics"]
        assert data["wonDealCount"] == 1
        assert Decimal(data["wonNewArr"]) == Decimal("6000")


@pytest.mark.django_db
class TestWonDealsQuery:
    QUERY = """
        query WonDeals($year: Int!) {
            wonDeals(year: $year) {
                contractId contractName customerName dealWonDate annualRecurringRevenue
            }
        }
    """

    def test_query_returns_won_deals(self, user, tenant, won_contract):
        ContractItem.objects.create(
            tenant=tenant,
            contract=won_contract,
            description="Monthly SaaS",
            quantity=1,
            unit_price=Decimal("1000"),
            price_period="monthly",
        )
        ctx = make_context(user)
        result = run_graphql(self.QUERY, {"year": 2026}, ctx)
        assert result.errors is None
        deals = result.data["wonDeals"]
        assert len(deals) == 1
        assert deals[0]["contractName"] == "Won Deal 2026"
        assert deals[0]["dealWonDate"] == "2026-03-15"
        assert Decimal(deals[0]["annualRecurringRevenue"]) == Decimal("12000")
