"""Tests for revenue_forecast and recognition_forecast GraphQL resolvers."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product
from apps.tenants.models import Role, Tenant, User
from apps.core.context import Context


def run_graphql(query, variables, context):
    """Helper to run GraphQL queries synchronously."""
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    """Create a proper Context object for GraphQL testing."""
    request = Mock()
    return Context(request=request, user=user)


# ---------------------------------------------------------------------------
# GraphQL query strings
# ---------------------------------------------------------------------------

REVENUE_FORECAST_QUERY = """
    query RevenueForecast(
        $months: Int,
        $quarters: Int,
        $view: String,
        $proRata: Boolean,
        $excludeOneOff: Boolean,
        $refresh: Boolean
    ) {
        revenueForecast(
            months: $months,
            quarters: $quarters,
            view: $view,
            proRata: $proRata,
            excludeOneOff: $excludeOneOff,
            refresh: $refresh
        ) {
            monthColumns
            monthlyTotals { month amount }
            contracts {
                contractId
                contractName
                customerId
                customerName
                customerNumber
                months { month amount invoiceStatus }
                total
            }
            grandTotal
            error
        }
    }
"""

RECOGNITION_FORECAST_QUERY = """
    query RecognitionForecast(
        $months: Int,
        $quarters: Int,
        $view: String,
        $proRata: Boolean,
        $excludeOneOff: Boolean,
        $refresh: Boolean
    ) {
        recognitionForecast(
            months: $months,
            quarters: $quarters,
            view: $view,
            proRata: $proRata,
            excludeOneOff: $excludeOneOff,
            refresh: $refresh
        ) {
            monthColumns
            monthlyTotals { month amount }
            contracts {
                contractId
                contractName
                customerId
                customerName
                customerNumber
                months { month amount invoiceStatus }
                total
            }
            grandTotal
            error
        }
    }
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Company",
        currency="EUR",
    )


@pytest.fixture
def user(db, tenant):
    """Create a test user with Admin role (full permissions)."""
    u = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def user_no_perms(db, tenant):
    """Create a test user without any roles (no permissions)."""
    return User.objects.create_user(
        email="noperm@example.com",
        password="testpass123",
        tenant=tenant,
    )


@pytest.fixture
def customer(db, tenant):
    """Create a test customer without netsuite_customer_number."""
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
    )


@pytest.fixture
def customer_with_number(db, tenant):
    """Create a test customer with netsuite_customer_number."""
    return Customer.objects.create(
        tenant=tenant,
        name="NetSuite Customer",
        is_active=True,
        netsuite_customer_number="CUS174",
    )


@pytest.fixture
def product(db, tenant):
    """Create a test product."""
    return Product.objects.create(
        tenant=tenant,
        name="Test Product",
        sku="TEST-001",
    )


@pytest.fixture
def active_contract(db, tenant, customer):
    """Create an active monthly contract starting Jan 1 of the current year."""
    today = date.today()
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Active Monthly",
        status=Contract.Status.ACTIVE,
        start_date=date(today.year, 1, 1),
        billing_start_date=date(today.year, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def active_contract_with_item(db, active_contract, product):
    """Add a recurring item to the active contract and return the contract."""
    ContractItem.objects.create(
        tenant=active_contract.tenant,
        contract=active_contract,
        product=product,
        quantity=1,
        unit_price=Decimal("1000.00"),
        price_period="monthly",
        billing_start_date=active_contract.billing_start_date,
    )
    return active_contract


# ---------------------------------------------------------------------------
# Tests: Revenue Forecast
# ---------------------------------------------------------------------------


class TestRevenueForecastMonthlyView:
    """Test revenue_forecast with monthly view."""

    def test_returns_correct_month_columns_default(self, user, active_contract_with_item):
        """Monthly view defaults to 13 months starting from January of the current year."""
        today = date.today()
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        assert data["error"] is None

        columns = data["monthColumns"]
        assert len(columns) == 13
        # First column is January of the current year
        assert columns[0] == f"{today.year}-01"
        # Last column is January of the next year
        assert columns[-1] == f"{today.year + 1}-01"

    def test_returns_correct_month_columns_custom_count(self, user, active_contract_with_item):
        """Custom months parameter controls the number of columns."""
        today = date.today()
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        columns = data["monthColumns"]
        assert len(columns) == 6
        assert columns[0] == f"{today.year}-01"

    def test_contract_appears_with_revenue(self, user, active_contract_with_item):
        """Active contract with a recurring item produces revenue rows."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contracts = data["contracts"]
        assert len(contracts) >= 1

        row = next(c for c in contracts if c["contractId"] == active_contract_with_item.id)
        assert row["contractName"] == "Active Monthly"
        assert row["customerName"] == "Test Customer"
        # Monthly billing at 1000/month => each month has 1000
        for m in row["months"]:
            assert Decimal(m["amount"]) == Decimal("1000.00")
        assert Decimal(row["total"]) == Decimal("3000.00")

    def test_grand_total_equals_sum_of_monthly_totals(self, user, active_contract_with_item):
        """grandTotal must equal the sum of all monthlyTotals amounts."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        sum_totals = sum(Decimal(t["amount"]) for t in data["monthlyTotals"])
        assert Decimal(data["grandTotal"]) == sum_totals

    def test_grand_total_equals_sum_of_contract_totals(self, user, active_contract_with_item):
        """grandTotal must also equal the sum of all per-contract totals."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        sum_contract_totals = sum(Decimal(c["total"]) for c in data["contracts"])
        assert Decimal(data["grandTotal"]) == sum_contract_totals


class TestRevenueForecastQuarterlyView:
    """Test revenue_forecast with quarterly view."""

    def test_returns_correct_quarter_columns_default(self, user, active_contract_with_item):
        """Quarterly view defaults to 6 quarters starting from Q1 of the current year."""
        today = date.today()
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "quarterly", "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        columns = data["monthColumns"]
        assert len(columns) == 6
        assert columns[0] == f"{today.year}-Q1"
        assert columns[1] == f"{today.year}-Q2"
        assert columns[2] == f"{today.year}-Q3"
        assert columns[3] == f"{today.year}-Q4"
        assert columns[4] == f"{today.year + 1}-Q1"
        assert columns[5] == f"{today.year + 1}-Q2"

    def test_returns_correct_quarter_columns_custom_count(self, user, active_contract_with_item):
        """Custom quarters parameter controls the number of quarter columns."""
        today = date.today()
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "quarterly", "quarters": 4, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        columns = data["monthColumns"]
        assert len(columns) == 4
        assert columns[0] == f"{today.year}-Q1"
        assert columns[3] == f"{today.year}-Q4"

    def test_quarterly_revenue_aggregation(self, user, active_contract_with_item):
        """Monthly billing amounts are aggregated into quarterly buckets."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "quarterly", "quarters": 4, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contracts = data["contracts"]
        assert len(contracts) >= 1

        row = next(c for c in contracts if c["contractId"] == active_contract_with_item.id)
        # Monthly billing at 1000/month => each quarter has 3 billing events = 3000
        for m in row["months"]:
            assert Decimal(m["amount"]) == Decimal("3000.00")


class TestRevenueForecastCustomerNumber:
    """Test that customer_number is populated from Customer.netsuite_customer_number."""

    def test_customer_with_netsuite_number(self, user, tenant, customer_with_number, product):
        """Contracts whose customer has netsuite_customer_number populate customerNumber."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer_with_number,
            name="NetSuite Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=contract.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)
        assert row["customerNumber"] == "CUS174"

    def test_customer_without_netsuite_number(self, user, active_contract_with_item):
        """Contracts whose customer lacks netsuite_customer_number return null."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == active_contract_with_item.id)
        assert row["customerNumber"] is None


class TestRevenueForecastStatusFiltering:
    """Test that only ACTIVE and PAUSED contracts appear in the forecast."""

    def test_active_contract_included(self, user, active_contract_with_item):
        """Active contracts appear in the forecast."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert active_contract_with_item.id in contract_ids

    def test_paused_contract_included(self, user, tenant, customer, product):
        """Paused contracts appear in the forecast."""
        today = date.today()
        paused = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Paused Contract",
            status=Contract.Status.PAUSED,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=paused,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=paused.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert paused.id in contract_ids

    def test_draft_contract_excluded(self, user, tenant, customer, product):
        """Draft contracts must not appear in the forecast."""
        today = date.today()
        draft = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Draft Contract",
            status=Contract.Status.DRAFT,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=draft,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=draft.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert draft.id not in contract_ids

    def test_cancelled_contract_excluded(self, user, tenant, customer, product):
        """Cancelled contracts must not appear in the forecast."""
        today = date.today()
        cancelled = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Cancelled Contract",
            status=Contract.Status.CANCELLED,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=cancelled,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=cancelled.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert cancelled.id not in contract_ids

    def test_ended_contract_excluded(self, user, tenant, customer, product):
        """Contracts with end_date before the forecast start are excluded."""
        today = date.today()
        ended = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Ended Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year - 2, 1, 1),
            end_date=date(today.year - 1, 6, 30),  # Ended well before this year
            billing_start_date=date(today.year - 2, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=ended,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=ended.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert ended.id not in contract_ids


class TestRevenueForecastExcludeOneOff:
    """Test the excludeOneOff filter."""

    def test_exclude_one_off_true_filters_one_off_items(self, user, tenant, customer, product):
        """With excludeOneOff=true, contracts with only one-off items are excluded."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="One-Off Only",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("5000.00"),
            price_period="monthly",
            is_one_off=True,
            billing_start_date=date(today.year, 3, 1),
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "excludeOneOff": True, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert contract.id not in contract_ids

    def test_exclude_one_off_false_includes_one_off_items(self, user, tenant, customer, product):
        """With excludeOneOff=false (default), one-off items are included."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="One-Off Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("5000.00"),
            price_period="monthly",
            is_one_off=True,
            billing_start_date=date(today.year, 3, 1),
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "excludeOneOff": False, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert contract.id in contract_ids

    def test_exclude_one_off_keeps_recurring_items(self, user, tenant, customer, product):
        """With excludeOneOff=true, contracts with both recurring and one-off items keep
        the recurring items and their revenue is correct."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Mixed Items",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        # Recurring item
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            is_one_off=False,
            billing_start_date=contract.billing_start_date,
        )
        # One-off item
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("5000.00"),
            price_period="monthly",
            is_one_off=True,
            billing_start_date=date(today.year, 3, 1),
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "excludeOneOff": True, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)
        # Only recurring item: 1000/month * 3 months = 3000
        assert Decimal(row["total"]) == Decimal("3000.00")


class TestRevenueForecastEmptyState:
    """Test revenue_forecast when no contracts exist."""

    def test_empty_result_no_contracts(self, user):
        """No contracts produces an empty but valid result (no error)."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        assert data["error"] is None
        assert data["contracts"] == []
        assert Decimal(data["grandTotal"]) == Decimal("0")
        assert len(data["monthColumns"]) == 3
        # Monthly totals exist but are all zero
        for t in data["monthlyTotals"]:
            assert Decimal(t["amount"]) == Decimal("0")


class TestRevenueForecastPermission:
    """Test that revenue_forecast requires contracts.read permission."""

    def test_requires_contracts_read_permission(self, user_no_perms):
        """Users without contracts.read permission are denied."""
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user_no_perms),
        )

        # Should error (permission denied) - Strawberry raises as a GraphQL error
        assert result.errors is not None


# ---------------------------------------------------------------------------
# Tests: Recognition Forecast
# ---------------------------------------------------------------------------


class TestRecognitionForecastMonthlyView:
    """Test recognition_forecast with monthly view."""

    def test_returns_correct_month_columns(self, user, active_contract_with_item):
        """Monthly view returns the expected month columns."""
        today = date.today()
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        assert data["error"] is None
        columns = data["monthColumns"]
        assert len(columns) == 6
        assert columns[0] == f"{today.year}-01"

    def test_contract_appears_with_revenue(self, user, active_contract_with_item):
        """Active contract with items produces recognition rows."""
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        contracts = data["contracts"]
        assert len(contracts) >= 1

        row = next(c for c in contracts if c["contractId"] == active_contract_with_item.id)
        assert row["contractName"] == "Active Monthly"
        assert Decimal(row["total"]) > Decimal("0")

    def test_grand_total_equals_sum_of_monthly_totals(self, user, active_contract_with_item):
        """grandTotal must equal the sum of all monthlyTotals amounts."""
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        sum_totals = sum(Decimal(t["amount"]) for t in data["monthlyTotals"])
        assert Decimal(data["grandTotal"]) == sum_totals


class TestRecognitionForecastQuarterlyView:
    """Test recognition_forecast with quarterly view."""

    def test_returns_correct_quarter_columns(self, user, active_contract_with_item):
        """Quarterly view returns the expected quarter columns."""
        today = date.today()
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "quarterly", "quarters": 4, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        columns = data["monthColumns"]
        assert len(columns) == 4
        assert columns[0] == f"{today.year}-Q1"
        assert columns[3] == f"{today.year}-Q4"


class TestRecognitionForecastCustomerNumber:
    """Test that customer_number is populated for recognition forecast too."""

    def test_customer_number_populated(self, user, tenant, customer_with_number, product):
        """Recognition forecast populates customerNumber from netsuite_customer_number."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer_with_number,
            name="Recognition NS Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("800.00"),
            price_period="monthly",
            billing_start_date=contract.billing_start_date,
        )

        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)
        assert row["customerNumber"] == "CUS174"

    def test_customer_number_null_when_absent(self, user, active_contract_with_item):
        """Recognition forecast returns null customerNumber when not set."""
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == active_contract_with_item.id)
        assert row["customerNumber"] is None


class TestRecognitionForecastStatusFiltering:
    """Test that recognition_forecast filters by contract status."""

    def test_draft_excluded(self, user, tenant, customer, product):
        """Draft contracts must not appear in the recognition forecast."""
        today = date.today()
        draft = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Draft Contract",
            status=Contract.Status.DRAFT,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=draft,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=draft.billing_start_date,
        )

        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert draft.id not in contract_ids

    def test_ended_before_period_excluded(self, user, tenant, customer, product):
        """Contracts with end_date before the forecast start are excluded."""
        today = date.today()
        ended = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Ended Last Year",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year - 2, 1, 1),
            end_date=date(today.year - 1, 6, 30),
            billing_start_date=date(today.year - 2, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=ended,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            billing_start_date=ended.billing_start_date,
        )

        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert ended.id not in contract_ids


class TestRecognitionForecastExcludeOneOff:
    """Test excludeOneOff filter for recognition forecast."""

    def test_exclude_one_off_filters_correctly(self, user, tenant, customer, product):
        """With excludeOneOff=true, contracts with only one-off items are excluded."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="One-Off Recognition",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("5000.00"),
            price_period="monthly",
            is_one_off=True,
            billing_start_date=date(today.year, 2, 1),
        )

        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "excludeOneOff": True, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert contract.id not in contract_ids


class TestRecognitionForecastEmptyState:
    """Test recognition_forecast when no contracts exist."""

    def test_empty_result_no_contracts(self, user):
        """No contracts produces an empty but valid result."""
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["recognitionForecast"]
        assert data["error"] is None
        assert data["contracts"] == []
        assert Decimal(data["grandTotal"]) == Decimal("0")


class TestRecognitionForecastPermission:
    """Test that recognition_forecast requires contracts.read permission."""

    def test_requires_contracts_read_permission(self, user_no_perms):
        """Users without contracts.read permission are denied."""
        result = run_graphql(
            RECOGNITION_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user_no_perms),
        )

        assert result.errors is not None


# ---------------------------------------------------------------------------
# Tests: Shared behavior (both forecasts)
# ---------------------------------------------------------------------------


class TestForecastTenantIsolation:
    """Test that forecasts only return contracts from the user's tenant."""

    def test_other_tenant_contracts_invisible(self, user, tenant, customer, product):
        """Contracts belonging to another tenant are never visible."""
        today = date.today()
        other_tenant = Tenant.objects.create(name="Other Corp", currency="USD")
        other_customer = Customer.objects.create(
            tenant=other_tenant,
            name="Other Customer",
            is_active=True,
        )
        other_contract = Contract.objects.create(
            tenant=other_tenant,
            customer=other_customer,
            name="Other Tenant Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        other_product = Product.objects.create(
            tenant=other_tenant, name="Other Product", sku="OTH-001",
        )
        ContractItem.objects.create(
            tenant=other_tenant,
            contract=other_contract,
            product=other_product,
            quantity=1,
            unit_price=Decimal("2000.00"),
            price_period="monthly",
            billing_start_date=other_contract.billing_start_date,
        )

        # Query as user from original tenant
        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert other_contract.id not in contract_ids


class TestForecastContractEndDateBoundary:
    """Test contracts with end_date on the boundary of the forecast period."""

    def test_contract_ending_within_period_included(self, user, tenant, customer, product):
        """Contracts with end_date within the forecast period are included."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Ending Soon",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            end_date=date(today.year, 3, 31),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=contract.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 6, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert contract.id in contract_ids

        # Revenue should stop at end_date -- months after March should be zero
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)
        months_after_end = [
            m for m in row["months"]
            if m["month"] > f"{today.year}-03"
        ]
        for m in months_after_end:
            assert Decimal(m["amount"]) == Decimal("0")

    def test_contract_end_date_exactly_at_period_start_excluded(self, user, tenant, customer, product):
        """Contract whose end_date is before the period start (Jan 1) is excluded."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Ended Before Period",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year - 1, 1, 1),
            end_date=date(today.year - 1, 12, 31),  # Ended Dec 31 last year
            billing_start_date=date(today.year - 1, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=contract.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        contract_ids = [c["contractId"] for c in data["contracts"]]
        assert contract.id not in contract_ids


class TestForecastContractNameFallback:
    """Test the contract name fallback when name is empty."""

    def test_unnamed_contract_uses_fallback(self, user, tenant, customer, product):
        """Contracts without a name use 'Vertrag {id}' as the display name."""
        today = date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=contract.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)
        assert row["contractName"] == f"Vertrag {contract.id}"


class TestForecastMultipleContracts:
    """Test forecast with multiple contracts to verify aggregation."""

    def test_monthly_totals_aggregate_across_contracts(self, user, tenant, customer, product):
        """Monthly totals are the sum of all contract amounts for each period."""
        today = date.today()

        # Contract A: 1000/month
        contract_a = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Contract A",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract_a,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=contract_a.billing_start_date,
        )

        # Contract B: 2000/month
        contract_b = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Contract B",
            status=Contract.Status.ACTIVE,
            start_date=date(today.year, 1, 1),
            billing_start_date=date(today.year, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract_b,
            product=product,
            quantity=1,
            unit_price=Decimal("2000.00"),
            price_period="monthly",
            billing_start_date=contract_b.billing_start_date,
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 3, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]

        # Each month total should be 3000
        for t in data["monthlyTotals"]:
            assert Decimal(t["amount"]) == Decimal("3000.00")

        # Grand total: 3000 * 3 = 9000
        assert Decimal(data["grandTotal"]) == Decimal("9000.00")

        # Two contracts in the result
        assert len(data["contracts"]) == 2


class TestProRataDistribution:
    """Pro-rata distribution respects the contract end_date as the upper bound.

    Regression for: biennial contract running only 13 months showed 766 €/month
    (18384/24) instead of 1414 €/month (18384/13) because the divisor was the
    full billing interval (24) rather than the actual covered months (13).
    """

    def test_biennial_contract_short_run_distributes_over_actual_months(
        self, user, tenant, customer, product, db
    ):
        """Biennial contract with min_duration of 12 months: pro-rata uses 12 not 24.

        Replicates production bug: contract billed every 2 years but only running
        12 months. Without explicit end_date, _calc_end_prorate does not pro-rate
        the billing event, so the full 24-month amount (24 000 €) is billed.
        The pro-rata forecast must then distribute that amount over the actual
        12 months (2 000 €/month), not the full 24 months (1 000 €/month).
        """
        # No end_date — only min_duration_months. _calc_end_prorate will NOT pro-rate
        # the billing event because self.end_date is None. The full 24 000 € is billed.
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Biennial Short",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            min_duration_months=12,  # 12-month term, no explicit end_date
            billing_interval=Contract.BillingInterval.BIENNIAL,
            billing_anchor_day=1,
        )
        # unit_price 1000 €/month → full 2-year billing event = 24 000 €
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=date(2026, 1, 1),
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 13, "proRata": True, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)

        # Pro-rata over actual 12 months → 24 000 / 12 = 2 000 €/month
        jan_2026 = next(m for m in row["months"] if m["month"] == "2026-01")
        assert Decimal(jan_2026["amount"]) == Decimal("2000.00")

        # Total across forecast = full billing event (24 000 €), spread over 12 months
        assert Decimal(row["total"]) == Decimal("24000.00")

    def test_annual_billing_crossing_year_boundary_included(
        self, user, tenant, customer, product, db
    ):
        """Annual billing event on 2025-04-01 must appear in Jan–Mar 2026 (pro-rata).

        The billing event falls before the forecast window (Jan 2026) but its
        period extends into the window. Without the lookback fix the event is
        silently skipped and Jan–Mar 2026 show zero revenue.
        """
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Annual Cross-Year",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 4, 1),
            billing_start_date=date(2025, 4, 1),
            billing_interval=Contract.BillingInterval.ANNUAL,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=date(2025, 4, 1),
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 13, "proRata": True, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)

        # Apr 2025 billing event = 12 000 €, distributed over 12 months.
        # Jan–Mar 2026 are the last 3 months of that period → each 1 000 €.
        jan_2026 = next(m for m in row["months"] if m["month"] == "2026-01")
        assert Decimal(jan_2026["amount"]) == Decimal("1000.00")
        mar_2026 = next(m for m in row["months"] if m["month"] == "2026-03")
        assert Decimal(mar_2026["amount"]) == Decimal("1000.00")

        # Apr 2026 billing event starts the next cycle — also 1 000 €/month
        apr_2026 = next(m for m in row["months"] if m["month"] == "2026-04")
        assert Decimal(apr_2026["amount"]) == Decimal("1000.00")

    def test_biennial_contract_full_run_keeps_24_month_divisor(
        self, user, tenant, customer, product, db
    ):
        """Open-ended biennial contract: divisor stays at 24 (no effective end)."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Biennial Full",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            # No end_date, no min_duration → open-ended → divisor = full interval
            billing_interval=Contract.BillingInterval.BIENNIAL,
            billing_anchor_day=1,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            billing_start_date=date(2026, 1, 1),
        )

        result = run_graphql(
            REVENUE_FORECAST_QUERY,
            {"view": "monthly", "months": 13, "proRata": True, "refresh": True},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["revenueForecast"]
        row = next(c for c in data["contracts"] if c["contractId"] == contract.id)

        # Pro-rata over full 24 months → 24 000 / 24 = 1 000 €/month
        jan_2026 = next(m for m in row["months"] if m["month"] == "2026-01")
        assert Decimal(jan_2026["amount"]) == Decimal("1000.00")
