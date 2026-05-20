"""Tests for time tracking mapping mutations."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from config.schema import schema
from apps.contracts.models import Contract, ContractItem, TimeTrackingProjectMapping
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
def viewer_user(db, tenant):
    """Create a user with Viewer role (no contracts.write permission)."""
    u = User.objects.create_user(
        email="viewer@example.com",
        password="view123",
        tenant=tenant,
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    u.roles.add(viewer_role)
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
def customer_with_clockodo(db, tenant):
    """Create a test customer linked to Clockodo."""
    return Customer.objects.create(
        tenant=tenant,
        name="Clockodo Customer",
        is_active=True,
        clockodo_customer_id="CK-999",
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
def contract(db, tenant, customer):
    """Create a test contract."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Test Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.ANNUAL,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_with_clockodo(db, tenant, customer_with_clockodo):
    """Create a test contract whose customer is linked to Clockodo."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer_with_clockodo,
        name="Clockodo Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_item(db, tenant, contract, product):
    """Create a contract item belonging to the test contract."""
    return ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        product=product,
        quantity=1,
        unit_price=Decimal("100.00"),
    )


@pytest.fixture
def contract_item_clockodo(db, tenant, contract_with_clockodo, product):
    """Create a contract item belonging to the clockodo-linked contract."""
    return ContractItem.objects.create(
        tenant=tenant,
        contract=contract_with_clockodo,
        product=product,
        quantity=1,
        unit_price=Decimal("200.00"),
    )


# ---------------------------------------------------------------------------
# GraphQL fragments
# ---------------------------------------------------------------------------

MAP_TIME_TRACKING_PROJECT_MUTATION = """
    mutation MapTimeTrackingProject(
        $contractId: ID!,
        $externalProjectId: String!,
        $externalProjectName: String!,
        $externalCustomerName: String,
        $contractItemId: ID
    ) {
        mapTimeTrackingProject(
            contractId: $contractId,
            externalProjectId: $externalProjectId,
            externalProjectName: $externalProjectName,
            externalCustomerName: $externalCustomerName,
            contractItemId: $contractItemId
        ) {
            success
            error
            mapping {
                id
                externalProjectId
                externalProjectName
                externalCustomerName
                contractItemId
                contractItemName
                cachedTotalHours
            }
        }
    }
"""

CREATE_CLOCKODO_PROJECT_MUTATION = """
    mutation CreateClockodoProjectForContract(
        $contractId: ID!,
        $projectName: String!,
        $contractItemId: ID
    ) {
        createClockodoProjectForContract(
            contractId: $contractId,
            projectName: $projectName,
            contractItemId: $contractItemId
        ) {
            success
            error
            mapping {
                id
                externalProjectId
                externalProjectName
                externalCustomerName
                contractItemId
                contractItemName
                cachedTotalHours
            }
        }
    }
"""


# ===========================================================================
# map_time_tracking_project tests
# ===========================================================================


class TestMapTimeTrackingProject:
    """Tests for the mapTimeTrackingProject mutation."""

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    def test_successfully_maps_project_to_contract(self, mock_sync, user, contract):
        """Mapping with valid data creates a TimeTrackingProjectMapping."""
        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "externalProjectId": "ext-123",
                "externalProjectName": "External Project",
                "externalCustomerName": "External Customer",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is True
        assert data["error"] is None
        assert data["mapping"]["externalProjectId"] == "ext-123"
        assert data["mapping"]["externalProjectName"] == "External Project"
        assert data["mapping"]["externalCustomerName"] == "External Customer"
        assert data["mapping"]["contractItemId"] is None
        assert data["mapping"]["contractItemName"] is None
        assert data["mapping"]["cachedTotalHours"] == 0

        # Verify DB record
        mapping = TimeTrackingProjectMapping.objects.get(
            tenant=user.tenant, external_project_id="ext-123"
        )
        assert mapping.contract == contract
        assert mapping.contract_item is None
        assert mapping.link_source == TimeTrackingProjectMapping.LinkSource.MANUAL

        # Verify async sync was triggered
        mock_sync.assert_called_once_with(mapping.id)

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    def test_maps_project_with_contract_item(
        self, mock_sync, user, contract, contract_item
    ):
        """Mapping with a valid contract_item_id links the item."""
        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "externalProjectId": "ext-456",
                "externalProjectName": "Item Project",
                "contractItemId": str(contract_item.id),
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is True
        assert data["mapping"]["contractItemId"] == contract_item.id
        assert data["mapping"]["contractItemName"] == "Test Product"

        mapping = TimeTrackingProjectMapping.objects.get(
            tenant=user.tenant, external_project_id="ext-456"
        )
        assert mapping.contract_item == contract_item

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    def test_rejects_duplicate_external_project_id(
        self, mock_sync, user, tenant, contract
    ):
        """Mapping the same external_project_id twice returns an error."""
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=contract,
            external_project_id="dup-100",
            external_project_name="Already Mapped",
        )

        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "externalProjectId": "dup-100",
                "externalProjectName": "Duplicate Attempt",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is False
        assert "already linked" in data["error"]

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    def test_rejects_contract_item_from_different_contract(
        self, mock_sync, user, tenant, contract, customer, product
    ):
        """An item belonging to a different contract is rejected."""
        other_contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Other Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        other_item = ContractItem.objects.create(
            tenant=tenant,
            contract=other_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("50.00"),
        )

        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "externalProjectId": "ext-789",
                "externalProjectName": "Mismatched Item",
                "contractItemId": str(other_item.id),
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is False
        assert data["error"] == "Item not found in this contract"

    def test_contract_not_found_returns_error(self, user):
        """A non-existent contract ID returns an error."""
        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": "99999",
                "externalProjectId": "ext-000",
                "externalProjectName": "Ghost Contract",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is False
        assert data["error"] == "Contract not found"

    def test_permission_denied_for_viewer(self, viewer_user, contract):
        """A Viewer user (no contracts.write) is rejected."""
        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "externalProjectId": "ext-no-perm",
                "externalProjectName": "No Permission",
            },
            make_context(viewer_user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is False
        assert data["error"] == "Permission denied"

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    def test_default_external_customer_name_is_empty(
        self, mock_sync, user, contract
    ):
        """When externalCustomerName is omitted, it defaults to empty string."""
        result = run_graphql(
            MAP_TIME_TRACKING_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "externalProjectId": "ext-default",
                "externalProjectName": "Default Customer Name",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is True
        assert data["mapping"]["externalCustomerName"] == ""

        mapping = TimeTrackingProjectMapping.objects.get(
            external_project_id="ext-default"
        )
        assert mapping.external_customer_name == ""


# ===========================================================================
# create_clockodo_project_for_contract tests
# ===========================================================================


class TestCreateClockodoProjectForContract:
    """Tests for the createClockodoProjectForContract mutation."""

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_customer_not_linked_to_clockodo_returns_error(
        self, mock_get_provider, mock_sync, user, contract
    ):
        """Contract whose customer lacks clockodo_customer_id is rejected."""
        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract.id),
                "projectName": "New Project",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert data["error"] == "Customer is not linked to Clockodo"
        mock_get_provider.assert_not_called()

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_maintenance_mapping_exists_requires_contract_item(
        self, mock_get_provider, mock_sync, user, tenant, contract_with_clockodo
    ):
        """When a maintenance mapping (contract_item=None) exists, omitting
        contract_item_id returns an error."""
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=contract_with_clockodo,
            contract_item=None,
            external_project_id="maintenance-1",
            external_project_name="Maintenance",
        )

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "Second Project",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert "maintenance project already exists" in data["error"].lower()
        mock_get_provider.assert_not_called()

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_maintenance_mapping_exists_succeeds_with_contract_item(
        self,
        mock_get_provider,
        mock_sync,
        user,
        tenant,
        contract_with_clockodo,
        contract_item_clockodo,
    ):
        """When a maintenance mapping exists, providing contract_item_id succeeds."""
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=contract_with_clockodo,
            contract_item=None,
            external_project_id="maintenance-2",
            external_project_name="Maintenance",
        )

        mock_provider = Mock()
        mock_provider.create_project.return_value = {
            "id": "12345",
            "name": "Test Project",
        }
        mock_get_provider.return_value = mock_provider

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "Test Project",
                "contractItemId": str(contract_item_clockodo.id),
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is True
        assert data["mapping"]["externalProjectId"] == "12345"
        assert data["mapping"]["externalProjectName"] == "Test Project"
        assert data["mapping"]["externalCustomerName"] == "Clockodo Customer"
        assert data["mapping"]["contractItemId"] == contract_item_clockodo.id

        mock_provider.create_project.assert_called_once_with(
            "CK-999", "Test Project"
        )
        mock_sync.assert_called_once()

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_no_maintenance_mapping_works_without_contract_item(
        self, mock_get_provider, mock_sync, user, contract_with_clockodo
    ):
        """When no maintenance mapping exists, contract_item_id is optional."""
        mock_provider = Mock()
        mock_provider.create_project.return_value = {
            "id": "67890",
            "name": "First Project",
        }
        mock_get_provider.return_value = mock_provider

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "First Project",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is True
        assert data["mapping"]["externalProjectId"] == "67890"
        assert data["mapping"]["externalProjectName"] == "First Project"
        assert data["mapping"]["contractItemId"] is None

        mapping = TimeTrackingProjectMapping.objects.get(
            tenant=user.tenant, external_project_id="67890"
        )
        assert mapping.contract == contract_with_clockodo
        assert mapping.contract_item is None
        assert mapping.external_customer_name == "Clockodo Customer"
        assert mapping.link_source == TimeTrackingProjectMapping.LinkSource.MANUAL

    def test_permission_denied_for_viewer(self, viewer_user, contract_with_clockodo):
        """A Viewer user (no contracts.write) is rejected."""
        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "Denied",
            },
            make_context(viewer_user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert data["error"] == "Permission denied"

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_no_time_tracking_provider_configured(
        self, mock_get_provider, mock_sync, user, contract_with_clockodo
    ):
        """When get_provider returns None, the mutation returns an error."""
        mock_get_provider.return_value = None

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "No Provider",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert data["error"] == "No time tracking provider configured"

    def test_contract_not_found_returns_error(self, user):
        """A non-existent contract ID returns an error."""
        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": "99999",
                "projectName": "Ghost Contract",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert data["error"] == "Contract not found"

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_contract_item_from_different_contract_rejected(
        self,
        mock_get_provider,
        mock_sync,
        user,
        tenant,
        contract_with_clockodo,
        customer_with_clockodo,
        product,
    ):
        """An item belonging to a different contract is rejected."""
        other_contract = Contract.objects.create(
            tenant=tenant,
            customer=customer_with_clockodo,
            name="Other Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        other_item = ContractItem.objects.create(
            tenant=tenant,
            contract=other_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("75.00"),
        )

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "Mismatched",
                "contractItemId": str(other_item.id),
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert data["error"] == "Item not found in this contract"
        mock_get_provider.assert_not_called()

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_clockodo_api_failure_returns_error(
        self, mock_get_provider, mock_sync, user, contract_with_clockodo
    ):
        """When the Clockodo API raises an exception, the error is returned."""
        mock_provider = Mock()
        mock_provider.create_project.side_effect = Exception("API timeout")
        mock_get_provider.return_value = mock_provider

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "Failing Project",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is False
        assert "Failed to create Clockodo project" in data["error"]
        assert "API timeout" in data["error"]

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task.delay")
    @patch("apps.contracts.services.time_tracking.get_provider")
    def test_project_name_is_stripped(
        self, mock_get_provider, mock_sync, user, contract_with_clockodo
    ):
        """The project_name is stripped of leading/trailing whitespace before
        being passed to the provider."""
        mock_provider = Mock()
        mock_provider.create_project.return_value = {
            "id": "strip-1",
            "name": "Trimmed Name",
        }
        mock_get_provider.return_value = mock_provider

        result = run_graphql(
            CREATE_CLOCKODO_PROJECT_MUTATION,
            {
                "contractId": str(contract_with_clockodo.id),
                "projectName": "  Trimmed Name  ",
            },
            make_context(user),
        )

        assert result.errors is None
        data = result.data["createClockodoProjectForContract"]
        assert data["success"] is True

        mock_provider.create_project.assert_called_once_with(
            "CK-999", "Trimmed Name"
        )
