"""GraphQL schema for todos."""

from datetime import date, datetime
from typing import List

import strawberry
from strawberry import UNSET
from strawberry.types import Info
from django.db.models import Q, F

from apps.core.permissions import get_current_user
from apps.core.schema import DeleteResult
from .models import TodoItem


@strawberry.type
class TodoItemType:
    """A todo item linked to an entity."""

    id: int
    text: str
    reminder_date: date | None
    is_public: bool
    is_completed: bool
    created_at: datetime

    # Entity info
    entity_type: str
    entity_name: str
    entity_id: int

    # Creator info
    created_by_id: int
    created_by_name: str

    # Assignee info
    assigned_to_id: int | None
    assigned_to_name: str | None

    # Entity IDs for linking
    contract_id: int | None
    contract_item_id: int | None
    customer_id: int | None


def todo_to_type(todo: TodoItem) -> TodoItemType:
    """Convert a TodoItem model to TodoItemType."""
    # Determine entity_id based on which entity is set
    entity_id = todo.contract_id or todo.contract_item_id or todo.customer_id

    # Get creator's display name (full name or email)
    created_by_name = todo.created_by.get_full_name() or todo.created_by.email

    # Get assignee's display name if assigned
    assigned_to_name = None
    if todo.assigned_to:
        assigned_to_name = todo.assigned_to.get_full_name() or todo.assigned_to.email

    return TodoItemType(
        id=todo.id,
        text=todo.text,
        reminder_date=todo.reminder_date,
        is_public=todo.is_public,
        is_completed=todo.is_completed,
        created_at=todo.created_at,
        entity_type=todo.entity_type or "",
        entity_name=todo.entity_name or "",
        entity_id=entity_id,
        created_by_id=todo.created_by_id,
        created_by_name=created_by_name,
        assigned_to_id=todo.assigned_to_id,
        assigned_to_name=assigned_to_name,
        contract_id=todo.contract_id,
        contract_item_id=todo.contract_item_id,
        customer_id=todo.customer_id,
    )


@strawberry.type
class TodoQuery:
    @strawberry.field
    def my_todos(self, info: Info, limit: int = 20) -> List[TodoItemType]:
        """Get todos created by or assigned to the current user."""
        user = get_current_user(info)
        if not user:
            return []

        todos = (
            TodoItem.objects.filter(
                tenant=user.tenant,
            )
            .filter(
                Q(created_by=user) | Q(assigned_to=user)
            )
            .select_related("created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer")
            .order_by(
                # Null reminder dates last
                F("reminder_date").asc(nulls_last=True),
                "-created_at",
            )[:limit]
        )

        return [todo_to_type(todo) for todo in todos]

    @strawberry.field
    def team_todos(self, info: Info, limit: int = 20) -> List[TodoItemType]:
        """Get public todos from other tenant users (not created by or assigned to current user)."""
        user = get_current_user(info)
        if not user:
            return []

        todos = (
            TodoItem.objects.filter(
                tenant=user.tenant,
                is_public=True,
            )
            .exclude(created_by=user)
            .exclude(assigned_to=user)
            .select_related("created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer")
            .order_by(
                F("reminder_date").asc(nulls_last=True),
                "-created_at",
            )[:limit]
        )

        return [todo_to_type(todo) for todo in todos]


@strawberry.type
class TodoCreateResult:
    success: bool
    todo: TodoItemType | None = None
    error: str | None = None


@strawberry.type
class TodoUpdateResult:
    success: bool
    todo: TodoItemType | None = None
    error: str | None = None


@strawberry.type
class TodoMutation:
    @strawberry.mutation
    def create_todo(
        self,
        info: Info,
        text: str,
        is_public: bool = False,
        reminder_date: date | None = None,
        assigned_to_id: int | None = None,
        contract_id: int | None = None,
        contract_item_id: int | None = None,
        customer_id: int | None = None,
    ) -> TodoCreateResult:
        """Create a new todo item."""
        user = get_current_user(info)
        if not user:
            return TodoCreateResult(success=False, error="Not authenticated")

        # Validate exactly one entity is provided
        entity_count = sum([
            contract_id is not None,
            contract_item_id is not None,
            customer_id is not None,
        ])
        if entity_count != 1:
            return TodoCreateResult(
                success=False,
                error="Exactly one of contract_id, contract_item_id, or customer_id must be provided",
            )

        # Default assigned_to to self if not specified
        if assigned_to_id is None:
            assigned_to_id = user.id
        else:
            # Validate assigned_to is in the same tenant
            from apps.tenants.models import User
            if not User.objects.filter(id=assigned_to_id, tenant=user.tenant, is_active=True).exists():
                return TodoCreateResult(success=False, error="Invalid assignee")

        try:
            todo = TodoItem(
                tenant=user.tenant,
                text=text,
                reminder_date=reminder_date,
                is_public=is_public,
                is_completed=False,
                created_by=user,
                assigned_to_id=assigned_to_id,
                contract_id=contract_id,
                contract_item_id=contract_item_id,
                customer_id=customer_id,
            )
            todo.save()

            # Reload with related objects
            todo = TodoItem.objects.select_related(
                "created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer"
            ).get(pk=todo.pk)

            return TodoCreateResult(success=True, todo=todo_to_type(todo))
        except Exception as e:
            return TodoCreateResult(success=False, error=str(e))

    @strawberry.mutation
    def update_todo(
        self,
        info: Info,
        todo_id: int,
        text: str | None = None,
        reminder_date: date | None = strawberry.UNSET,
        is_public: bool | None = None,
        is_completed: bool | None = None,
        assigned_to_id: int | None = strawberry.UNSET,
    ) -> TodoUpdateResult:
        """Update a todo item."""
        user = get_current_user(info)
        if not user:
            return TodoUpdateResult(success=False, error="Not authenticated")

        try:
            todo = TodoItem.objects.select_related(
                "created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer"
            ).get(pk=todo_id, tenant=user.tenant)

            # Only creator can edit text, reminder_date, is_public, assigned_to
            # For public todos or assigned todos, assignee can toggle is_completed
            is_creator = todo.created_by_id == user.id
            is_assignee = todo.assigned_to_id == user.id

            if not is_creator and not is_assignee:
                # Non-creators/non-assignees can only toggle completion on public todos
                if not todo.is_public:
                    return TodoUpdateResult(success=False, error="Permission denied")
                if text is not None or reminder_date is not strawberry.UNSET or is_public is not None or assigned_to_id is not strawberry.UNSET:
                    return TodoUpdateResult(success=False, error="Only the creator can edit this todo")

            if not is_creator:
                # Assignees can only toggle completion
                if text is not None or reminder_date is not strawberry.UNSET or is_public is not None or assigned_to_id is not strawberry.UNSET:
                    return TodoUpdateResult(success=False, error="Only the creator can edit this todo")

            update_fields = ["updated_at"]

            if text is not None and is_creator:
                todo.text = text
                update_fields.append("text")

            if reminder_date is not strawberry.UNSET and is_creator:
                todo.reminder_date = reminder_date
                update_fields.append("reminder_date")

            if is_public is not None and is_creator:
                todo.is_public = is_public
                update_fields.append("is_public")

            if assigned_to_id is not strawberry.UNSET and is_creator:
                # Validate assigned_to is in the same tenant
                if assigned_to_id is not None:
                    from apps.tenants.models import User
                    if not User.objects.filter(id=assigned_to_id, tenant=user.tenant, is_active=True).exists():
                        return TodoUpdateResult(success=False, error="Invalid assignee")
                todo.assigned_to_id = assigned_to_id
                update_fields.append("assigned_to_id")

            if is_completed is not None:
                todo.is_completed = is_completed
                update_fields.append("is_completed")

            if len(update_fields) > 1:
                todo.save(update_fields=update_fields)

            # Reload to get updated assigned_to relation
            todo = TodoItem.objects.select_related(
                "created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer"
            ).get(pk=todo.pk)

            return TodoUpdateResult(success=True, todo=todo_to_type(todo))
        except TodoItem.DoesNotExist:
            return TodoUpdateResult(success=False, error="Todo not found")
        except Exception as e:
            return TodoUpdateResult(success=False, error=str(e))

    @strawberry.mutation
    def delete_todo(self, info: Info, todo_id: int) -> DeleteResult:
        """Delete a todo item. Only the creator can delete."""
        user = get_current_user(info)
        if not user:
            return DeleteResult(success=False, error="Not authenticated")

        try:
            todo = TodoItem.objects.get(pk=todo_id, tenant=user.tenant)

            # Only creator can delete
            if todo.created_by_id != user.id:
                return DeleteResult(success=False, error="Only the creator can delete this todo")

            todo.delete()
            return DeleteResult(success=True)
        except TodoItem.DoesNotExist:
            return DeleteResult(success=False, error="Todo not found")
        except Exception as e:
            return DeleteResult(success=False, error=str(e))
