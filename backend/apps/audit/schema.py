"""GraphQL schema for audit logs."""

import base64
from datetime import datetime
from typing import List, Optional

import strawberry
from strawberry.types import Info

from apps.audit.models import AuditLog
from apps.core.permissions import get_current_user


@strawberry.type
class AuditLogChangeType:
    """A single field change in an audit log entry."""

    field: str
    old_value: Optional[strawberry.scalars.JSON]
    new_value: Optional[strawberry.scalars.JSON]


@strawberry.type
class AuditLogType:
    """An audit log entry."""

    id: int
    action: str
    entity_type: str
    entity_id: int
    entity_repr: str
    user_id: Optional[int]
    user_name: Optional[str]
    changes: List[AuditLogChangeType]
    timestamp: datetime
    parent_entity_type: Optional[str]
    parent_entity_id: Optional[int]


@strawberry.type
class PageInfo:
    """Pagination info for cursor-based pagination."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]


@strawberry.type
class AuditLogEdge:
    """An edge in the audit log connection."""

    node: AuditLogType
    cursor: str


@strawberry.type
class AuditLogConnection:
    """A paginated connection of audit logs."""

    edges: List[AuditLogEdge]
    page_info: PageInfo
    total_count: int


def _encode_cursor(pk: int) -> str:
    """Encode a primary key as a cursor."""
    return base64.b64encode(f"auditlog:{pk}".encode()).decode()


def _decode_cursor(cursor: str) -> int:
    """Decode a cursor to get the primary key."""
    decoded = base64.b64decode(cursor.encode()).decode()
    return int(decoded.split(":")[1])


def _convert_audit_log(log: AuditLog) -> AuditLogType:
    """Convert an AuditLog model instance to GraphQL type."""
    changes = [
        AuditLogChangeType(
            field=field_name,
            old_value=change.get("old"),
            new_value=change.get("new"),
        )
        for field_name, change in (log.changes or {}).items()
    ]

    return AuditLogType(
        id=log.id,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        entity_repr=log.entity_repr,
        user_id=log.user_id,
        user_name=log.user.email if log.user else None,
        changes=changes,
        timestamp=log.timestamp,
        parent_entity_type=log.parent_entity_type,
        parent_entity_id=log.parent_entity_id,
    )


@strawberry.type
class AuditLogQuery:
    """Audit log queries."""

    @strawberry.field
    def audit_logs(
        self,
        info: Info,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        include_related: bool = False,
        first: int = 25,
        after: Optional[str] = None,
    ) -> AuditLogConnection:
        """Get audit logs with filtering and pagination.

        Args:
            entity_type: Filter by entity type (e.g., 'contract', 'customer')
            entity_id: Filter by entity ID (requires entity_type)
            user_id: Filter by user ID
            action: Filter by action type ('create', 'update', 'delete')
            include_related: Include related entity changes (e.g., contract items for contracts)
            first: Number of items to fetch (max 100)
            after: Cursor for pagination
        """
        user = get_current_user(info)
        tenant = user.tenant

        # Start with tenant-scoped queryset
        queryset = AuditLog.objects.filter(tenant=tenant)

        # Apply filters
        from django.db.models import Q

        if entity_type and entity_id:
            if include_related:
                # Include both the entity itself and related entities
                queryset = queryset.filter(
                    Q(entity_type=entity_type, entity_id=entity_id)
                    | Q(parent_entity_type=entity_type, parent_entity_id=entity_id)
                )
            else:
                queryset = queryset.filter(entity_type=entity_type, entity_id=entity_id)
        elif entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if action:
            queryset = queryset.filter(action=action)

        # Order by timestamp descending (newest first)
        queryset = queryset.order_by("-timestamp", "-id")

        # Get total count before pagination
        total_count = queryset.count()

        # Apply cursor-based pagination
        if after:
            after_id = _decode_cursor(after)
            queryset = queryset.filter(id__lt=after_id)

        # Limit results (cap at 100)
        first = min(first, 100)
        logs = list(queryset[: first + 1])

        # Check if there are more results
        has_next_page = len(logs) > first
        if has_next_page:
            logs = logs[:first]

        # Build edges
        edges = [
            AuditLogEdge(
                node=_convert_audit_log(log),
                cursor=_encode_cursor(log.id),
            )
            for log in logs
        ]

        # Build page info
        page_info = PageInfo(
            has_next_page=has_next_page,
            has_previous_page=after is not None,
            start_cursor=edges[0].cursor if edges else None,
            end_cursor=edges[-1].cursor if edges else None,
        )

        return AuditLogConnection(
            edges=edges,
            page_info=page_info,
            total_count=total_count,
        )
