"""GraphQL tests for contract billing fields."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product
from apps.tenants.models import Tenant, User
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
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Company",
        currency="EUR",
    )


@pytest.fixture
def user(db, tenant):
    """Create a test user."""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )


@pytest.fixture
def customer(db, tenant):
    """Create a test customer."""
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
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
def annual_contract(db, tenant, customer):
    """Create a test contract with annual billing starting Jan 1."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Annual Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.ANNUAL,
        billing_anchor_day=1,
    )


class TestSuggestedAlignmentDateQuery:
    """Test suggestedAlignmentDate GraphQL query."""

    def test_suggested_alignment_date_query(self, user, annual_contract):
        """Test querying suggested alignment date."""
        query = """
            query SuggestedAlignmentDate($contractId: ID!, $billingStartDate: Date!) {
                suggestedAlignmentDate(contractId: $contractId, billingStartDate: $billingStartDate) {
                    suggestedDate
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {
                "contractId": str(annual_contract.id),
                "billingStartDate": "2026-05-04",
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["suggestedAlignmentDate"]["error"] is None
        assert result.data["suggestedAlignmentDate"]["suggestedDate"] == "2027-01-01"

    def test_suggested_alignment_date_contract_not_found(self, user):
        """Test error when contract not found."""
        query = """
            query SuggestedAlignmentDate($contractId: ID!, $billingStartDate: Date!) {
                suggestedAlignmentDate(contractId: $contractId, billingStartDate: $billingStartDate) {
                    suggestedDate
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {
                "contractId": "99999",
                "billingStartDate": "2026-05-04",
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["suggestedAlignmentDate"]["error"] == "Contract not found"


class TestAddContractItemWithBillingFields:
    """Test addContractItem mutation with billing fields."""

    def test_add_item_with_billing_dates(self, user, annual_contract, product):
        """Test adding a contract item with billing dates."""
        mutation = """
            mutation AddContractItem($contractId: ID!, $input: ContractItemInput!) {
                addContractItem(contractId: $contractId, input: $input) {
                    success
                    error
                    item {
                        id
                        quantity
                        unitPrice
                        billingStartDate
                        alignToContractAt
                        suggestedAlignmentDate
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "contractId": str(annual_contract.id),
                "input": {
                    "productId": str(product.id),
                    "quantity": 1,
                    "unitPrice": "100.00",
                    "priceSource": "list",
                    "billingStartDate": "2026-05-04",
                    "alignToContractAt": "2027-01-01",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItem"]["success"] is True
        assert result.data["addContractItem"]["item"]["billingStartDate"] == "2026-05-04"
        assert result.data["addContractItem"]["item"]["alignToContractAt"] == "2027-01-01"
        assert result.data["addContractItem"]["item"]["suggestedAlignmentDate"] == "2027-01-01"

    def test_add_item_without_billing_dates(self, user, annual_contract, product):
        """Test adding a contract item without billing dates."""
        mutation = """
            mutation AddContractItem($contractId: ID!, $input: ContractItemInput!) {
                addContractItem(contractId: $contractId, input: $input) {
                    success
                    error
                    item {
                        id
                        billingStartDate
                        alignToContractAt
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "contractId": str(annual_contract.id),
                "input": {
                    "productId": str(product.id),
                    "quantity": 1,
                    "unitPrice": "100.00",
                    "priceSource": "list",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItem"]["success"] is True
        assert result.data["addContractItem"]["item"]["billingStartDate"] is None
        assert result.data["addContractItem"]["item"]["alignToContractAt"] is None


class TestUpdateContractItemWithBillingFields:
    """Test updateContractItem mutation with billing fields."""

    def test_update_item_billing_dates(self, user, tenant, annual_contract, product):
        """Test updating a contract item's billing dates."""
        # Create an item first
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        mutation = """
            mutation UpdateContractItem($input: UpdateContractItemInput!) {
                updateContractItem(input: $input) {
                    success
                    error
                    item {
                        id
                        billingStartDate
                        billingEndDate
                        alignToContractAt
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "input": {
                    "id": str(item.id),
                    "billingStartDate": "2026-05-04",
                    "billingEndDate": "2026-12-31",
                    "alignToContractAt": "2027-01-01",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["updateContractItem"]["success"] is True
        assert result.data["updateContractItem"]["item"]["billingStartDate"] == "2026-05-04"
        assert result.data["updateContractItem"]["item"]["billingEndDate"] == "2026-12-31"
        assert result.data["updateContractItem"]["item"]["alignToContractAt"] == "2027-01-01"


class TestContractItemsQuery:
    """Test querying contract items with billing fields."""

    def test_query_contract_items_with_billing_fields(self, user, tenant, annual_contract, product):
        """Test querying contract items returns billing fields."""
        # Create an item with billing dates
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 5, 4),
            align_to_contract_at=date(2027, 1, 1),
        )

        query = """
            query Contract($id: ID!) {
                contract(id: $id) {
                    id
                    items {
                        id
                        billingStartDate
                        billingEndDate
                        alignToContractAt
                        suggestedAlignmentDate
                    }
                }
            }
        """

        result = run_graphql(
            query,
            {"id": str(annual_contract.id)},
            make_context(user),
        )

        assert result.errors is None
        items = result.data["contract"]["items"]
        assert len(items) == 1
        assert items[0]["billingStartDate"] == "2026-05-04"
        assert items[0]["billingEndDate"] is None
        assert items[0]["alignToContractAt"] == "2027-01-01"
        assert items[0]["suggestedAlignmentDate"] == "2027-01-01"


class TestPriceLockValidation:
    """Test price lock validation in GraphQL mutations."""

    def test_update_item_price_when_locked_fails(self, user, tenant, annual_contract, product):
        """Test that updating unit_price fails when price is locked."""
        # Create an item with price_locked=True
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_locked=True,
        )

        mutation = """
            mutation UpdateContractItem($input: UpdateContractItemInput!) {
                updateContractItem(input: $input) {
                    success
                    error
                    item {
                        id
                        unitPrice
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "input": {
                    "id": str(item.id),
                    "unitPrice": "150.00",  # Try to change price
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["updateContractItem"]["success"] is False
        assert "locked" in result.data["updateContractItem"]["error"].lower()

    def test_update_item_price_when_lock_expired_succeeds(self, user, tenant, annual_contract, product):
        """Test that updating unit_price succeeds when price lock has expired."""
        # Create an item with price_locked=True but expired lock
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_locked=True,
            price_locked_until=date(2020, 1, 1),  # Expired
        )

        mutation = """
            mutation UpdateContractItem($input: UpdateContractItemInput!) {
                updateContractItem(input: $input) {
                    success
                    error
                    item {
                        id
                        unitPrice
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "input": {
                    "id": str(item.id),
                    "unitPrice": "150.00",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["updateContractItem"]["success"] is True
        assert result.data["updateContractItem"]["item"]["unitPrice"] == "150.00"

    def test_add_price_period_when_locked_fails(self, user, tenant, annual_contract, product):
        """Test that adding a price period fails when price is locked."""
        from apps.contracts.models import ContractItemPrice

        # Create an item with price_locked=True
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_locked=True,
        )

        mutation = """
            mutation AddContractItemPrice($itemId: ID!, $input: ContractItemPriceInput!) {
                addContractItemPrice(itemId: $itemId, input: $input) {
                    success
                    error
                    pricePeriod {
                        id
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "itemId": str(item.id),
                "input": {
                    "validFrom": "2025-01-01",
                    "validTo": "2025-12-31",
                    "unitPrice": "80.00",
                    "source": "fixed",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItemPrice"]["success"] is False
        assert "locked" in result.data["addContractItemPrice"]["error"].lower()

    def test_remove_price_period_when_locked_fails(self, user, tenant, annual_contract, product):
        """Test that removing a price period fails when price is locked."""
        from apps.contracts.models import ContractItemPrice

        # Create an item (unlocked initially to add price period)
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Add a price period
        price_period = ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        # Now lock the price
        item.price_locked = True
        item.save()

        mutation = """
            mutation RemoveContractItemPrice($priceId: ID!) {
                removeContractItemPrice(priceId: $priceId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"priceId": str(price_period.id)},
            make_context(user),
        )

        assert result.errors is None
        assert result.data["removeContractItemPrice"]["success"] is False
        assert "locked" in result.data["removeContractItemPrice"]["error"].lower()


class TestPricePeriodsGraphQL:
    """Test price periods GraphQL queries and mutations."""

    def test_query_contract_items_with_price_periods(self, user, tenant, annual_contract, product):
        """Test querying contract items returns price periods."""
        from apps.contracts.models import ContractItemPrice

        # Create an item with price periods
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("100.00"),
            source="list",
        )

        query = """
            query Contract($id: ID!) {
                contract(id: $id) {
                    id
                    items {
                        id
                        unitPrice
                        priceLocked
                        priceLockedUntil
                        pricePeriods {
                            id
                            validFrom
                            validTo
                            unitPrice
                            source
                        }
                    }
                }
            }
        """

        result = run_graphql(
            query,
            {"id": str(annual_contract.id)},
            make_context(user),
        )

        assert result.errors is None
        items = result.data["contract"]["items"]
        assert len(items) == 1
        assert items[0]["priceLocked"] is False
        assert items[0]["priceLockedUntil"] is None
        assert len(items[0]["pricePeriods"]) == 2
        assert items[0]["pricePeriods"][0]["validFrom"] == "2025-01-01"
        assert items[0]["pricePeriods"][0]["unitPrice"] == "80.00"
        assert items[0]["pricePeriods"][1]["validFrom"] == "2026-01-01"
        assert items[0]["pricePeriods"][1]["validTo"] is None

    def test_add_price_period_success(self, user, tenant, annual_contract, product):
        """Test adding a price period successfully."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        mutation = """
            mutation AddContractItemPrice($itemId: ID!, $input: ContractItemPriceInput!) {
                addContractItemPrice(itemId: $itemId, input: $input) {
                    success
                    error
                    pricePeriod {
                        id
                        validFrom
                        validTo
                        unitPrice
                        source
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "itemId": str(item.id),
                "input": {
                    "validFrom": "2025-01-01",
                    "validTo": "2025-12-31",
                    "unitPrice": "80.00",
                    "source": "fixed",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItemPrice"]["success"] is True
        pp = result.data["addContractItemPrice"]["pricePeriod"]
        assert pp["validFrom"] == "2025-01-01"
        assert pp["validTo"] == "2025-12-31"
        assert pp["unitPrice"] == "80.00"
        assert pp["source"] == "fixed"

    def test_remove_price_period_success(self, user, tenant, annual_contract, product):
        """Test removing a price period successfully."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        price_period = ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        mutation = """
            mutation RemoveContractItemPrice($priceId: ID!) {
                removeContractItemPrice(priceId: $priceId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"priceId": str(price_period.id)},
            make_context(user),
        )

        assert result.errors is None
        assert result.data["removeContractItemPrice"]["success"] is True

        # Verify it's deleted
        from apps.contracts.models import ContractItemPrice
        assert not ContractItemPrice.objects.filter(id=price_period.id).exists()

    def test_add_price_period_overlap_fails(self, user, tenant, annual_contract, product):
        """Test that adding a price period that overlaps with existing fails."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Create existing period: 2025-01-01 to 2025-12-31
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        mutation = """
            mutation AddContractItemPrice($itemId: ID!, $input: ContractItemPriceInput!) {
                addContractItemPrice(itemId: $itemId, input: $input) {
                    success
                    error
                }
            }
        """

        # Try to add overlapping period: 2025-06-01 to 2026-06-30
        result = run_graphql(
            mutation,
            {
                "itemId": str(item.id),
                "input": {
                    "validFrom": "2025-06-01",
                    "validTo": "2026-06-30",
                    "unitPrice": "90.00",
                    "source": "fixed",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItemPrice"]["success"] is False
        assert "overlap" in result.data["addContractItemPrice"]["error"].lower()

    def test_add_price_period_no_overlap_succeeds(self, user, tenant, annual_contract, product):
        """Test that adding a non-overlapping price period succeeds."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Create existing period: 2025-01-01 to 2025-12-31
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        mutation = """
            mutation AddContractItemPrice($itemId: ID!, $input: ContractItemPriceInput!) {
                addContractItemPrice(itemId: $itemId, input: $input) {
                    success
                    error
                }
            }
        """

        # Add non-overlapping period: 2026-01-01 to 2026-12-31
        result = run_graphql(
            mutation,
            {
                "itemId": str(item.id),
                "input": {
                    "validFrom": "2026-01-01",
                    "validTo": "2026-12-31",
                    "unitPrice": "90.00",
                    "source": "fixed",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItemPrice"]["success"] is True

    def test_update_price_period_overlap_fails(self, user, tenant, annual_contract, product):
        """Test that updating a price period to overlap with another fails."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Create two non-overlapping periods
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        period2 = ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
            unit_price=Decimal("90.00"),
            source="fixed",
        )

        mutation = """
            mutation UpdateContractItemPrice($input: UpdateContractItemPriceInput!) {
                updateContractItemPrice(input: $input) {
                    success
                    error
                }
            }
        """

        # Try to update period2 to overlap with period1
        result = run_graphql(
            mutation,
            {
                "input": {
                    "id": str(period2.id),
                    "validFrom": "2025-06-01",  # Now overlaps with period1
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["updateContractItemPrice"]["success"] is False
        assert "overlap" in result.data["updateContractItemPrice"]["error"].lower()

    def test_add_open_ended_period_with_existing_open_ended_fails(self, user, tenant, annual_contract, product):
        """Test that adding an open-ended period when one already exists fails."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Create open-ended period: 2025-01-01 onwards
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=None,  # Open-ended
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        mutation = """
            mutation AddContractItemPrice($itemId: ID!, $input: ContractItemPriceInput!) {
                addContractItemPrice(itemId: $itemId, input: $input) {
                    success
                    error
                }
            }
        """

        # Try to add another open-ended period starting later
        result = run_graphql(
            mutation,
            {
                "itemId": str(item.id),
                "input": {
                    "validFrom": "2026-01-01",
                    "validTo": None,
                    "unitPrice": "90.00",
                    "source": "fixed",
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["addContractItemPrice"]["success"] is False
        assert "overlap" in result.data["addContractItemPrice"]["error"].lower()


class TestNoticePeriodAfterMinGraphQL:
    """Test notice_period_after_min_months in GraphQL."""

    def test_create_contract_with_notice_period_after_min(self, user, customer):
        """Test creating a contract with notice_period_after_min_months."""
        mutation = """
            mutation CreateContract($input: CreateContractInput!) {
                createContract(input: $input) {
                    success
                    error
                    contract {
                        id
                        noticePeriodMonths
                        noticePeriodAfterMinMonths
                        minDurationMonths
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "input": {
                    "customerId": str(customer.id),
                    "startDate": "2025-01-01",
                    "billingInterval": "monthly",
                    "noticePeriodMonths": 3,
                    "noticePeriodAfterMinMonths": 1,
                    "minDurationMonths": 12,
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["createContract"]["success"] is True
        contract = result.data["createContract"]["contract"]
        assert contract["noticePeriodMonths"] == 3
        assert contract["noticePeriodAfterMinMonths"] == 1
        assert contract["minDurationMonths"] == 12

    def test_update_contract_notice_period_after_min(self, user, tenant, customer):
        """Test updating contract notice_period_after_min_months."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            notice_period_months=3,
        )

        mutation = """
            mutation UpdateContract($input: UpdateContractInput!) {
                updateContract(input: $input) {
                    success
                    error
                    contract {
                        id
                        noticePeriodAfterMinMonths
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "input": {
                    "id": str(contract.id),
                    "noticePeriodAfterMinMonths": 1,
                },
            },
            make_context(user),
        )

        assert result.errors is None
        assert result.data["updateContract"]["success"] is True
        assert result.data["updateContract"]["contract"]["noticePeriodAfterMinMonths"] == 1

    def test_query_contract_notice_period_after_min(self, user, tenant, customer):
        """Test querying contract returns notice_period_after_min_months."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            notice_period_months=3,
            notice_period_after_min_months=1,
            min_duration_months=24,
        )

        query = """
            query Contract($id: ID!) {
                contract(id: $id) {
                    id
                    noticePeriodMonths
                    noticePeriodAfterMinMonths
                    minDurationMonths
                }
            }
        """

        result = run_graphql(
            query,
            {"id": str(contract.id)},
            make_context(user),
        )

        assert result.errors is None
        assert result.data["contract"]["noticePeriodMonths"] == 3
        assert result.data["contract"]["noticePeriodAfterMinMonths"] == 1
        assert result.data["contract"]["minDurationMonths"] == 24
