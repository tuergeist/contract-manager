"""GraphQL tests for contract billing fields."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import Contract, ContractAmendment, ContractItem, ContractItemPrice
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


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Company",
        currency="EUR",
    )


@pytest.fixture
def user(db, tenant):
    """Create a test user with Admin role."""
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


BULK_PRICE_INCREASE_MUTATION = """
    mutation BulkPriceIncrease($input: BulkPriceIncreaseInput!) {
        bulkPriceIncrease(input: $input) {
            success
            error
            itemsChanged
            itemsSkipped
            details {
                itemId
                itemDescription
                oldPrice
                newPrice
                skipped
                skipReason
            }
        }
    }
"""


class TestBulkPriceIncrease:
    """Tests for the bulk_price_increase mutation."""

    def test_direct_mode_basic(self, user, tenant, annual_contract, product):
        """Direct mode updates unit_price on each item."""
        item1 = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )
        item2 = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract,
            description="Support Service", quantity=1, unit_price=Decimal("200.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.errors is None
        data = result.data["bulkPriceIncrease"]
        assert data["success"] is True
        assert data["itemsChanged"] == 2
        assert data["itemsSkipped"] == 0

        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.unit_price == Decimal("110.00")
        assert item2.unit_price == Decimal("220.00")

    def test_period_specific_mode_basic(self, user, tenant, annual_contract, product):
        """Period-specific mode creates ContractItemPrice records."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "5",
                "effectiveDate": "2027-01-01",
                "mode": "period_specific",
            }
        }, make_context(user))

        assert result.errors is None
        data = result.data["bulkPriceIncrease"]
        assert data["success"] is True
        assert data["itemsChanged"] == 1

        # Original price unchanged
        item.refresh_from_db()
        assert item.unit_price == Decimal("100.00")

        # New price period created
        price_period = ContractItemPrice.objects.get(item=item)
        assert price_period.valid_from == date(2027, 1, 1)
        assert price_period.valid_to is None
        assert price_period.unit_price == Decimal("105.00")
        assert price_period.source == "fixed"

    def test_direct_mode_multiple_increases(self, user, tenant, annual_contract, product):
        """Direct mode can be applied multiple times, compounding."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        # First increase: 10%
        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))
        assert result.data["bulkPriceIncrease"]["success"] is True
        item.refresh_from_db()
        assert item.unit_price == Decimal("110.00")

        # Second increase: 5%
        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "5",
                "effectiveDate": "2028-01-01",
                "mode": "direct",
            }
        }, make_context(user))
        assert result.data["bulkPriceIncrease"]["success"] is True
        item.refresh_from_db()
        assert item.unit_price == Decimal("115.50")

    def test_period_specific_mode_multiple_increases(self, user, tenant, annual_contract, product):
        """Period-specific mode compounds: second increase uses effective price from first."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        # First increase: 10% from 2027-01-01
        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "period_specific",
            }
        }, make_context(user))
        assert result.data["bulkPriceIncrease"]["success"] is True

        pp1 = ContractItemPrice.objects.get(item=item)
        assert pp1.valid_from == date(2027, 1, 1)
        assert pp1.valid_to is None
        assert pp1.unit_price == Decimal("110.00")

        # Second increase: 5% from 2028-01-01
        # Should base on 110.00 (the effective price at 2028-01-01)
        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "5",
                "effectiveDate": "2028-01-01",
                "mode": "period_specific",
            }
        }, make_context(user))
        assert result.data["bulkPriceIncrease"]["success"] is True

        # First period should be closed
        pp1.refresh_from_db()
        assert pp1.valid_to == date(2027, 12, 31)

        # New period created
        pp2 = ContractItemPrice.objects.filter(item=item, valid_from=date(2028, 1, 1)).first()
        assert pp2 is not None
        assert pp2.valid_to is None
        assert pp2.unit_price == Decimal("115.50")

    def test_period_specific_three_consecutive_increases(self, user, tenant, annual_contract, product):
        """Three consecutive yearly increases all compound correctly."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("1000.00"),
        )

        for year, pct in [(2027, "3"), (2028, "3"), (2029, "3")]:
            result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
                "input": {
                    "contractId": str(annual_contract.id),
                    "percentage": pct,
                    "effectiveDate": f"{year}-01-01",
                    "mode": "period_specific",
                }
            }, make_context(user))
            assert result.data["bulkPriceIncrease"]["success"] is True

        periods = list(ContractItemPrice.objects.filter(item=item).order_by("valid_from"))
        assert len(periods) == 3

        # 2027: 1000 * 1.03 = 1030
        assert periods[0].valid_from == date(2027, 1, 1)
        assert periods[0].valid_to == date(2027, 12, 31)
        assert periods[0].unit_price == Decimal("1030.00")

        # 2028: 1030 * 1.03 = 1060.90
        assert periods[1].valid_from == date(2028, 1, 1)
        assert periods[1].valid_to == date(2028, 12, 31)
        assert periods[1].unit_price == Decimal("1060.90")

        # 2029: 1060.90 * 1.03 = 1092.73 (rounded)
        assert periods[2].valid_from == date(2029, 1, 1)
        assert periods[2].valid_to is None
        assert periods[2].unit_price == Decimal("1092.73")

    def test_skips_one_off_items(self, user, tenant, annual_contract, product):
        """One-off items are not included in the increase."""
        recurring = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"), is_one_off=False,
        )
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract,
            description="Setup Fee", quantity=1,
            unit_price=Decimal("500.00"), is_one_off=True,
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is True
        assert result.data["bulkPriceIncrease"]["itemsChanged"] == 1

        recurring.refresh_from_db()
        one_off.refresh_from_db()
        assert recurring.unit_price == Decimal("110.00")
        assert one_off.unit_price == Decimal("500.00")  # unchanged

    def test_skips_price_locked_items(self, user, tenant, annual_contract, product):
        """Price-locked items are skipped with a reason."""
        locked = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
            price_locked=True, price_locked_until=date(2028, 12, 31),
        )
        unlocked = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract,
            description="Unlocked Item", quantity=1, unit_price=Decimal("200.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        data = result.data["bulkPriceIncrease"]
        assert data["success"] is True
        assert data["itemsChanged"] == 1
        assert data["itemsSkipped"] == 1

        skipped = [d for d in data["details"] if d["skipped"]]
        assert len(skipped) == 1
        assert skipped[0]["skipReason"] == "Price locked"

        locked.refresh_from_db()
        unlocked.refresh_from_db()
        assert locked.unit_price == Decimal("100.00")
        assert unlocked.unit_price == Decimal("220.00")

    def test_price_locked_until_before_effective_date_not_skipped(self, user, tenant, annual_contract, product):
        """Item locked until before effective date is NOT skipped."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
            price_locked=True, price_locked_until=date(2026, 6, 30),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is True
        assert result.data["bulkPriceIncrease"]["itemsChanged"] == 1

        item.refresh_from_db()
        assert item.unit_price == Decimal("110.00")

    def test_creates_amendment_for_active_contract(self, user, tenant, annual_contract, product):
        """Active contract gets an amendment record."""
        assert annual_contract.status == Contract.Status.ACTIVE

        ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "5",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is True

        amendment = ContractAmendment.objects.get(contract=annual_contract)
        assert amendment.type == ContractAmendment.AmendmentType.PRICE_CHANGED
        assert "5" in amendment.description
        assert amendment.effective_date == date(2027, 1, 1)
        assert amendment.changes["type"] == "bulk_price_increase"
        assert len(amendment.changes["items_changed"]) == 1

    def test_no_amendment_for_draft_contract(self, user, tenant, customer, product):
        """Draft contract does not get an amendment record."""
        draft = Contract.objects.create(
            tenant=tenant, customer=customer, name="Draft Contract",
            status=Contract.Status.DRAFT, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )
        ContractItem.objects.create(
            tenant=tenant, contract=draft, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(draft.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is True
        assert ContractAmendment.objects.filter(contract=draft).count() == 0

    def test_error_zero_percentage(self, user, tenant, annual_contract, product):
        """Zero percentage is rejected."""
        ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "0",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is False
        assert "greater than 0" in result.data["bulkPriceIncrease"]["error"]

    def test_error_invalid_mode(self, user, tenant, annual_contract, product):
        """Invalid mode is rejected."""
        ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "5",
                "effectiveDate": "2027-01-01",
                "mode": "invalid",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is False
        assert "Mode" in result.data["bulkPriceIncrease"]["error"]

    def test_error_no_recurring_items(self, user, tenant, annual_contract):
        """Contract with no recurring items returns error."""
        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "5",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is False
        assert "No recurring items" in result.data["bulkPriceIncrease"]["error"]

    def test_fractional_percentage(self, user, tenant, annual_contract, product):
        """Fractional percentages (e.g. 3.5%) work correctly."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "3.5",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.data["bulkPriceIncrease"]["success"] is True
        item.refresh_from_db()
        assert item.unit_price == Decimal("103.50")

    def test_multiple_amendments_from_multiple_increases(self, user, tenant, annual_contract, product):
        """Each bulk increase on an active contract creates a separate amendment."""
        ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        for year in [2027, 2028]:
            result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
                "input": {
                    "contractId": str(annual_contract.id),
                    "percentage": "5",
                    "effectiveDate": f"{year}-01-01",
                    "mode": "direct",
                }
            }, make_context(user))
            assert result.data["bulkPriceIncrease"]["success"] is True

        amendments = ContractAmendment.objects.filter(contract=annual_contract)
        assert amendments.count() == 2

    def test_skips_discount_items_without_product(self, user, tenant, annual_contract, product):
        """Discount/descriptive items without a product are skipped gracefully."""
        # Regular item with product
        item = ContractItem.objects.create(
            tenant=tenant, contract=annual_contract, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )
        # Discount item — no product, zero price
        ContractItem.objects.create(
            tenant=tenant, contract=annual_contract,
            description="Discount -10%", quantity=1, unit_price=Decimal("0.00"),
        )
        # Descriptive-only item — no product, no price
        ContractItem.objects.create(
            tenant=tenant, contract=annual_contract,
            description="", quantity=1, unit_price=Decimal("0.00"),
        )

        result = run_graphql(BULK_PRICE_INCREASE_MUTATION, {
            "input": {
                "contractId": str(annual_contract.id),
                "percentage": "10",
                "effectiveDate": "2027-01-01",
                "mode": "direct",
            }
        }, make_context(user))

        assert result.errors is None
        data = result.data["bulkPriceIncrease"]
        assert data["success"] is True
        assert data["itemsChanged"] == 1
        item.refresh_from_db()
        assert item.unit_price == Decimal("110.00")


UPDATE_CONTRACT_STATUS_MUTATION = """
    mutation TransitionContractStatus($contractId: ID!, $newStatus: String!) {
        transitionContractStatus(contractId: $contractId, newStatus: $newStatus) {
            success
            error
            contract {
                id
                status
            }
        }
    }
"""

SET_ACTIVATION_FIELDS_MUTATION = """
    mutation SetActivationRequiredFields($fields: [String!]!) {
        setActivationRequiredFields(fields: $fields) {
            success
            error
        }
    }
"""


class TestActivationChecklist:
    """Tests for the activation checklist feature."""

    @pytest.fixture
    def draft_contract(self, db, tenant, customer):
        return Contract.objects.create(
            tenant=tenant, customer=customer, name="Draft Contract",
            status=Contract.Status.DRAFT, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )

    def test_activation_blocked_missing_fields(self, user, tenant, draft_contract):
        """Activation fails when required fields are missing."""
        tenant.settings = {"activation_required_fields": ["po_number", "netsuite_url"]}
        tenant.save(update_fields=["settings"])

        result = run_graphql(UPDATE_CONTRACT_STATUS_MUTATION, {
            "contractId": str(draft_contract.id),
            "newStatus": "active",
        }, make_context(user))

        assert result.errors is None
        data = result.data["transitionContractStatus"]
        assert data["success"] is False
        assert "po_number" in data["error"]
        assert "netsuite_url" in data["error"]

        draft_contract.refresh_from_db()
        assert draft_contract.status == Contract.Status.DRAFT

    def test_activation_succeeds_all_fields_filled(self, user, tenant, draft_contract):
        """Activation succeeds when all required fields are present."""
        tenant.settings = {"activation_required_fields": ["po_number"]}
        tenant.save(update_fields=["settings"])

        draft_contract.po_number = "PO-123"
        draft_contract.save(update_fields=["po_number"])

        result = run_graphql(UPDATE_CONTRACT_STATUS_MUTATION, {
            "contractId": str(draft_contract.id),
            "newStatus": "active",
        }, make_context(user))

        assert result.errors is None
        data = result.data["transitionContractStatus"]
        assert data["success"] is True

        draft_contract.refresh_from_db()
        assert draft_contract.status == Contract.Status.ACTIVE

    def test_activation_succeeds_no_required_fields(self, user, tenant, draft_contract):
        """Activation succeeds when no required fields are configured (default)."""
        # No settings configured at all
        result = run_graphql(UPDATE_CONTRACT_STATUS_MUTATION, {
            "contractId": str(draft_contract.id),
            "newStatus": "active",
        }, make_context(user))

        assert result.errors is None
        assert result.data["transitionContractStatus"]["success"] is True

    def test_paused_to_active_not_blocked(self, user, tenant, customer):
        """Paused → active transition is not blocked by checklist."""
        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Paused Contract",
            status=Contract.Status.PAUSED, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )
        tenant.settings = {"activation_required_fields": ["po_number"]}
        tenant.save(update_fields=["settings"])
        # po_number is NOT set, but transition should still work

        result = run_graphql(UPDATE_CONTRACT_STATUS_MUTATION, {
            "contractId": str(contract.id),
            "newStatus": "active",
        }, make_context(user))

        assert result.errors is None
        assert result.data["transitionContractStatus"]["success"] is True

    def test_set_activation_fields_valid(self, user, tenant):
        """Setting valid activation fields works."""
        result = run_graphql(SET_ACTIVATION_FIELDS_MUTATION, {
            "fields": ["po_number", "netsuite_url"],
        }, make_context(user))

        assert result.errors is None
        assert result.data["setActivationRequiredFields"]["success"] is True

        tenant.refresh_from_db()
        assert tenant.settings["activation_required_fields"] == ["po_number", "netsuite_url"]

    def test_set_activation_fields_rejects_invalid(self, user, tenant):
        """Setting invalid field names returns an error."""
        result = run_graphql(SET_ACTIVATION_FIELDS_MUTATION, {
            "fields": ["po_number", "invalid_field"],
        }, make_context(user))

        assert result.errors is None
        data = result.data["setActivationRequiredFields"]
        assert data["success"] is False
        assert "invalid_field" in data["error"]


# =============================================================================
# Activation Workflow Tests
# =============================================================================

UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION = """
    mutation TransitionContractStatus(
        $contractId: ID!, $newStatus: String!, $activationOptions: ActivationOptionsInput
    ) {
        transitionContractStatus(
            contractId: $contractId, newStatus: $newStatus,
            activationOptions: $activationOptions
        ) {
            success
            error
            contract { id status }
        }
    }
"""

CONTRACT_ORDER_CONFIRMATION_QUERY = """
    query Contract($id: ID!) {
        contract(id: $id) {
            id
            orderConfirmation {
                id
                orderConfirmationNumber
                status
                pdfUrl
            }
        }
    }
"""


@pytest.mark.django_db
class TestActivationWorkflow:
    @pytest.fixture
    def customer(self, tenant):
        return Customer.objects.create(tenant=tenant, name="Test Customer")

    @pytest.fixture
    def draft_contract(self, tenant, customer):
        return Contract.objects.create(
            tenant=tenant, customer=customer, name="Draft Contract",
            status=Contract.Status.DRAFT, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )

    def test_activation_with_send_ab_false(self, user, tenant, draft_contract):
        """Activation with sendOrderConfirmation=false should not create an AB."""
        from apps.contracts.order_confirmation_models import OrderConfirmation

        result = run_graphql(UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION, {
            "contractId": str(draft_contract.id),
            "newStatus": "active",
            "activationOptions": {"sendOrderConfirmation": False},
        }, make_context(user))

        assert result.errors is None
        data = result.data["transitionContractStatus"]
        assert data["success"] is True
        assert data["contract"]["status"] == "active"

        # No OrderConfirmation should exist
        assert not OrderConfirmation.objects.filter(contract=draft_contract).exists()

    def test_activation_with_send_ab_true(self, user, tenant, draft_contract):
        """Activation with sendOrderConfirmation=true should create an AB."""
        from apps.contracts.order_confirmation_models import OrderConfirmation
        from unittest.mock import patch

        # Mock the email task to avoid actual sending
        with patch("apps.contracts.tasks.send_order_confirmation_email_task") as mock_task:
            result = run_graphql(UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION, {
                "contractId": str(draft_contract.id),
                "newStatus": "active",
                "activationOptions": {"sendOrderConfirmation": True},
            }, make_context(user))

        assert result.errors is None
        data = result.data["transitionContractStatus"]
        assert data["success"] is True

        # OrderConfirmation should exist
        ab = OrderConfirmation.objects.filter(contract=draft_contract).first()
        assert ab is not None
        assert ab.order_confirmation_number != ""
        mock_task.delay.assert_called_once()

    def test_activation_options_ignored_for_non_draft(self, user, tenant, customer):
        """activationOptions should be ignored for non-draft→active transitions."""
        from apps.contracts.order_confirmation_models import OrderConfirmation

        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Paused",
            status=Contract.Status.PAUSED, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )
        result = run_graphql(UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION, {
            "contractId": str(contract.id),
            "newStatus": "active",
            "activationOptions": {"sendOrderConfirmation": True},
        }, make_context(user))

        assert result.errors is None
        assert result.data["transitionContractStatus"]["success"] is True
        assert not OrderConfirmation.objects.filter(contract=contract).exists()

    def test_activation_default_creates_ab(self, user, tenant, draft_contract):
        """Activation without activationOptions defaults to creating AB."""
        from apps.contracts.order_confirmation_models import OrderConfirmation
        from unittest.mock import patch

        with patch("apps.contracts.tasks.send_order_confirmation_email_task"):
            result = run_graphql(UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION, {
                "contractId": str(draft_contract.id),
                "newStatus": "active",
            }, make_context(user))

        assert result.errors is None
        assert result.data["transitionContractStatus"]["success"] is True
        assert OrderConfirmation.objects.filter(contract=draft_contract).exists()

    def test_order_confirmation_query_on_contract(self, user, tenant, draft_contract):
        """Contract query should return linked OrderConfirmation."""
        from apps.contracts.order_confirmation_models import OrderConfirmation
        from unittest.mock import patch

        # Activate with AB
        with patch("apps.contracts.tasks.send_order_confirmation_email_task"):
            run_graphql(UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION, {
                "contractId": str(draft_contract.id),
                "newStatus": "active",
                "activationOptions": {"sendOrderConfirmation": True},
            }, make_context(user))

        result = run_graphql(CONTRACT_ORDER_CONFIRMATION_QUERY, {
            "id": str(draft_contract.id),
        }, make_context(user))

        assert result.errors is None
        contract_data = result.data["contract"]
        assert contract_data["orderConfirmation"] is not None
        assert contract_data["orderConfirmation"]["orderConfirmationNumber"] != ""

    def test_checklist_still_blocks_activation(self, user, tenant, draft_contract):
        """Checklist validation still blocks activation with activationOptions."""
        tenant.settings = {"activation_required_fields": ["po_number"]}
        tenant.save(update_fields=["settings"])

        result = run_graphql(UPDATE_CONTRACT_STATUS_WITH_OPTIONS_MUTATION, {
            "contractId": str(draft_contract.id),
            "newStatus": "active",
            "activationOptions": {"sendOrderConfirmation": True},
        }, make_context(user))

        assert result.errors is None
        data = result.data["transitionContractStatus"]
        assert data["success"] is False
        assert "po_number" in data["error"]


# =============================================================================
# Item Dependencies & Delivery Tests
# =============================================================================

MARK_ITEM_DELIVERED_MUTATION = """
    mutation MarkItemDelivered($itemId: ID!, $deliveredAt: Date!) {
        markItemDelivered(itemId: $itemId, deliveredAt: $deliveredAt) {
            success
            error
            dependentItems {
                id
                name
                hasBillingStartDate
            }
        }
    }
"""

REVERT_ITEM_DELIVERY_MUTATION = """
    mutation RevertItemDelivery($itemId: ID!) {
        revertItemDelivery(itemId: $itemId) {
            success
            error
        }
    }
"""

DELIVERABLE_ITEMS_QUERY = """
    query DeliverableItems($status: String, $customerId: ID) {
        deliverableItems(status: $status, customerId: $customerId) {
            id
            productName
            description
            isOneOff
            deliveryStatus
            deliveredAt
            estimatedDeliveryDate
            contractId
            contractName
            customerName
            customerId
            dependentItemsCount
        }
    }
"""

SET_DELIVERABLE_ETA_MUTATION = """
    mutation SetDeliverableEta($itemId: ID!, $estimatedDeliveryDate: Date) {
        setDeliverableEta(itemId: $itemId, estimatedDeliveryDate: $estimatedDeliveryDate) {
            success
            error
        }
    }
"""

UPDATE_ITEM_DEPENDENCY_MUTATION = """
    mutation UpdateContractItem($input: UpdateContractItemInput!) {
        updateContractItem(input: $input) {
            success
            error
            item {
                id
                deliveryStatus
                dependsOn {
                    id
                }
            }
        }
    }
"""


class TestItemDependencies:
    """Tests for item delivery tracking and dependencies."""

    @pytest.fixture
    def active_contract(self, db, tenant, customer):
        return Contract.objects.create(
            tenant=tenant, customer=customer, name="Active Contract",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )

    @pytest.fixture
    def product(self, db, tenant):
        return Product.objects.create(
            tenant=tenant, name="Dev Workshop",
        )

    def test_pending_item_excluded_from_billing(self, db, tenant, active_contract, product):
        """Item with delivery_status='pending' excluded from billing schedule."""
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            billing_start_date=date(2025, 1, 1),
            delivery_status="pending",
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31)
        )
        assert len(schedule) == 0

    def test_delivered_item_included_in_billing(self, db, tenant, active_contract, product):
        """Item with delivery_status='delivered' included in billing schedule."""
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            billing_start_date=date(2025, 3, 1),
            delivery_status="delivered", delivered_at=date(2025, 3, 1),
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31)
        )
        assert len(schedule) == 1
        assert schedule[0]["total"] == Decimal("5000")

    def test_item_blocked_by_pending_dependency(self, db, tenant, active_contract, product):
        """Recurring item depending on pending item excluded from billing."""
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            billing_start_date=date(2025, 1, 1),
            delivery_status="pending",
        )
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
            billing_start_date=date(2025, 1, 1),
            depends_on=one_off,
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31)
        )
        assert len(schedule) == 0

    def test_item_unblocked_after_dependency_delivered(self, db, tenant, active_contract, product):
        """Recurring item depending on delivered item included in billing."""
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            billing_start_date=date(2025, 1, 1),
            delivery_status="delivered", delivered_at=date(2025, 1, 15),
        )
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
            billing_start_date=date(2025, 2, 1),
            depends_on=one_off,
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31)
        )
        # Should include both: one-off on Jan 1 and recurring monthly from Feb
        assert len(schedule) > 0
        all_item_ids = set()
        for event in schedule:
            for item_info in event["items"]:
                all_item_ids.add(item_info["item_id"])
        assert len(all_item_ids) == 2

    def test_mark_item_delivered_mutation(self, user, tenant, active_contract, product):
        """mark_item_delivered sets status and date, returns dependents."""
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="pending",
        )
        dep = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
            depends_on=one_off,
        )

        result = run_graphql(MARK_ITEM_DELIVERED_MUTATION, {
            "itemId": str(one_off.id),
            "deliveredAt": "2025-03-15",
        }, make_context(user))

        assert result.errors is None
        data = result.data["markItemDelivered"]
        assert data["success"] is True
        assert len(data["dependentItems"]) == 1
        assert data["dependentItems"][0]["id"] == dep.id

        one_off.refresh_from_db()
        assert one_off.delivery_status == "delivered"
        assert one_off.delivered_at == date(2025, 3, 15)

    def test_revert_item_delivery_mutation(self, user, tenant, active_contract, product):
        """revert_item_delivery clears status and date."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="delivered", delivered_at=date(2025, 3, 15),
        )

        result = run_graphql(REVERT_ITEM_DELIVERY_MUTATION, {
            "itemId": str(item.id),
        }, make_context(user))

        assert result.errors is None
        data = result.data["revertItemDelivery"]
        assert data["success"] is True

        item.refresh_from_db()
        assert item.delivery_status == "pending"
        assert item.delivered_at is None

    def test_dependency_must_be_same_contract(self, user, tenant, customer, product):
        """Setting dependency to item in different contract is rejected."""
        contract_a = Contract.objects.create(
            tenant=tenant, customer=customer, name="Contract A",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )
        contract_b = Contract.objects.create(
            tenant=tenant, customer=customer, name="Contract B",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )
        item_a = ContractItem.objects.create(
            tenant=tenant, contract=contract_a, product=product,
            quantity=1, unit_price=Decimal("100"),
        )
        item_b = ContractItem.objects.create(
            tenant=tenant, contract=contract_b, product=product,
            quantity=1, unit_price=Decimal("100"),
        )

        result = run_graphql(UPDATE_ITEM_DEPENDENCY_MUTATION, {
            "input": {"id": str(item_a.id), "dependsOnItemId": str(item_b.id)},
        }, make_context(user))

        assert result.errors is None
        data = result.data["updateContractItem"]
        assert data["success"] is False
        assert "not found in this contract" in data["error"]

    def test_self_dependency_rejected(self, user, tenant, active_contract, product):
        """Setting dependency to itself is rejected."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
        )

        result = run_graphql(UPDATE_ITEM_DEPENDENCY_MUTATION, {
            "input": {"id": str(item.id), "dependsOnItemId": str(item.id)},
        }, make_context(user))

        assert result.errors is None
        data = result.data["updateContractItem"]
        assert data["success"] is False
        assert "cannot depend on itself" in data["error"]

    def test_deleting_dependency_target_sets_null(self, db, tenant, active_contract, product):
        """Deleting dependency target sets depends_on=NULL on dependents."""
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="pending",
        )
        dep = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
            depends_on=one_off,
        )
        one_off.delete()
        dep.refresh_from_db()
        assert dep.depends_on is None

    def test_deliverable_items_query(self, user, tenant, active_contract, product):
        """deliverable_items returns correct items with filters."""
        pending = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="pending",
        )
        delivered = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("3000"), is_one_off=True,
            delivery_status="delivered", delivered_at=date(2025, 2, 1),
        )
        # Normal item without delivery tracking — should NOT appear
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
        )

        # Query all
        result = run_graphql(DELIVERABLE_ITEMS_QUERY, {}, make_context(user))
        assert result.errors is None
        items = result.data["deliverableItems"]
        assert len(items) == 2

        # Query pending only
        result = run_graphql(DELIVERABLE_ITEMS_QUERY, {
            "status": "pending",
        }, make_context(user))
        assert result.errors is None
        items = result.data["deliverableItems"]
        assert len(items) == 1
        assert items[0]["id"] == pending.id

        # Query delivered only
        result = run_graphql(DELIVERABLE_ITEMS_QUERY, {
            "status": "delivered",
        }, make_context(user))
        assert result.errors is None
        items = result.data["deliverableItems"]
        assert len(items) == 1
        assert items[0]["id"] == delivered.id


class TestDeliverableEta:
    """Tests for estimated delivery date on contract items."""

    @pytest.fixture
    def active_contract(self, db, tenant, customer):
        return Contract.objects.create(
            tenant=tenant, customer=customer, name="ETA Test Contract",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )

    def test_eta_saved_and_cleared_on_model(self, db, tenant, active_contract, product):
        """ETA field can be set and cleared on ContractItem."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="pending",
            estimated_delivery_date=date(2025, 6, 1),
        )
        assert item.estimated_delivery_date == date(2025, 6, 1)
        item.estimated_delivery_date = None
        item.save()
        item.refresh_from_db()
        assert item.estimated_delivery_date is None

    def test_eta_cleared_on_delivery(self, user, tenant, active_contract, product):
        """ETA is cleared when item is marked as delivered."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="pending",
            estimated_delivery_date=date(2025, 6, 1),
        )
        result = run_graphql(MARK_ITEM_DELIVERED_MUTATION, {
            "itemId": str(item.id),
            "deliveredAt": "2025-06-15",
        }, make_context(user))
        assert result.errors is None
        assert result.data["markItemDelivered"]["success"] is True
        item.refresh_from_db()
        assert item.estimated_delivery_date is None
        assert item.delivery_status == "delivered"

    def test_forecast_includes_pending_with_eta(self, db, tenant, active_contract, product):
        """Pending item with ETA included in forecast billing schedule."""
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("10000"), is_one_off=True,
            billing_start_date=date(2025, 6, 1),
            delivery_status="pending",
            estimated_delivery_date=date(2025, 6, 1),
        )
        # Without forecast mode: excluded
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
        )
        assert len(schedule) == 0

        # With forecast mode: included
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
            include_eta_items=True,
        )
        assert len(schedule) == 1
        assert schedule[0]["total"] == Decimal("10000")

    def test_forecast_excludes_pending_without_eta(self, db, tenant, active_contract, product):
        """Pending item without ETA excluded from forecast."""
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("10000"), is_one_off=True,
            billing_start_date=date(2025, 6, 1),
            delivery_status="pending",
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
            include_eta_items=True,
        )
        assert len(schedule) == 0

    def test_invoice_independent_pending_item_is_billed(self, db, tenant, active_contract, product):
        """Pending item flagged as invoice_independent is billed anyway (e.g. upfront payment)."""
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("10000"), is_one_off=True,
            billing_start_date=date(2025, 6, 1),
            delivery_status="pending",
            invoice_independent=True,
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
        )
        assert len(schedule) == 1
        assert schedule[0]["total"] == Decimal("10000")

    def test_invoice_independent_dependent_not_blocked_by_pending_dependency(
        self, db, tenant, active_contract, product
    ):
        """invoice_independent bypasses dependency blocking too."""
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            billing_start_date=date(2025, 3, 1),
            delivery_status="pending",
        )
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
            billing_start_date=date(2025, 1, 1),
            depends_on=one_off,
            invoice_independent=True,
        )
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
        )
        # recurring is billed every month (12 entries) despite pending dependency
        assert len(schedule) == 12

    def test_invoice_independent_included_in_recognition_schedule(
        self, db, tenant, active_contract, product
    ):
        """Recognition schedule also honors invoice_independent flag."""
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("10000"), is_one_off=True,
            billing_start_date=date(2025, 6, 1),
            delivery_status="pending",
            invoice_independent=True,
        )
        schedule = active_contract.get_recognition_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
        )
        assert len(schedule) >= 1

    def test_dependent_item_included_when_dependency_has_eta(self, db, tenant, active_contract, product):
        """Recurring item with pending dependency included when dependency has ETA."""
        one_off = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            billing_start_date=date(2025, 3, 1),
            delivery_status="pending",
            estimated_delivery_date=date(2025, 6, 1),
        )
        ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("100"),
            billing_start_date=date(2025, 1, 1),
            depends_on=one_off,
        )
        # Without forecast mode: nothing
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
        )
        assert len(schedule) == 0

        # With forecast mode: both items included, recurring starts from ETA
        schedule = active_contract.get_billing_schedule(
            from_date=date(2025, 1, 1), to_date=date(2025, 12, 31),
            include_eta_items=True,
        )
        assert len(schedule) > 0
        # The one-off should appear at ETA date
        one_off_events = [e for e in schedule if any(
            i["item_id"] == one_off.id for i in e["items"]
        )]
        assert len(one_off_events) >= 1

    def test_set_deliverable_eta_mutation(self, user, tenant, active_contract, product):
        """set_deliverable_eta sets and clears ETA on pending item."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"), is_one_off=True,
            delivery_status="pending",
        )
        # Set ETA
        result = run_graphql(SET_DELIVERABLE_ETA_MUTATION, {
            "itemId": str(item.id),
            "estimatedDeliveryDate": "2025-06-01",
        }, make_context(user))
        assert result.errors is None
        assert result.data["setDeliverableEta"]["success"] is True
        item.refresh_from_db()
        assert item.estimated_delivery_date == date(2025, 6, 1)

        # Clear ETA
        result = run_graphql(SET_DELIVERABLE_ETA_MUTATION, {
            "itemId": str(item.id),
            "estimatedDeliveryDate": None,
        }, make_context(user))
        assert result.errors is None
        assert result.data["setDeliverableEta"]["success"] is True
        item.refresh_from_db()
        assert item.estimated_delivery_date is None

    def test_set_deliverable_eta_rejects_non_tracking(self, user, tenant, active_contract, product):
        """set_deliverable_eta rejects items without delivery tracking."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=active_contract, product=product,
            quantity=1, unit_price=Decimal("5000"),
        )
        result = run_graphql(SET_DELIVERABLE_ETA_MUTATION, {
            "itemId": str(item.id),
            "estimatedDeliveryDate": "2025-06-01",
        }, make_context(user))
        assert result.errors is None
        assert result.data["setDeliverableEta"]["success"] is False
        assert "delivery tracking" in result.data["setDeliverableEta"]["error"]


# =============================================================================
# Contract Merge Tests
# =============================================================================

MERGE_PREVIEW_QUERY = """
    query MergePreview($sourceId: ID!, $targetId: ID!) {
        mergeContractPreview(sourceContractId: $sourceId, targetContractId: $targetId) {
            items {
                id
                productName
                quantity
                unitPrice
                isOneOff
            }
            willCreateAmendments
            sourceContractName
            targetContractName
            errors
        }
    }
"""

MERGE_MUTATION = """
    mutation MergeContract($input: MergeContractInput!) {
        mergeContract(input: $input) {
            success
            errors
            itemsTransferred
            contract {
                id
                name
            }
        }
    }
"""


class TestMergeContractPreview:
    def test_preview_returns_items(self, user, tenant, customer, product):
        source = Contract.objects.create(
            tenant=tenant, customer=customer, name="Source",
            status=Contract.Status.DRAFT, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        target = Contract.objects.create(
            tenant=tenant, customer=customer, name="Target",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=source, product=product,
            quantity=2, unit_price=Decimal("100.00"),
        )

        result = run_graphql(MERGE_PREVIEW_QUERY, {
            "sourceId": str(source.id), "targetId": str(target.id),
        }, make_context(user))

        assert result.errors is None
        data = result.data["mergeContractPreview"]
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["willCreateAmendments"] is True
        assert data["errors"] == []

    def test_preview_returns_errors_for_invalid_merge(self, user, tenant, customer):
        source = Contract.objects.create(
            tenant=tenant, customer=customer, name="Source",
            status=Contract.Status.PAUSED, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        target = Contract.objects.create(
            tenant=tenant, customer=customer, name="Target",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        result = run_graphql(MERGE_PREVIEW_QUERY, {
            "sourceId": str(source.id), "targetId": str(target.id),
        }, make_context(user))

        assert result.errors is None
        data = result.data["mergeContractPreview"]
        assert len(data["errors"]) > 0
        assert "Only draft or active" in data["errors"][0]


class TestMergeContractMutation:
    def test_merge_success(self, user, tenant, customer, product):
        source = Contract.objects.create(
            tenant=tenant, customer=customer, name="Source Draft",
            status=Contract.Status.DRAFT, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        target = Contract.objects.create(
            tenant=tenant, customer=customer, name="Target Active",
            status=Contract.Status.ACTIVE, start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=source, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        result = run_graphql(MERGE_MUTATION, {
            "input": {
                "sourceContractId": str(source.id),
                "targetContractId": str(target.id),
            },
        }, make_context(user))

        assert result.errors is None
        data = result.data["mergeContract"]
        assert data["success"] is True
        assert data["itemsTransferred"] == 1
        assert data["contract"]["name"] == "Target Active"

        source.refresh_from_db()
        assert source.status == Contract.Status.DELETED

    def test_merge_with_date_overrides(self, user, tenant, customer, product):
        source = Contract.objects.create(
            tenant=tenant, customer=customer, name="Source",
            status=Contract.Status.DRAFT, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        target = Contract.objects.create(
            tenant=tenant, customer=customer, name="Target",
            status=Contract.Status.DRAFT, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        item = ContractItem.objects.create(
            tenant=tenant, contract=source, product=product,
            quantity=1, unit_price=Decimal("100.00"),
            start_date=date(2026, 1, 1),
        )

        result = run_graphql(MERGE_MUTATION, {
            "input": {
                "sourceContractId": str(source.id),
                "targetContractId": str(target.id),
                "itemOverrides": [
                    {"itemId": item.id, "startDate": "2026-06-01"},
                ],
            },
        }, make_context(user))

        assert result.errors is None
        assert result.data["mergeContract"]["success"] is True

        item.refresh_from_db()
        assert item.start_date == date(2026, 6, 1)

    def test_merge_fails_for_invalid_preconditions(self, user, tenant, customer):
        contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Self",
            status=Contract.Status.DRAFT, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        result = run_graphql(MERGE_MUTATION, {
            "input": {
                "sourceContractId": str(contract.id),
                "targetContractId": str(contract.id),
            },
        }, make_context(user))

        assert result.errors is None
        data = result.data["mergeContract"]
        assert data["success"] is False
        assert len(data["errors"]) > 0
