"""Tests for revenue by stream calculation."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from config.schema import schema
from apps.contracts.models import Contract, ContractItem
from apps.contracts.schema import calculate_revenue_by_stream
from apps.core.models import RevenueType
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
def recurring_product(db, tenant):
    return Product.objects.create(
        tenant=tenant, name="SaaS License", sku="SAAS-001",
        type=Product.ProductType.SUBSCRIPTION,
        revenue_type=RevenueType.RECURRING,
    )


@pytest.fixture
def dev_product(db, tenant):
    return Product.objects.create(
        tenant=tenant, name="Custom Dev", sku="DEV-001",
        type=Product.ProductType.ONE_OFF,
        revenue_type=RevenueType.ADVANCED_DEVELOPMENT,
    )


@pytest.fixture
def training_product(db, tenant):
    return Product.objects.create(
        tenant=tenant, name="Training", sku="TRN-001",
        type=Product.ProductType.ONE_OFF,
        revenue_type=RevenueType.TRAINING_IMPLEMENTATION,
    )


class TestCalculateRevenueByStream:
    @patch("apps.contracts.schema.date")
    def test_recurring_revenue_classified(self, mock_date, tenant, customer, recurring_product):
        mock_date.today.return_value = date(2026, 6, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Test",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=contract,
            product=recurring_product,
            quantity=1, unit_price=Decimal("1000.00"),
        )

        result = calculate_revenue_by_stream(tenant, 2026)
        stream_map = {s["revenue_type"]: s for s in result}
        assert "recurring" in stream_map
        # Full year forecast: 12 months × €1000 = €12000
        assert stream_map["recurring"]["full_year_forecast"] == Decimal("12000")
        # YTD (Jan-Jun 15): 6 months billed = €6000
        assert stream_map["recurring"]["ytd_actual"] == Decimal("6000")

    @patch("apps.contracts.schema.date")
    def test_one_off_dev_classified(self, mock_date, tenant, customer, dev_product):
        mock_date.today.return_value = date(2026, 6, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Dev Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 3, 1),
            billing_start_date=date(2026, 3, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=contract,
            product=dev_product,
            quantity=1, unit_price=Decimal("5000.00"),
            is_one_off=True,
            billing_start_date=date(2026, 3, 1),
        )

        result = calculate_revenue_by_stream(tenant, 2026)
        stream_map = {s["revenue_type"]: s for s in result}
        assert "advanced_development" in stream_map
        assert stream_map["advanced_development"]["full_year_forecast"] == Decimal("5000.00")

    @patch("apps.contracts.schema.date")
    def test_unclassified_bucket(self, mock_date, tenant, customer):
        mock_date.today.return_value = date(2026, 6, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Unclassified",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        # Item with no product and no revenue type
        ContractItem.objects.create(
            tenant=tenant, contract=contract,
            product=None, description="Misc service",
            quantity=1, unit_price=Decimal("500.00"),
        )

        result = calculate_revenue_by_stream(tenant, 2026)
        stream_map = {s["revenue_type"]: s for s in result}
        assert "unclassified" in stream_map
        assert stream_map["unclassified"]["full_year_forecast"] > Decimal("0")

    @patch("apps.contracts.schema.date")
    def test_all_standard_streams_present(self, mock_date, tenant, customer):
        """Even with no items, all 3 standard streams should be present."""
        mock_date.today.return_value = date(2026, 6, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = calculate_revenue_by_stream(tenant, 2026)
        stream_types = {s["revenue_type"] for s in result}
        assert "recurring" in stream_types
        assert "advanced_development" in stream_types
        assert "training_implementation" in stream_types

    @patch("apps.contracts.schema.date")
    def test_mixed_streams(self, mock_date, tenant, customer, recurring_product, training_product):
        mock_date.today.return_value = date(2026, 6, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Mixed",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=contract,
            product=recurring_product,
            quantity=1, unit_price=Decimal("1000.00"),
        )
        ContractItem.objects.create(
            tenant=tenant, contract=contract,
            product=training_product,
            quantity=1, unit_price=Decimal("3000.00"),
            is_one_off=True,
            billing_start_date=date(2026, 2, 1),
        )

        result = calculate_revenue_by_stream(tenant, 2026)
        stream_map = {s["revenue_type"]: s for s in result}
        assert stream_map["recurring"]["full_year_forecast"] == Decimal("12000")
        assert stream_map["training_implementation"]["full_year_forecast"] == Decimal("3000.00")


class TestRevenueByStreamQuery:
    QUERY = """
        query RevenueByStream($year: Int!) {
            revenueByStream(year: $year) {
                revenueType
                ytdActual
                fullYearForecast
            }
        }
    """

    def test_query_returns_stream_data(self, user, tenant):
        result = run_graphql(self.QUERY, {"year": 2026}, make_context(user))
        assert result.errors is None
        streams = result.data["revenueByStream"]
        # Should have at least the 3 standard streams
        stream_types = {s["revenueType"] for s in streams}
        assert "recurring" in stream_types
        assert "advanced_development" in stream_types
        assert "training_implementation" in stream_types
