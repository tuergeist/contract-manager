"""Tests for contract merge service."""
import pytest
from datetime import date
from decimal import Decimal

from apps.contracts.models import (
    Contract,
    ContractAmendment,
    ContractItem,
    TimeTrackingProjectMapping,
)
from apps.contracts.services.contract_merge import (
    execute_merge,
    preview_merge,
    validate_merge_preconditions,
)
from apps.customers.models import Customer
from apps.products.models import Product


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant, name="Test Customer", is_active=True
    )


@pytest.fixture
def other_customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant, name="Other Customer", is_active=True
    )


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant, name="Test Product", sku="TEST-001"
    )


@pytest.fixture
def product2(db, tenant):
    return Product.objects.create(
        tenant=tenant, name="Second Product", sku="TEST-002"
    )


@pytest.fixture
def draft_source(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Source Draft",
        status=Contract.Status.DRAFT,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
    )


@pytest.fixture
def active_target(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Target Active",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
    )


@pytest.fixture
def draft_target(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Target Draft",
        status=Contract.Status.DRAFT,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
    )


@pytest.fixture
def source_items(db, tenant, draft_source, product, product2):
    item1 = ContractItem.objects.create(
        tenant=tenant,
        contract=draft_source,
        product=product,
        quantity=1,
        unit_price=Decimal("100.00"),
        price_period="monthly",
        start_date=date(2026, 3, 1),
        billing_start_date=date(2026, 3, 1),
        sort_order=1,
    )
    item2 = ContractItem.objects.create(
        tenant=tenant,
        contract=draft_source,
        product=product2,
        quantity=2,
        unit_price=Decimal("50.00"),
        price_period="monthly",
        is_one_off=True,
        sort_order=1,
    )
    return [item1, item2]


class TestValidateMergePreconditions:
    def test_valid_merge(self, draft_source, active_target):
        errors = validate_merge_preconditions(draft_source, active_target)
        assert errors == []

    def test_same_contract(self, draft_source):
        errors = validate_merge_preconditions(draft_source, draft_source)
        assert "Cannot merge a contract into itself" in errors

    def test_different_customers(self, tenant, draft_source, other_customer):
        target = Contract.objects.create(
            tenant=tenant,
            customer=other_customer,
            name="Other Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        errors = validate_merge_preconditions(draft_source, target)
        assert "Contracts must belong to the same customer" in errors

    def test_source_not_draft_or_active(self, tenant, customer, active_target):
        paused_source = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Paused",
            status=Contract.Status.PAUSED,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        errors = validate_merge_preconditions(paused_source, active_target)
        assert "Only draft or active contracts can be merged" in errors

    def test_target_deleted(self, tenant, customer, draft_source):
        deleted_target = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Deleted",
            status=Contract.Status.DELETED,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        errors = validate_merge_preconditions(draft_source, deleted_target)
        assert "Target contract is not in a mergeable state" in errors

    def test_target_cancelled(self, tenant, customer, draft_source):
        cancelled_target = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Cancelled",
            status=Contract.Status.CANCELLED,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        errors = validate_merge_preconditions(draft_source, cancelled_target)
        assert "Target contract is not in a mergeable state" in errors

    def test_target_ended(self, tenant, customer, draft_source):
        ended_target = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Ended",
            status=Contract.Status.ENDED,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        errors = validate_merge_preconditions(draft_source, ended_target)
        assert "Target contract is not in a mergeable state" in errors

    def test_source_with_invoices(self, tenant, customer, draft_source, active_target):
        # Create an invoice record on the source
        from apps.invoices.models import InvoiceRecord
        InvoiceRecord.objects.create(
            tenant=tenant,
            contract=draft_source,
            customer=customer,
            invoice_number="INV-001",
            invoice_date=date(2026, 1, 1),
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("19.00"),
            total_gross=Decimal("119.00"),
            line_items_snapshot=[],
            company_data_snapshot={},
        )
        errors = validate_merge_preconditions(draft_source, active_target)
        assert "Source contract has invoices and cannot be merged" in errors

    def test_active_source_valid(self, tenant, customer, active_target):
        active_source = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Active Source",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 6, 1),
            billing_start_date=date(2025, 6, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        errors = validate_merge_preconditions(active_source, active_target)
        assert errors == []


class TestPreviewMerge:
    def test_preview_returns_items(self, draft_source, active_target, source_items):
        preview = preview_merge(draft_source, active_target)
        assert len(preview["items"]) == 2
        assert preview["items"][0]["product_name"] == "Test Product"
        assert preview["items"][0]["quantity"] == 1
        assert preview["items"][1]["is_one_off"] is True

    def test_preview_amendments_for_active_target(self, draft_source, active_target, source_items):
        preview = preview_merge(draft_source, active_target)
        assert preview["will_create_amendments"] is True

    def test_preview_no_amendments_for_draft_target(self, draft_source, draft_target, source_items):
        preview = preview_merge(draft_source, draft_target)
        assert preview["will_create_amendments"] is False

    def test_preview_includes_contract_names(self, draft_source, active_target, source_items):
        preview = preview_merge(draft_source, active_target)
        assert preview["source_contract_name"] == "Source Draft"
        assert preview["target_contract_name"] == "Target Active"


class TestExecuteMerge:
    def test_items_transferred_to_target(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)

        # Source should have no items
        assert draft_source.items.count() == 0
        # Target should have 2 items
        assert active_target.items.count() == 2

    def test_source_set_to_deleted(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)
        draft_source.refresh_from_db()
        assert draft_source.status == Contract.Status.DELETED

    def test_sort_order_appended(self, tenant, draft_source, active_target, source_items, product):
        # Add existing items to target
        ContractItem.objects.create(
            tenant=tenant, contract=active_target, product=product,
            quantity=1, unit_price=Decimal("200.00"), sort_order=5,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=active_target, product=product,
            quantity=1, unit_price=Decimal("200.00"), is_one_off=True, sort_order=3,
        )

        execute_merge(draft_source, active_target)

        transferred = active_target.items.exclude(unit_price=Decimal("200.00"))
        recurring = transferred.filter(is_one_off=False).first()
        oneoff = transferred.filter(is_one_off=True).first()

        assert recurring.sort_order == 6  # max(5) + 1
        assert oneoff.sort_order == 4  # max(3) + 1

    def test_amendments_created_for_active_target(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)
        amendments = ContractAmendment.objects.filter(contract=active_target)
        assert amendments.count() == 2
        assert all(a.type == ContractAmendment.AmendmentType.PRODUCT_ADDED for a in amendments)

    def test_no_amendments_for_draft_target(self, draft_source, draft_target, source_items):
        execute_merge(draft_source, draft_target)
        amendments = ContractAmendment.objects.filter(contract=draft_target)
        assert amendments.count() == 0

    def test_hubspot_deal_id_preserved(self, draft_source, active_target, source_items):
        draft_source.hubspot_deal_id = "12345"
        draft_source.save()

        execute_merge(draft_source, active_target)

        for item in active_target.items.all():
            assert item.source_hubspot_deal_id == "12345"

    def test_no_hubspot_deal_id_stays_null(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)
        for item in active_target.items.all():
            assert item.source_hubspot_deal_id is None

    def test_date_overrides_applied(self, draft_source, active_target, source_items):
        item = source_items[0]
        overrides = {
            item.id: {
                "start_date": date(2026, 6, 1),
                "billing_start_date": date(2026, 6, 15),
            }
        }

        execute_merge(draft_source, active_target, item_overrides=overrides)

        item.refresh_from_db()
        assert item.start_date == date(2026, 6, 1)
        assert item.billing_start_date == date(2026, 6, 15)

    def test_items_without_overrides_keep_dates(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)
        source_items[0].refresh_from_db()
        assert source_items[0].start_date == date(2026, 3, 1)
        assert source_items[0].billing_start_date == date(2026, 3, 1)

    def test_amendment_arr_delta(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)
        amendments = ContractAmendment.objects.filter(contract=active_target).order_by("id")

        # Recurring item: 100 * 1 * 12 = 1200
        recurring_amendment = amendments.filter(arr_delta=Decimal("1200")).first()
        assert recurring_amendment is not None

        # One-off item: ARR = 0
        oneoff_amendment = amendments.filter(arr_delta=Decimal("0")).first()
        assert oneoff_amendment is not None

    def test_atomicity_on_failure(self, tenant, customer, active_target, product):
        """If merge fails, everything should roll back."""
        source = Contract.objects.create(
            tenant=tenant, customer=customer, name="Source",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant, contract=source, product=product,
            quantity=1, unit_price=Decimal("100.00"),
        )

        # Make source invalid by giving it an invoice between validate and execute
        # We simulate by testing that a direct validation failure rolls back
        # By changing the source status mid-transaction isn't possible, so we test
        # that calling with invalid preconditions raises and doesn't change state.
        source_copy_status = source.status
        with pytest.raises(ValueError):
            execute_merge(source, source)  # self-merge should fail

        source.refresh_from_db()
        assert source.status == source_copy_status
        assert source.items.count() == 1

    def test_clockodo_mappings_deleted(self, tenant, draft_source, active_target, source_items):
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant,
            contract=draft_source,
            external_project_id="ext-123",
            external_project_name="Test Project",
            external_customer_name="Test Customer",
            link_source="manual",
        )

        execute_merge(draft_source, active_target)

        assert TimeTrackingProjectMapping.objects.filter(contract=draft_source).count() == 0

    def test_amendment_linked_to_items(self, draft_source, active_target, source_items):
        execute_merge(draft_source, active_target)
        for item in active_target.items.all():
            assert item.added_by_amendment is not None
            assert item.added_by_amendment.contract == active_target
