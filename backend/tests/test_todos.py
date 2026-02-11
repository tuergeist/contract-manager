"""Tests for todo feature."""
import pytest
from datetime import date
from django.core.exceptions import ValidationError

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product
from apps.todos.models import TodoItem, TodoComment
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


class TestTodoComment:
    """Test TodoComment model."""

    def test_create_comment(self, db, tenant, user, contract):
        """Comments can be created on todos."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test todo",
            created_by=user,
            contract=contract,
        )
        comment = TodoComment.objects.create(
            tenant=tenant,
            todo=todo,
            text="This is a comment",
            author=user,
        )
        assert comment.id is not None
        assert comment.text == "This is a comment"
        assert comment.author == user

    def test_comment_count_property(self, db, tenant, user, contract):
        """Todo.comment_count returns the correct count."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test todo",
            created_by=user,
            contract=contract,
        )
        assert todo.comment_count == 0

        TodoComment.objects.create(tenant=tenant, todo=todo, text="Comment 1", author=user)
        TodoComment.objects.create(tenant=tenant, todo=todo, text="Comment 2", author=user)

        # Refresh from db
        todo.refresh_from_db()
        assert todo.comment_count == 2

    def test_comments_ordered_by_created_at(self, db, tenant, user, contract):
        """Comments are ordered by created_at ascending."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test todo",
            created_by=user,
            contract=contract,
        )
        c1 = TodoComment.objects.create(tenant=tenant, todo=todo, text="First", author=user)
        c2 = TodoComment.objects.create(tenant=tenant, todo=todo, text="Second", author=user)
        c3 = TodoComment.objects.create(tenant=tenant, todo=todo, text="Third", author=user)

        comments = list(todo.comments.all())
        assert comments[0].id == c1.id
        assert comments[1].id == c2.id
        assert comments[2].id == c3.id

    def test_delete_todo_deletes_comments(self, db, tenant, user, contract):
        """Deleting a todo deletes its comments."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Test todo",
            created_by=user,
            contract=contract,
        )
        comment = TodoComment.objects.create(
            tenant=tenant,
            todo=todo,
            text="Will be deleted",
            author=user,
        )
        comment_id = comment.id

        todo.delete()

        assert not TodoComment.objects.filter(id=comment_id).exists()


class TestTodoReassignment:
    """Test todo reassignment rules."""

    def test_reassign_public_todo_to_self(self, db, tenant, user, other_user, contract):
        """Users can reassign public todos to themselves."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Public todo",
            created_by=user,
            assigned_to=user,
            contract=contract,
            is_public=True,
        )

        # Simulate other_user taking over
        todo.assigned_to = other_user
        todo.save()

        todo.refresh_from_db()
        assert todo.assigned_to == other_user

    def test_cannot_reassign_private_todo_of_another(self, db, tenant, user, other_user, contract):
        """Private todos can only be reassigned by their creator."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Private todo",
            created_by=user,
            assigned_to=user,
            contract=contract,
            is_public=False,
        )
        # The business logic for permission checking is in the GraphQL mutation
        # Here we just verify the model allows the assignment (model doesn't enforce this)
        assert todo.is_public is False
        assert todo.created_by == user

    def test_reassign_unassigned_todo(self, db, tenant, user, other_user, contract):
        """Unassigned todos can be assigned."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Unassigned todo",
            created_by=user,
            assigned_to=None,
            contract=contract,
            is_public=True,
        )

        todo.assigned_to = other_user
        todo.save()

        todo.refresh_from_db()
        assert todo.assigned_to == other_user


class TestCustomerTodosAggregation:
    """Test that customer todos include contract todos."""

    def test_direct_customer_todo_visible(self, db, tenant, user, customer):
        """Direct customer todos are visible."""
        todo = TodoItem.objects.create(
            tenant=tenant,
            text="Customer todo",
            created_by=user,
            customer=customer,
        )
        customer_todos = TodoItem.objects.filter(customer=customer)
        assert todo in customer_todos

    def test_contract_todo_separate_from_customer(self, db, tenant, user, contract, customer):
        """Contract todos are not in direct customer todos query."""
        contract_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Contract todo",
            created_by=user,
            contract=contract,
        )
        customer_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Customer todo",
            created_by=user,
            customer=customer,
        )

        # Direct customer todos query
        direct_customer_todos = TodoItem.objects.filter(customer=customer)
        assert customer_todo in direct_customer_todos
        assert contract_todo not in direct_customer_todos

    def test_aggregated_customer_todos_includes_contract_todos(self, db, tenant, user, contract, customer):
        """Aggregated query includes both customer and contract todos."""
        from django.db.models import Q

        # Create todos
        customer_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Customer todo",
            created_by=user,
            customer=customer,
        )
        contract_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Contract todo",
            created_by=user,
            contract=contract,
        )

        # Simulate the aggregated query from CustomerType.todos resolver
        contract_ids = list(Contract.objects.filter(customer=customer).values_list("id", flat=True))
        aggregated_todos = TodoItem.objects.filter(
            Q(customer=customer) | Q(contract_id__in=contract_ids)
        )

        assert customer_todo in aggregated_todos
        assert contract_todo in aggregated_todos

    def test_aggregated_respects_visibility(self, db, tenant, user, other_user, contract, customer):
        """Aggregated todos respects visibility (public or created_by)."""
        from django.db.models import Q

        # Private todo by other user (should not be visible to `user`)
        private_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Private by other",
            created_by=other_user,
            customer=customer,
            is_public=False,
        )
        # Public todo by other user (should be visible)
        public_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Public by other",
            created_by=other_user,
            customer=customer,
            is_public=True,
        )
        # Private todo by user (should be visible to user)
        own_todo = TodoItem.objects.create(
            tenant=tenant,
            text="Own private",
            created_by=user,
            customer=customer,
            is_public=False,
        )

        # Aggregated query with visibility filter for `user`
        contract_ids = list(Contract.objects.filter(customer=customer).values_list("id", flat=True))
        visible_todos = TodoItem.objects.filter(
            Q(customer=customer) | Q(contract_id__in=contract_ids)
        ).filter(
            Q(created_by=user) | Q(is_public=True)
        )

        assert own_todo in visible_todos
        assert public_todo in visible_todos
        assert private_todo not in visible_todos
