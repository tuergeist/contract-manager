"""GraphQL tests for the Projects overview (deliverable one-off items)."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from config.schema import schema
from apps.contracts.models import Contract, ContractItem, TimeTrackingProjectMapping
from apps.customers.models import Customer
from apps.tenants.models import Role, Tenant, User
from apps.core.context import Context


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    return Context(request=Mock(), user=user)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        email="test@example.com", password="testpass123", tenant=tenant
    )
    u.roles.add(Role.objects.get(tenant=tenant, name="Admin"))
    return u


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(tenant=tenant, name="Test Customer", is_active=True)


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Project Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
    )


DELIVERABLE_QUERY = """
    query {
        deliverableItems {
            id
            isOneOff
            deliveryStatus
            hoursBooked
            orderValue
            orderConfirmationNumber
            psRatio
        }
    }
"""


class TestDeliverableItems:
    def test_one_off_deliverable_appears_with_metrics(self, user, tenant, contract):
        """One-off deliverable item shows hours, order value and PS ratio."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Custom development",
            quantity=1,
            unit_price=Decimal("8000.00"),
            is_one_off=True,
            delivery_status="pending",
            order_confirmation_number="AB-2025-0001",
        )
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=contract,
            contract_item=item,
            external_project_id="ext-1",
            external_project_name="Ext Project",
            cached_total_hours=20.0,
        )

        result = run_graphql(DELIVERABLE_QUERY, {}, make_context(user))

        assert result.errors is None
        items = result.data["deliverableItems"]
        assert len(items) == 1
        row = items[0]
        assert row["hoursBooked"] == 20.0
        assert row["orderValue"] == 8000.0
        assert row["orderConfirmationNumber"] == "AB-2025-0001"
        # 8000 / (20 * 160) = 2.5
        assert row["psRatio"] == pytest.approx(2.5)

    def test_recurring_deliverable_excluded(self, user, tenant, contract):
        """Recurring (non one-off) deliverable items are not projects."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Monthly service",
            quantity=1,
            unit_price=Decimal("100.00"),
            is_one_off=False,
            delivery_status="pending",
        )

        result = run_graphql(DELIVERABLE_QUERY, {}, make_context(user))

        assert result.errors is None
        assert result.data["deliverableItems"] == []

    def test_ps_ratio_null_without_hours(self, user, tenant, contract):
        """PS ratio is null when no hours are booked."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Untracked work",
            quantity=2,
            unit_price=Decimal("500.00"),
            is_one_off=True,
            delivery_status="pending",
        )

        result = run_graphql(DELIVERABLE_QUERY, {}, make_context(user))

        assert result.errors is None
        row = result.data["deliverableItems"][0]
        assert row["hoursBooked"] == 0
        assert row["orderValue"] == 1000.0
        assert row["psRatio"] is None


class TestPsHourlyRate:
    def test_default_rate_is_160(self, user):
        result = run_graphql("query { psHourlyRate }", {}, make_context(user))
        assert result.errors is None
        assert result.data["psHourlyRate"] == 160.0

    def test_save_and_read_rate(self, user, tenant):
        mutation = """
            mutation($rate: Float!) {
                savePsHourlyRate(rate: $rate) { success error }
            }
        """
        result = run_graphql(mutation, {"rate": 200.0}, make_context(user))
        assert result.errors is None
        assert result.data["savePsHourlyRate"]["success"] is True

        tenant.refresh_from_db()
        assert tenant.settings["ps_hourly_rate"] == 200.0

        read = run_graphql("query { psHourlyRate }", {}, make_context(user))
        assert read.data["psHourlyRate"] == 200.0

    def test_negative_rate_rejected(self, user):
        mutation = """
            mutation($rate: Float!) {
                savePsHourlyRate(rate: $rate) { success error }
            }
        """
        result = run_graphql(mutation, {"rate": -5.0}, make_context(user))
        assert result.errors is None
        assert result.data["savePsHourlyRate"]["success"] is False

class TestMapTimeTrackingProjectConflict:
    def test_already_mapped_returns_conflict_details(self, user, tenant, contract, customer):
        """Conflict response carries existing-contract details for the UI."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Existing item",
            quantity=1,
            unit_price=Decimal("500.00"),
            is_one_off=True,
        )
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=contract,
            contract_item=item,
            external_project_id="ext-conflict",
            external_project_name="Conflict Project",
        )
        # A second contract to try mapping the same external project to.
        other_contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Other Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 2, 1),
            billing_start_date=date(2025, 2, 1),
        )

        mutation = """
            mutation($cid: ID!, $ext: String!) {
                mapTimeTrackingProject(
                    contractId: $cid,
                    externalProjectId: $ext,
                    externalProjectName: "X",
                    externalCustomerName: ""
                ) {
                    success
                    error
                    conflictContractId
                    conflictContractName
                    conflictItemName
                }
            }
        """
        result = run_graphql(
            mutation,
            {"cid": str(other_contract.id), "ext": "ext-conflict"},
            make_context(user),
        )
        assert result.errors is None
        data = result.data["mapTimeTrackingProject"]
        assert data["success"] is False
        assert "Project Contract" in data["error"]
        assert data["conflictContractId"] == contract.id
        assert data["conflictContractName"] == "Project Contract"
        assert data["conflictItemName"] == "Existing item"


class TestPsHourlyRateRatio:
    def test_rate_affects_ps_ratio(self, user, tenant, contract):
        """Changing the PS rate changes the computed PS ratio."""
        tenant.settings = {"ps_hourly_rate": 100.0}
        tenant.save(update_fields=["settings"])

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            description="Dev",
            quantity=1,
            unit_price=Decimal("4000.00"),
            is_one_off=True,
            delivery_status="pending",
        )
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=contract,
            contract_item=item,
            external_project_id="ext-2",
            external_project_name="Ext",
            cached_total_hours=10.0,
        )

        result = run_graphql(DELIVERABLE_QUERY, {}, make_context(user))
        assert result.errors is None
        # 4000 / (10 * 100) = 4.0
        assert result.data["deliverableItems"][0]["psRatio"] == pytest.approx(4.0)
