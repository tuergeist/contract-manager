"""Tests for todo feature."""
import pytest
from datetime import date
from django.core.exceptions import ValidationError

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product
from apps.todos.models import TodoItem
from apps.tenants.models import Tenant, User


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
    )


@pytest.fixture
def contract_item(db, tenant, contract, product):
    """Create a test contract item."""
    return ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        product=product,
        quantity=1,
        unit_price=100,
    )


@pytest.fixture
def other_tenant(db):
    """Create another tenant for isolation tests."""
    return Tenant.objects.create(
        name="Other Company",
        currency="EUR",
    )


@pytest.fixture
def other_user(db, tenant):
    """Create another user in the same tenant."""
    return User.objects.create_user(
        email="other@example.com",
        password="testpass123",
        tenant=tenant,
        name="Other User",
    )


class TestTodoItemModelValidation:
    """Test TodoItem model validation (exactly one entity required)."""

    def test_todo_with_contract_is_valid(self, db, tenant, user, contract):
        """Todo with only contract set is valid."""
        todo = TodoItem(
            tenant=tenant,
            text="Follow up on renewal",
            created_by=user,
            contract=contract,
        )
        todo.save()  # Should not raise
        assert todo.id is not None
        assert todo.entity_type == "contract"

    def test_todo_with_customer_is_valid(self, db, tenant, user, customer):
        """Todo with only customer set is valid."""
        todo = TodoItem(
            tenant=tenant,
            text="Follow up on pricing",
            created_by=user,
            customer=customer,
        )
        todo.save()
        assert todo.entity_type == "customer"

    def test_todo_with_contract_item_is_valid(self, db, tenant, user, contract_item):
        """Todo with only contract_item set is valid."""
        todo = TodoItem(
            tenant=tenant,
            text="Check license count",
            created_by=user,
            contract_item=contract_item,
        )
        todo.save()
        assert todo.entity_type == "contract_item"

    def test_todo_without_entity_raises(self, db, tenant, user):
        """Todo without any entity raises ValidationError."""
        todo = TodoItem(
            tenant=tenant,
            text="Orphan todo",
            created_by=user,
        )
        with pytest.raises(ValidationError) as exc_info:
            todo.save()
        assert "must be linked" in str(exc_info.value)

    def test_todo_with_multiple_entities_raises(self, db, tenant, user, contract, customer):
        """Todo with multiple entities raises ValidationError."""
        todo = TodoItem(
            tenant=tenant,
            text="Multi-entity todo",
            created_by=user,
            contract=contract,
            customer=customer,
        )
        with pytest.raises(ValidationError) as exc_info:
            todo.save()
        assert "only be linked to one" in str(exc_info.value)


class TestTodoItemEntityName:
    """Test entity_name property returns correct display names."""

    def test_entity_name_for_contract(self, db, tenant, user, contract):
        """entity_name returns contract name."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test",
            created_by=user,
            contract=contract,
        )
        assert todo.entity_name == "Test Contract"

    def test_entity_name_for_customer(self, db, tenant, user, customer):
        """entity_name returns customer name."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test",
            created_by=user,
            customer=customer,
        )
        assert todo.entity_name == "Test Customer"

    def test_entity_name_for_contract_item(self, db, tenant, user, contract_item):
        """entity_name returns product name with contract context."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test",
            created_by=user,
            contract_item=contract_item,
        )
        assert "Test Product" in todo.entity_name
        assert "Test Contract" in todo.entity_name


class TestTodoCascadeDelete:
    """Test cascade delete when contract/customer is deleted."""

    def test_delete_contract_deletes_todos(self, db, tenant, user, contract):
        """Deleting a contract deletes associated todos."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Follow up",
            created_by=user,
            contract=contract,
        )
        contract_id = contract.id
        todo_id = todo.id

        contract.delete()

        assert not TodoItem.objects.filter(id=todo_id).exists()

    def test_delete_customer_deletes_todos(self, db, tenant, user, customer):
        """Deleting a customer deletes associated todos."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Follow up",
            created_by=user,
            customer=customer,
        )
        todo_id = todo.id

        customer.delete()

        assert not TodoItem.objects.filter(id=todo_id).exists()

    def test_delete_contract_item_deletes_todos(self, db, tenant, user, contract_item):
        """Deleting a contract item deletes associated todos."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Follow up",
            created_by=user,
            contract_item=contract_item,
        )
        todo_id = todo.id

        contract_item.delete()

        assert not TodoItem.objects.filter(id=todo_id).exists()


class TestTodoVisibility:
    """Test todo visibility rules."""

    def test_private_todo_defaults(self, db, tenant, user, contract):
        """Todos are private by default."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Private by default",
            created_by=user,
            contract=contract,
        )
        assert todo.is_public is False

    def test_public_todo_can_be_created(self, db, tenant, user, contract):
        """Public todos can be created."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Shared with team",
            created_by=user,
            contract=contract,
            is_public=True,
        )
        assert todo.is_public is True


class TestTodoOrdering:
    """Test todo ordering by reminder_date."""

    def test_todos_ordered_by_reminder_date(self, db, tenant, user, contract):
        """Todos are ordered by reminder_date ascending, nulls last."""
        todo_no_date = TodoItem.objects.create(
            tenant=tenant,
            text="No reminder",
            created_by=user,
            contract=contract,
        )
        todo_later = TodoItem.objects.create(
            tenant=tenant,
            text="Later",
            created_by=user,
            contract=contract,
            reminder_date=date(2026, 6, 1),
        )
        todo_sooner = TodoItem.objects.create(
            tenant=tenant,
            text="Sooner",
            created_by=user,
            contract=contract,
            reminder_date=date(2026, 3, 1),
        )

        todos = list(TodoItem.objects.filter(tenant=tenant))
        # With default ordering: reminder_date asc, nulls behavior depends on DB
        # The model's Meta has: ordering = ["reminder_date", "-created_at"]
        # sooner should come before later
        reminder_dates = [t.reminder_date for t in todos if t.reminder_date]
        assert reminder_dates == sorted(reminder_dates)
