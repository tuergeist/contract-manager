"""Tests for HubSpot sync, specifically company merge handling and billing contacts."""
import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import httpx

from apps.customers.models import Customer, CustomerNote, CustomerLink
from apps.contracts.models import Contract, ContractGroup
from apps.invoices.models import InvoiceRecord, ImportedInvoice
from apps.banking.models import Counterparty
from apps.todos.models import TodoItem
from apps.tenants.models import User
from apps.customers.hubspot import HubSpotService


@pytest.fixture
def tenant_with_hubspot(tenant):
    """Tenant with HubSpot config."""
    tenant.hubspot_config = {"api_key": "test-key"}
    tenant.save()
    return tenant


@pytest.fixture
def hubspot_service(tenant_with_hubspot):
    return HubSpotService(tenant_with_hubspot)


@pytest.fixture
def old_customer(db, tenant_with_hubspot):
    """The customer that existed before the merge (old HubSpot ID)."""
    return Customer.objects.create(
        tenant=tenant_with_hubspot,
        hubspot_id="326297284815",
        name="KSB Industries B.V.",
        is_active=True,
    )


@pytest.fixture
def user(db, tenant_with_hubspot):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant_with_hubspot,
    )


class TestMergeCustomer:
    """Test _merge_customer reassigns all dependent objects."""

    def test_contracts_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot):
        """Contracts are moved from old customer to new customer."""
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        contract = Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="Test Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        contract.refresh_from_db()
        assert contract.customer == new_customer

    def test_contract_groups_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot):
        """Contract groups are moved to new customer."""
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        group = ContractGroup.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="Group A",
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        group.refresh_from_db()
        assert group.customer == new_customer

    def test_contract_groups_consolidated_on_name_collision(
        self, hubspot_service, old_customer, tenant_with_hubspot
    ):
        """When both customers have a group with the same name, contracts are consolidated."""
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        src_group = ContractGroup.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="Shared Group",
        )
        tgt_group = ContractGroup.objects.create(
            tenant=tenant_with_hubspot,
            customer=new_customer,
            name="Shared Group",
        )
        contract = Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="Contract in old group",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
            group=src_group,
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        contract.refresh_from_db()
        assert contract.group == tgt_group
        assert contract.customer == new_customer
        assert not ContractGroup.objects.filter(pk=src_group.pk).exists()

    def test_notes_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot, user):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        note = CustomerNote.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            user=user,
            content="Important note",
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        note.refresh_from_db()
        assert note.customer == new_customer

    def test_links_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot, user):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        link = CustomerLink.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="Website",
            url="https://example.com",
            created_by=user,
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        link.refresh_from_db()
        assert link.customer == new_customer

    def test_todos_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot, user):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        todo = TodoItem.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            created_by=user,
            text="Follow up",
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        todo.refresh_from_db()
        assert todo.customer == new_customer

    def test_invoice_records_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        invoice = InvoiceRecord.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            invoice_number="INV-001",
            billing_date=date(2025, 6, 1),
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            total_net=100,
            tax_rate=19,
            tax_amount=19,
            total_gross=119,
            line_items_snapshot=[],
            company_data_snapshot={},
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        invoice.refresh_from_db()
        assert invoice.customer == new_customer

    def test_imported_invoices_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        imported = ImportedInvoice.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            pdf_file="invoices/test.pdf",
            original_filename="test.pdf",
            file_size=1024,
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        imported.refresh_from_db()
        assert imported.customer == new_customer

    def test_counterparties_reassigned(self, hubspot_service, old_customer, tenant_with_hubspot):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )
        cp = Counterparty.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="KSB Payment",
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        cp.refresh_from_db()
        assert cp.customer == new_customer

    def test_source_customer_deactivated(self, hubspot_service, old_customer, tenant_with_hubspot):
        new_customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="381968328892",
            name="KSB Industries B.V.",
            is_active=True,
        )

        hubspot_service._merge_customer(old_customer, new_customer)

        old_customer.refresh_from_db()
        assert old_customer.is_active is False
        assert old_customer.hubspot_deleted_at is not None


class TestSyncCompanyMergeDetection:
    """Test that _sync_company detects merges from hs_merged_object_ids."""

    def test_merge_triggered_on_sync(self, hubspot_service, old_customer, tenant_with_hubspot):
        """Syncing the canonical company triggers merge of old customer."""
        contract = Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=old_customer,
            name="Old Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        # Simulate HubSpot returning the canonical company with merged IDs
        company_data = {
            "id": "381968328892",
            "properties": {
                "name": "KSB Industries B.V.",
                "address": "",
                "city": "",
                "zip": "",
                "country_list": "",
                "hs_merged_object_ids": "326071100639;326297284815",
            },
        }

        result = hubspot_service._sync_company(company_data, is_active=True)
        assert result == "created"

        # Old customer should be deactivated
        old_customer.refresh_from_db()
        assert old_customer.is_active is False
        assert old_customer.hubspot_deleted_at is not None

        # Contract should be on the new customer
        contract.refresh_from_db()
        new_customer = Customer.objects.get(
            tenant=tenant_with_hubspot, hubspot_id="381968328892"
        )
        assert contract.customer == new_customer

    def test_no_merge_when_no_merged_ids(self, hubspot_service, old_customer, tenant_with_hubspot):
        """No merge happens when hs_merged_object_ids is empty."""
        company_data = {
            "id": "999999",
            "properties": {
                "name": "Other Company",
                "hs_merged_object_ids": "",
            },
        }

        hubspot_service._sync_company(company_data, is_active=True)

        old_customer.refresh_from_db()
        assert old_customer.is_active is True
        assert old_customer.hubspot_deleted_at is None

    def test_canonical_id_excluded_from_merge_ids(self, hubspot_service, tenant_with_hubspot):
        """The canonical ID itself is not treated as an old ID to merge."""
        company_data = {
            "id": "12345",
            "properties": {
                "name": "Self-referencing",
                # The canonical ID appears in its own merged list
                "hs_merged_object_ids": "12345;67890",
            },
        }

        # Create the "old" customer for 67890
        old = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="67890",
            name="Old Record",
            is_active=True,
        )

        hubspot_service._sync_company(company_data, is_active=True)

        old.refresh_from_db()
        assert old.is_active is False

    def test_merge_with_multiple_old_ids(self, hubspot_service, tenant_with_hubspot):
        """Multiple old customers can be merged into one canonical."""
        old1 = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="111",
            name="Old 1",
            is_active=True,
        )
        old2 = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="222",
            name="Old 2",
            is_active=True,
        )
        c1 = Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=old1,
            name="Contract 1",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        c2 = Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=old2,
            name="Contract 2",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        company_data = {
            "id": "333",
            "properties": {
                "name": "Canonical",
                "hs_merged_object_ids": "111;222",
            },
        }

        hubspot_service._sync_company(company_data, is_active=True)

        canonical = Customer.objects.get(tenant=tenant_with_hubspot, hubspot_id="333")
        c1.refresh_from_db()
        c2.refresh_from_db()
        assert c1.customer == canonical
        assert c2.customer == canonical

        old1.refresh_from_db()
        old2.refresh_from_db()
        assert old1.is_active is False
        assert old2.is_active is False

    def test_no_crash_when_old_customer_not_found(self, hubspot_service, tenant_with_hubspot):
        """No error when merged IDs reference customers we don't have."""
        company_data = {
            "id": "555",
            "properties": {
                "name": "New Company",
                "hs_merged_object_ids": "999;888",
            },
        }

        result = hubspot_service._sync_company(company_data, is_active=True)
        assert result == "created"


def _mock_response(status_code, json_data):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


class TestBillingContactSync:
    """Test syncing billing contact emails from HubSpot associations."""

    def test_emails_synced_for_customer_with_active_contract(
        self, hubspot_service, tenant_with_hubspot
    ):
        """Billing emails are fetched and stored for customers with active contracts."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="100",
            name="Test Corp",
            is_active=True,
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Active Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(200, {
                "results": [
                    {
                        "toObjectId": 999,
                        "associationTypes": [
                            {"typeId": 2, "label": "Contact with Primary Company"},
                        ],
                    },
                    {
                        "toObjectId": 888,
                        "associationTypes": [
                            {"typeId": 930, "label": "Billing Contact"},
                        ],
                    },
                ]
            }),
            # contact fetch for 888
            _mock_response(200, {
                "properties": {"email": "billing@testcorp.com"},
            }),
        ]

        errors = []
        hubspot_service._sync_all_billing_contacts(mock_client, "Billing Contact", errors)

        customer.refresh_from_db()
        assert customer.billing_emails == ["billing@testcorp.com"]
        assert errors == []

    def test_multiple_billing_contacts(self, hubspot_service, tenant_with_hubspot):
        """Multiple billing contacts produce multiple emails."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="200",
            name="Multi Corp",
            is_active=True,
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Active",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(200, {
                "results": [
                    {
                        "toObjectId": 111,
                        "associationTypes": [{"typeId": 930, "label": "Billing Contact"}],
                    },
                    {
                        "toObjectId": 222,
                        "associationTypes": [{"typeId": 930, "label": "Billing Contact"}],
                    },
                ]
            }),
            _mock_response(200, {"properties": {"email": "B@corp.com"}}),
            _mock_response(200, {"properties": {"email": "A@corp.com"}}),
        ]

        hubspot_service._sync_all_billing_contacts(mock_client, "Billing Contact", [])

        customer.refresh_from_db()
        assert customer.billing_emails == ["a@corp.com", "b@corp.com"]

    def test_no_billing_contacts_clears_emails(self, hubspot_service, tenant_with_hubspot):
        """When no billing contacts exist, billing_emails is cleared."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="300",
            name="No Billing Corp",
            is_active=True,
            billing_emails=["old@corp.com"],
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Active",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(200, {"results": []})

        hubspot_service._sync_all_billing_contacts(mock_client, "Billing Contact", [])

        customer.refresh_from_db()
        assert customer.billing_emails == []

    def test_skips_customers_without_active_contracts(
        self, hubspot_service, tenant_with_hubspot
    ):
        """Customers with only draft contracts are not synced."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="400",
            name="Draft Only Corp",
            is_active=True,
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Draft",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)

        hubspot_service._sync_all_billing_contacts(mock_client, "Billing Contact", [])

        # Client should never be called — no eligible customers
        mock_client.get.assert_not_called()
        customer.refresh_from_db()
        assert customer.billing_emails == []

    def test_paused_contract_still_triggers_sync(self, hubspot_service, tenant_with_hubspot):
        """Customers with paused contracts still get billing contacts synced."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="500",
            name="Paused Corp",
            is_active=True,
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Paused",
            status=Contract.Status.PAUSED,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(200, {
                "results": [
                    {
                        "toObjectId": 777,
                        "associationTypes": [{"typeId": 930, "label": "Billing Contact"}],
                    },
                ]
            }),
            _mock_response(200, {"properties": {"email": "paused@corp.com"}}),
        ]

        hubspot_service._sync_all_billing_contacts(mock_client, "Billing Contact", [])

        customer.refresh_from_db()
        assert customer.billing_emails == ["paused@corp.com"]

    def test_contact_fetch_error_does_not_crash(self, hubspot_service, tenant_with_hubspot):
        """A failed contact fetch logs a warning but doesn't stop the sync."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="600",
            name="Error Corp",
            is_active=True,
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Active",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(200, {
                "results": [
                    {
                        "toObjectId": 666,
                        "associationTypes": [{"typeId": 930, "label": "Billing Contact"}],
                    },
                ]
            }),
            _mock_response(403, {"error": "Missing scopes"}),
        ]

        errors = []
        hubspot_service._sync_all_billing_contacts(mock_client, "Billing Contact", errors)

        # No emails set, but no crash
        customer.refresh_from_db()
        assert customer.billing_emails == []

    def test_custom_label_name_used(self, hubspot_service, tenant_with_hubspot):
        """A custom label name (e.g. 'Purchasing Department') is matched correctly."""
        customer = Customer.objects.create(
            tenant=tenant_with_hubspot,
            hubspot_id="700",
            name="Custom Label Corp",
            is_active=True,
        )
        Contract.objects.create(
            tenant=tenant_with_hubspot,
            customer=customer,
            name="Active",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(200, {
                "results": [
                    {
                        "toObjectId": 111,
                        "associationTypes": [{"typeId": 930, "label": "Billing Contact"}],
                    },
                    {
                        "toObjectId": 222,
                        "associationTypes": [{"typeId": 4, "label": "Purchasing Department"}],
                    },
                ]
            }),
            # Only contact 222 should be fetched
            _mock_response(200, {"properties": {"email": "purchasing@corp.com"}}),
        ]

        hubspot_service._sync_all_billing_contacts(
            mock_client, "Purchasing Department", []
        )

        customer.refresh_from_db()
        assert customer.billing_emails == ["purchasing@corp.com"]
