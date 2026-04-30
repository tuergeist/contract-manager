"""Tests for Clockodo project provisioning on contract activation."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from apps.contracts.models import Contract, ContractItem, TimeTrackingProjectMapping
from apps.contracts.services.clockodo_provisioning import (
    preview_activation,
    provision_projects,
    render_template,
)
from apps.contracts.services.time_tracking import TimeTrackingProject
from apps.core.context import Context
from config.schema import schema


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def customer(db, tenant):
    from apps.customers.models import Customer
    return Customer.objects.create(
        tenant=tenant, name="Acme Corp", is_active=True,
        clockodo_customer_id="42",
    )


@pytest.fixture
def customer_unlinked(db, tenant):
    from apps.customers.models import Customer
    return Customer.objects.create(
        tenant=tenant, name="Unlinked Corp", is_active=True,
    )


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant, customer=customer, name="Service Contract",
        status=Contract.Status.DRAFT, start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1), billing_interval="monthly",
        billing_anchor_day=1,
    )


@pytest.fixture
def recurring_item(db, tenant, contract):
    return ContractItem.objects.create(
        tenant=tenant, contract=contract, description="Monthly Support",
        quantity=1, unit_price=Decimal("1000"), price_period="monthly",
        is_one_off=False,
    )


@pytest.fixture
def oneoff_item(db, tenant, contract):
    return ContractItem.objects.create(
        tenant=tenant, contract=contract, description="Initial Setup",
        quantity=1, unit_price=Decimal("5000"), price_period="once",
        is_one_off=True,
    )


class TestRenderTemplate:
    def test_basic(self):
        assert render_template("Wartung {customer_name}", customer_name="Acme") == "Wartung Acme"

    def test_multiple_placeholders(self):
        result = render_template("{customer_name} - {contract_name}", customer_name="Acme", contract_name="Q1")
        assert result == "Acme - Q1"

    def test_year_placeholder(self):
        result = render_template("{customer_name} {year}", customer_name="Acme")
        assert str(date.today().year) in result

    def test_fallback_uses_first_non_empty(self):
        # contract_name set → use it, ignore item_name
        assert render_template(
            "{contract_name|item_name}",
            contract_name="Wartung Q1", item_name="Item A",
        ) == "Wartung Q1"

    def test_fallback_falls_through_when_first_empty(self):
        assert render_template(
            "{contract_name|item_name}",
            contract_name="", item_name="Item A",
        ) == "Item A"

    def test_fallback_chain_three_alternatives(self):
        assert render_template(
            "{contract_name|item_name|customer_name}",
            contract_name="", item_name="", customer_name="Acme",
        ) == "Acme"

    def test_fallback_all_empty(self):
        assert render_template(
            "{contract_name|item_name}",
            contract_name="", item_name="",
        ) == ""

    def test_length_limit_truncates(self):
        long_name = "A very very very long contract name that exceeds thirty chars"
        assert render_template(
            "{contract_name:30}", contract_name=long_name,
        ) == long_name[:30].rstrip()

    def test_length_limit_short_value_unchanged(self):
        assert render_template(
            "{contract_name:30}", contract_name="Short",
        ) == "Short"

    def test_fallback_with_length_limit(self):
        assert render_template(
            "{contract_name|item_name:30}",
            contract_name="", item_name="A" * 50,
        ) == "A" * 30

    def test_invalid_length_specifier_treated_literal(self):
        # "abc" is not numeric → no truncation, key "missing:abc" not found → empty
        result = render_template("{missing:abc}", missing="value")
        assert result == ""

    def test_combined_realistic_template(self):
        # Per-Item one-off project name, falling back to item description, max 30 chars
        item = "Implementierung neuer Modulbaustein"
        result = render_template(
            "{customer_name} - {contract_name|item_name:30}",
            customer_name="Acme GmbH", contract_name="", item_name=item,
        )
        assert result == f"Acme GmbH - {item[:30].rstrip()}"


class TestPreviewActivation:
    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    def test_no_provider(self, mock_provider, contract, recurring_item):
        mock_provider.return_value = None
        result = preview_activation(contract)
        assert result["clockodo_configured"] is False
        assert result["maintenance_needed"] is True

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    def test_customer_not_linked(self, mock_provider, contract, customer_unlinked, recurring_item):
        contract.customer = customer_unlinked
        contract.save()
        mock_provider.return_value = Mock()
        result = preview_activation(contract)
        assert result["customer_linked"] is False

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    def test_maintenance_needed(self, mock_provider, contract, recurring_item):
        provider = Mock()
        provider.get_customer_projects.return_value = []
        mock_provider.return_value = provider
        result = preview_activation(contract)
        assert result["maintenance_needed"] is True
        assert result["maintenance_project_exists"] is False
        assert "Wartung Acme" in result["maintenance_project_name"]

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    def test_maintenance_exists(self, mock_provider, contract, recurring_item):
        provider = Mock()
        provider.get_customer_projects.return_value = [
            TimeTrackingProject(id="99", name="Wartung Acme Corp", customer_name="Acme", active=True)
        ]
        mock_provider.return_value = provider
        result = preview_activation(contract)
        assert result["maintenance_project_exists"] is True

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    def test_oneoff_items_listed(self, mock_provider, contract, oneoff_item):
        provider = Mock()
        provider.get_customer_projects.return_value = []
        mock_provider.return_value = provider
        result = preview_activation(contract)
        assert len(result["one_off_items"]) == 1
        assert result["one_off_items"][0]["description"] == "Initial Setup"


class TestProvisionProjects:
    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_creates_maintenance_project(self, mock_sync, mock_provider, contract, recurring_item):
        mock_sync.delay = MagicMock()
        provider = Mock()
        provider.get_customer_projects.return_value = []
        provider.create_project.return_value = {"id": "100", "name": "Wartung Acme Corp"}
        mock_provider.return_value = provider

        result = provision_projects(contract, create_maintenance=True, oneoff_strategy="skip")
        assert result["success"] is True
        assert len(result["created_projects"]) == 1
        assert result["created_projects"][0]["action"] == "created"

        mapping = TimeTrackingProjectMapping.objects.get(external_project_id="100")
        assert mapping.contract == contract
        assert mapping.link_source == "auto"

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_links_existing_maintenance(self, mock_sync, mock_provider, contract, recurring_item):
        mock_sync.delay = MagicMock()
        provider = Mock()
        provider.get_customer_projects.return_value = [
            TimeTrackingProject(id="99", name="Wartung Acme Corp", customer_name="Acme", active=True)
        ]
        mock_provider.return_value = provider

        result = provision_projects(contract, create_maintenance=True, oneoff_strategy="skip")
        assert result["success"] is True
        assert result["created_projects"][0]["action"] == "linked"

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_combined_oneoff(self, mock_sync, mock_provider, contract, oneoff_item):
        mock_sync.delay = MagicMock()
        provider = Mock()
        provider.get_customer_projects.return_value = []
        provider.create_project.return_value = {"id": "101", "name": "Acme Corp - Service Contract"}
        mock_provider.return_value = provider

        result = provision_projects(contract, create_maintenance=False, oneoff_strategy="combined")
        assert result["success"] is True
        assert len(result["created_projects"]) == 1
        assert TimeTrackingProjectMapping.objects.filter(external_project_id="101").exists()

    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_per_item_oneoff(self, mock_sync, mock_provider, contract, oneoff_item):
        mock_sync.delay = MagicMock()
        # Add a second one-off item
        oneoff2 = ContractItem.objects.create(
            tenant=contract.tenant, contract=contract, description="Migration",
            quantity=1, unit_price=Decimal("3000"), price_period="once", is_one_off=True,
        )

        provider = Mock()
        provider.get_customer_projects.return_value = []
        provider.create_project.side_effect = [
            {"id": "201", "name": "Acme - Setup"},
            {"id": "202", "name": "Acme - Migration"},
        ]
        mock_provider.return_value = provider

        result = provision_projects(contract, create_maintenance=False, oneoff_strategy="per_item")
        assert result["success"] is True
        assert len(result["created_projects"]) == 2

    def test_no_provider(self, contract):
        with patch("apps.contracts.services.clockodo_provisioning.get_provider", return_value=None):
            result = provision_projects(contract)
        assert result["success"] is False

    def test_customer_not_linked(self, contract, customer_unlinked):
        contract.customer = customer_unlinked
        contract.save()
        with patch("apps.contracts.services.clockodo_provisioning.get_provider", return_value=Mock()):
            result = provision_projects(contract)
        assert result["success"] is False


PREVIEW_QUERY = """
query($contractId: ID!) {
  previewContractActivation(contractId: $contractId) {
    clockodoConfigured
    customerLinked
    maintenanceNeeded
    maintenanceProjectExists
    maintenanceProjectName
    oneOffItems { id description }
  }
}
"""


class TestPreviewGraphQL:
    @patch("apps.contracts.services.clockodo_provisioning.get_provider")
    def test_preview_query(self, mock_provider, user, contract, recurring_item, oneoff_item):
        provider = Mock()
        provider.get_customer_projects.return_value = []
        mock_provider.return_value = provider

        result = run_graphql(PREVIEW_QUERY, {"contractId": str(contract.id)}, make_context(user))
        assert result.errors is None
        data = result.data["previewContractActivation"]
        assert data["clockodoConfigured"] is True
        assert data["customerLinked"] is True
        assert data["maintenanceNeeded"] is True
        assert len(data["oneOffItems"]) == 1
