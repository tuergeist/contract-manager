"""GraphQL schema for todos."""

from datetime import date, datetime
from typing import List

import strawberry
from strawberry import UNSET
from strawberry.types import Info
from django.db.models import Q, F

from apps.core.permissions import check_perm, get_current_user, require_perm
from apps.core.schema import DeleteResult
from .models import TodoItem, TodoComment


@strawberry.type
class TodoCommentType:
    """A comment on a todo item."""

    id: int
    text: str
    author_id: int
    author_name: str
    created_at: datetime


def comment_to_type(comment: TodoComment) -> TodoCommentType:
    """Convert a TodoComment model to TodoCommentType."""
    author_name = comment.author.get_full_name() or comment.author.email
    return TodoCommentType(
        id=comment.id,
        text=comment.text,
        author_id=comment.author_id,
        author_name=author_name,
        created_at=comment.created_at,
    )


@strawberry.type
class TodoItemType:
    """A todo item linked to an entity."""

    id: int
    text: str
    reminder_date: date | None
    is_public: bool
    is_completed: bool
    completed_at: datetime | None
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

    # Comments
    comment_count: int
    comments: List[TodoCommentType]


def todo_to_type(todo: TodoItem, include_comments: bool = True) -> TodoItemType:
    """Convert a TodoItem model to TodoItemType."""
    # Determine entity_id based on which entity is set
    entity_id = todo.contract_id or todo.contract_item_id or todo.customer_id

    # Get creator's display name (full name or email)
    created_by_name = todo.created_by.get_full_name() or todo.created_by.email

    # Get assignee's display name if assigned
    assigned_to_name = None
    if todo.assigned_to:
        assigned_to_name = todo.assigned_to.get_full_name() or todo.assigned_to.email

    # Get comments
    comments = []
    if include_comments:
        comments = [comment_to_type(c) for c in todo.comments.select_related("author").all()]

    return TodoItemType(
        id=todo.id,
        text=todo.text,
        reminder_date=todo.reminder_date,
        is_public=todo.is_public,
        is_completed=todo.is_completed,
        completed_at=todo.completed_at,
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
        comment_count=todo.comment_count,
        comments=comments,
    )


@strawberry.type
class TodoQuery:
    @strawberry.field
    def my_todos(
        self,
        info: Info,
        is_completed: bool | None = None,
        limit: int = 100,
    ) -> List[TodoItemType]:
        """Get todos where the current user is assignee OR creator.

        Includes todos from contracts, contract items, and customers.
        """
        user = require_perm(info, "todos", "read")
        if not user:
            return []

        queryset = TodoItem.objects.filter(
            tenant=user.tenant,
        ).filter(
            Q(assigned_to=user) | Q(created_by=user)
        )

        # Optional filter by completion status
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed)

        todos = queryset.select_related(
            "created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer"
        ).order_by(
            # Null reminder dates last
            F("reminder_date").asc(nulls_last=True),
            "-created_at",
        )[:limit]

        return [todo_to_type(todo) for todo in todos]

    @strawberry.field
    def team_todos(self, info: Info, limit: int = 20) -> List[TodoItemType]:
        """Get public todos not in the user's 'my todos' list."""
        user = require_perm(info, "todos", "read")
        if not user:
            return []

        todos = (
            TodoItem.objects.filter(
                tenant=user.tenant,
                is_public=True,
            )
            .exclude(
                Q(assigned_to=user) | Q(assigned_to__isnull=True, created_by=user)
            )
            .select_related("created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer")
            .order_by(
                F("reminder_date").asc(nulls_last=True),
                "-created_at",
            )[:limit]
        )

        return [todo_to_type(todo) for todo in todos]

    @strawberry.field
    def todos_by_assignee(
        self,
        info: Info,
        include_completed: bool = False,
    ) -> List["AssigneeColumn"]:
        """Get todos grouped by assignee for board view."""
        user = require_perm(info, "todos", "read")
        if not user:
            return []

        # Get all visible todos
        base_query = TodoItem.objects.filter(
            tenant=user.tenant,
        ).filter(
            Q(is_public=True) | Q(created_by=user) | Q(assigned_to=user)
        )

        if not include_completed:
            base_query = base_query.filter(is_completed=False)

        todos = base_query.select_related(
            "created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer"
        ).order_by(
            F("reminder_date").asc(nulls_last=True),
            "-created_at",
        )

        # Group by assignee
        from collections import defaultdict
        grouped: dict[int | None, list[TodoItem]] = defaultdict(list)
        for todo in todos:
            grouped[todo.assigned_to_id].append(todo)

        # Build columns with current user first
        columns = []

        # Current user's column (even if empty)
        user_todos = grouped.pop(user.id, [])
        columns.append(AssigneeColumn(
            assignee_id=user.id,
            assignee_name=user.get_full_name() or user.email,
            is_current_user=True,
            todos=[todo_to_type(t, include_comments=False) for t in user_todos],
        ))

        # Other assignees
        from apps.tenants.models import User as TenantUser
        assignee_ids = [aid for aid in grouped.keys() if aid is not None]
        assignees_by_id = {u.id: u for u in TenantUser.objects.filter(id__in=assignee_ids)}

        for assignee_id in sorted(assignee_ids, key=lambda x: assignees_by_id.get(x, TenantUser()).email or ""):
            assignee = assignees_by_id.get(assignee_id)
            if assignee:
                columns.append(AssigneeColumn(
                    assignee_id=assignee_id,
                    assignee_name=assignee.get_full_name() or assignee.email,
                    is_current_user=False,
                    todos=[todo_to_type(t, include_comments=False) for t in grouped[assignee_id]],
                ))

        # Unassigned column last
        unassigned = grouped.get(None, [])
        if unassigned:
            columns.append(AssigneeColumn(
                assignee_id=None,
                assignee_name="Unassigned",
                is_current_user=False,
                todos=[todo_to_type(t, include_comments=False) for t in unassigned],
            ))

        return columns


@strawberry.type
class AssigneeColumn:
    """A column in the todo board representing an assignee."""
    assignee_id: int | None
    assignee_name: str
    is_current_user: bool
    todos: List[TodoItemType]


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
class TodoCommentResult:
    success: bool
    comment: TodoCommentType | None = None
    error: str | None = None


@strawberry.type
class ReassignResult:
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
        user, err = check_perm(info, "todos", "write")
        if err:
            return TodoCreateResult(success=False, error=err)

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
        user, err = check_perm(info, "todos", "write")
        if err:
            return TodoUpdateResult(success=False, error=err)

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
                # Set or clear completed_at timestamp
                if is_completed and not todo.completed_at:
                    from django.utils import timezone
                    todo.completed_at = timezone.now()
                    update_fields.append("completed_at")
                elif not is_completed and todo.completed_at:
                    todo.completed_at = None
                    update_fields.append("completed_at")

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
        user, err = check_perm(info, "todos", "write")
        if err:
            return DeleteResult(success=False, error=err)

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

    @strawberry.mutation
    def add_todo_comment(
        self,
        info: Info,
        todo_id: int,
        text: str,
    ) -> TodoCommentResult:
        """Add an immutable comment to a todo."""
        user, err = check_perm(info, "todos", "write")
        if err:
            return TodoCommentResult(success=False, error=err)

        # Validate text
        text = text.strip()
        if not text:
            return TodoCommentResult(success=False, error="Comment text is required")

        try:
            todo = TodoItem.objects.get(pk=todo_id, tenant=user.tenant)

            # Check if user can view this todo (public or creator or assignee)
            if not todo.is_public and todo.created_by_id != user.id and todo.assigned_to_id != user.id:
                return TodoCommentResult(success=False, error="Todo not found")

            comment = TodoComment.objects.create(
                tenant=user.tenant,
                todo=todo,
                text=text,
                author=user,
            )

            return TodoCommentResult(success=True, comment=comment_to_type(comment))
        except TodoItem.DoesNotExist:
            return TodoCommentResult(success=False, error="Todo not found")
        except Exception as e:
            return TodoCommentResult(success=False, error=str(e))

    @strawberry.mutation
    def reassign_todo_to_self(self, info: Info, todo_id: int) -> ReassignResult:
        """Reassign a todo to the current user (take over)."""
        user, err = check_perm(info, "todos", "write")
        if err:
            return ReassignResult(success=False, error=err)

        try:
            todo = TodoItem.objects.select_related(
                "created_by", "assigned_to", "contract", "contract_item__product", "contract_item__contract", "customer"
            ).get(pk=todo_id, tenant=user.tenant)

            # Can only reassign public todos or todos you created/are assigned to
            if not todo.is_public and todo.created_by_id != user.id and todo.assigned_to_id != user.id:
                return ReassignResult(success=False, error="Cannot reassign private todo")

            # Already assigned to self - no-op
            if todo.assigned_to_id == user.id:
                return ReassignResult(success=True, todo=todo_to_type(todo))

            todo.assigned_to = user
            todo.save(update_fields=["assigned_to", "updated_at"])

            return ReassignResult(success=True, todo=todo_to_type(todo))
        except TodoItem.DoesNotExist:
            return ReassignResult(success=False, error="Todo not found")
        except Exception as e:
            return ReassignResult(success=False, error=str(e))
