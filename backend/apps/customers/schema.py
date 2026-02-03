"""GraphQL schema for customers."""
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, List
import base64
import os

import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q

from apps.core.context import Context
from apps.core.permissions import get_current_user
from apps.core.schema import DeleteResult
from .models import Customer, CustomerAttachment, CustomerLink

if TYPE_CHECKING:
    from apps.contracts.schema import ContractType
    from apps.todos.schema import TodoItemType


# =============================================================================
# Type Definitions
# =============================================================================


@strawberry.type
class CustomerAttachmentType:
    """A file attachment for a customer."""

    id: int
    original_filename: str
    file_size: int
    content_type: str
    description: str
    uploaded_at: datetime
    uploaded_by_name: str | None
    download_url: str


@strawberry.type
class CustomerLinkType:
    """A named link attached to a customer."""

    id: int
    name: str
    url: str
    created_at: datetime
    created_by_name: str | None


@strawberry_django.type(Customer)
class CustomerType:
    id: auto
    name: auto
    hubspot_id: auto
    netsuite_customer_number: auto
    address: auto
    is_active: auto
    synced_at: auto
    created_at: auto

    @strawberry.field
    def hubspot_url(self, info: Info[Context, None]) -> str | None:
        """Get the HubSpot company URL if this customer was synced from HubSpot."""
        if not self.hubspot_id:
            return None
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = user.tenant.hubspot_config or {}
        portal_id = config.get("portal_id")
        if not portal_id:
            return None
        return f"https://app-eu1.hubspot.com/contacts/{portal_id}/company/{self.hubspot_id}"

    @strawberry.field
    def contracts(self) -> List[Annotated["ContractType", strawberry.lazy("apps.contracts.schema")]]:
        """Get all contracts for this customer."""
        from apps.contracts.models import Contract

        return list(Contract.objects.filter(customer=self).order_by("-created_at"))

    @strawberry.field
    def active_contract_count(self) -> int:
        """Get the number of active contracts for this customer."""
        from apps.contracts.models import Contract

        return Contract.objects.filter(
            customer=self,
            status=Contract.Status.ACTIVE,
        ).count()

    @strawberry.field
    def attachments(self) -> List[CustomerAttachmentType]:
        """Get all file attachments for this customer."""
        attachments = CustomerAttachment.objects.filter(customer=self).select_related("uploaded_by")
        return [
            CustomerAttachmentType(
                id=a.id,
                original_filename=a.original_filename,
                file_size=a.file_size,
                content_type=a.content_type,
                description=a.description,
                uploaded_at=a.created_at,
                uploaded_by_name=a.uploaded_by.email if a.uploaded_by else None,
                download_url=f"/api/customer-attachments/{a.id}/download/",
            )
            for a in attachments
        ]

    @strawberry.field
    def links(self) -> List[CustomerLinkType]:
        """Get all links for this customer."""
        links = CustomerLink.objects.filter(customer=self).select_related("created_by")
        return [
            CustomerLinkType(
                id=link.id,
                name=link.name,
                url=link.url,
                created_at=link.created_at,
                created_by_name=link.created_by.email if link.created_by else None,
            )
            for link in links
        ]

    @strawberry.field
    def todos(self, info: Info[Context, None]) -> List[Annotated["TodoItemType", strawberry.lazy("apps.todos.schema")]]:
        """Get todos for this customer visible to the current user."""
        from apps.todos.models import TodoItem
        from apps.todos.schema import todo_to_type

        user = get_current_user(info)
        if not user:
            return []

        # Get todos: user's own todos OR public todos from team
        todos = TodoItem.objects.filter(
            customer=self,
        ).filter(
            Q(created_by=user) | Q(is_public=True)
        ).select_related("created_by").order_by("-created_at")

        return [todo_to_type(todo) for todo in todos]


@strawberry.type
class CustomerConnection:
    """Paginated customer list."""

    items: list[CustomerType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool
    has_previous_page: bool


# =============================================================================
# Input and Result Types
# =============================================================================


@strawberry.input
class UploadCustomerAttachmentInput:
    """Input for uploading a file attachment to a customer."""

    customer_id: strawberry.ID
    file_content: str  # Base64-encoded file content
    filename: str
    content_type: str
    description: str = ""


@strawberry.input
class AddCustomerLinkInput:
    """Input for adding a link to a customer."""

    customer_id: strawberry.ID
    name: str
    url: str


@strawberry.type
class CustomerAttachmentResult:
    """Result of customer attachment operations."""

    attachment: CustomerAttachmentType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class CustomerLinkResult:
    """Result of customer link operations."""

    link: CustomerLinkType | None = None
    success: bool = False
    error: str | None = None


# =============================================================================
# Queries
# =============================================================================


@strawberry.type
class CustomerQuery:
    @strawberry.field
    def customers(
        self,
        info: Info[Context, None],
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = "name",
        sort_order: str | None = "asc",
    ) -> CustomerConnection:
        user = get_current_user(info)
        if not user.tenant:
            return CustomerConnection(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next_page=False,
                has_previous_page=False,
            )

        queryset = Customer.objects.filter(tenant=user.tenant)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(netsuite_customer_number__icontains=search)
            )

        # Sorting
        allowed_sort_fields = {"name", "is_active", "synced_at", "created_at"}
        if sort_by and sort_by in allowed_sort_fields:
            order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
            queryset = queryset.order_by(order_field)
        else:
            queryset = queryset.order_by("name")

        total_count = queryset.count()

        # Calculate pagination
        offset = (page - 1) * page_size
        items = list(queryset[offset : offset + page_size])

        return CustomerConnection(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=offset + page_size < total_count,
            has_previous_page=page > 1,
        )

    @strawberry.field
    def customer(self, info: Info[Context, None], id: strawberry.ID) -> CustomerType | None:
        user = get_current_user(info)
        if user.tenant:
            return Customer.objects.filter(tenant=user.tenant, id=id).first()
        return None


# =============================================================================
# Mutations
# =============================================================================


@strawberry.type
class CustomerMutation:
    # =========================================================================
    # Customer Attachment Mutations
    # =========================================================================

    @strawberry.mutation
    def upload_customer_attachment(
        self,
        info: Info[Context, None],
        input: UploadCustomerAttachmentInput,
    ) -> CustomerAttachmentResult:
        """Upload a file attachment to a customer."""
        user = get_current_user(info)
        if not user.tenant:
            return CustomerAttachmentResult(error="No tenant assigned")

        # Verify customer belongs to tenant
        customer = Customer.objects.filter(
            tenant=user.tenant, id=input.customer_id
        ).first()
        if not customer:
            return CustomerAttachmentResult(error="Customer not found")

        # Validate filename extension
        ext = os.path.splitext(input.filename)[1].lower()
        if ext not in settings.ALLOWED_ATTACHMENT_EXTENSIONS:
            return CustomerAttachmentResult(error=f"File type {ext} not allowed")

        # Decode and validate file size
        try:
            file_bytes = base64.b64decode(input.file_content)
        except Exception:
            return CustomerAttachmentResult(error="Invalid base64 file content")

        file_size = len(file_bytes)
        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            return CustomerAttachmentResult(error=f"File too large. Maximum size is {max_mb:.0f}MB")

        try:
            # Create attachment
            attachment = CustomerAttachment.objects.create(
                tenant=user.tenant,
                customer=customer,
                original_filename=input.filename,
                file_size=file_size,
                content_type=input.content_type,
                description=input.description,
                uploaded_by=user,
            )

            # Save file
            content_file = ContentFile(file_bytes, name=input.filename)
            attachment.file.save(input.filename, content_file, save=True)

            return CustomerAttachmentResult(
                attachment=CustomerAttachmentType(
                    id=attachment.id,
                    original_filename=attachment.original_filename,
                    file_size=attachment.file_size,
                    content_type=attachment.content_type,
                    description=attachment.description,
                    uploaded_at=attachment.created_at,
                    uploaded_by_name=user.email,
                    download_url=f"/api/customer-attachments/{attachment.id}/download/",
                ),
                success=True,
            )
        except Exception as e:
            return CustomerAttachmentResult(error=str(e))

    @strawberry.mutation
    def delete_customer_attachment(
        self,
        info: Info[Context, None],
        attachment_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete a customer file attachment."""
        user = get_current_user(info)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        attachment = CustomerAttachment.objects.filter(
            tenant=user.tenant, id=attachment_id
        ).first()
        if not attachment:
            return DeleteResult(error="Attachment not found")

        try:
            attachment.delete()  # Will also delete the file from storage
            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    # =========================================================================
    # Customer Link Mutations
    # =========================================================================

    @strawberry.mutation
    def add_customer_link(
        self,
        info: Info[Context, None],
        input: AddCustomerLinkInput,
    ) -> CustomerLinkResult:
        """Add a link to a customer."""
        user = get_current_user(info)
        if not user.tenant:
            return CustomerLinkResult(error="No tenant assigned")

        # Verify customer belongs to tenant
        customer = Customer.objects.filter(
            tenant=user.tenant, id=input.customer_id
        ).first()
        if not customer:
            return CustomerLinkResult(error="Customer not found")

        try:
            link = CustomerLink.objects.create(
                tenant=user.tenant,
                customer=customer,
                name=input.name,
                url=input.url,
                created_by=user,
            )

            return CustomerLinkResult(
                link=CustomerLinkType(
                    id=link.id,
                    name=link.name,
                    url=link.url,
                    created_at=link.created_at,
                    created_by_name=user.email,
                ),
                success=True,
            )
        except Exception as e:
            return CustomerLinkResult(error=str(e))

    @strawberry.mutation
    def delete_customer_link(
        self,
        info: Info[Context, None],
        link_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete a customer link."""
        user = get_current_user(info)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        link = CustomerLink.objects.filter(
            tenant=user.tenant, id=link_id
        ).first()
        if not link:
            return DeleteResult(error="Link not found")

        try:
            link.delete()
            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))
