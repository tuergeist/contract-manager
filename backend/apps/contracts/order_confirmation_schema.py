"""GraphQL types and mutations for order confirmations."""
from datetime import datetime

import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm
from apps.contracts.order_confirmation_models import OrderConfirmation


@strawberry_django.type(OrderConfirmation)
class OrderConfirmationType:
    """An order confirmation (Auftragsbestätigung) for a contract."""

    id: auto
    order_confirmation_number: auto
    status: auto
    personal_message: auto
    include_message_in_pdf: auto
    include_message_in_email: auto
    additional_emails: auto
    language: auto
    sent_at: auto
    sent_to: auto
    email_message_id: auto
    created_at: auto
    updated_at: auto

    @strawberry.field
    def pdf_url(self) -> str | None:
        """URL to the PDF file, if available."""
        if self.pdf_file and self.pdf_file.name:
            return self.pdf_file.url
        return None

    @strawberry.field
    def contract_id(self) -> strawberry.ID:
        return strawberry.ID(str(self.contract_id))

    @strawberry.field
    def created_by_name(self) -> str:
        if self.created_by:
            return self.created_by.get_full_name() or self.created_by.email
        return ""


@strawberry.type
class OrderConfirmationResult:
    order_confirmation: OrderConfirmationType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class OrderConfirmationPreviewResult:
    html: str | None = None
    error: str | None = None


@strawberry.type
class OrderConfirmationQuery:
    @strawberry.field
    def order_confirmation(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> OrderConfirmationType | None:
        user, err = check_perm(info, "contracts", "read")
        if err or not user or not user.tenant:
            return None
        return OrderConfirmation.objects.filter(
            tenant=user.tenant, id=id
        ).first()


@strawberry.type
class OrderConfirmationMutation:
    @strawberry.mutation
    def create_order_confirmation(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        personal_message: str = "",
        include_message_in_pdf: bool = True,
        include_message_in_email: bool = True,
        additional_emails: list[str] | None = None,
    ) -> OrderConfirmationResult:
        """Create an order confirmation for a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return OrderConfirmationResult(error=err)
        if not user.tenant:
            return OrderConfirmationResult(error="No tenant assigned")

        from apps.contracts.models import Contract
        from apps.contracts.services.order_confirmation import OrderConfirmationService

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return OrderConfirmationResult(error="Contract not found")

        service = OrderConfirmationService(user.tenant)
        try:
            ab = service.create_order_confirmation(
                contract=contract,
                user=user,
                personal_message=personal_message,
                include_message_in_pdf=include_message_in_pdf,
                include_message_in_email=include_message_in_email,
                additional_emails=additional_emails,
            )
            return OrderConfirmationResult(order_confirmation=ab, success=True)
        except Exception as e:
            return OrderConfirmationResult(error=str(e))

    @strawberry.mutation
    def send_order_confirmation(
        self,
        info: Info[Context, None],
        order_confirmation_id: strawberry.ID,
    ) -> OrderConfirmationResult:
        """Send an order confirmation email."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return OrderConfirmationResult(error=err)
        if not user.tenant:
            return OrderConfirmationResult(error="No tenant assigned")

        ab = OrderConfirmation.objects.filter(
            tenant=user.tenant, id=order_confirmation_id
        ).first()
        if not ab:
            return OrderConfirmationResult(error="Order confirmation not found")

        if ab.status == OrderConfirmation.Status.SENT:
            return OrderConfirmationResult(error="Order confirmation already sent")

        from apps.contracts.tasks import send_order_confirmation_email_task
        send_order_confirmation_email_task.delay(ab.id, user_id=user.id)

        return OrderConfirmationResult(order_confirmation=ab, success=True)

    @strawberry.mutation
    def preview_order_confirmation_html(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        personal_message: str = "",
        include_message_in_pdf: bool = True,
    ) -> OrderConfirmationPreviewResult:
        """Preview the order confirmation HTML without creating a record."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return OrderConfirmationPreviewResult(error=err)
        if not user.tenant:
            return OrderConfirmationPreviewResult(error="No tenant assigned")

        from apps.contracts.models import Contract
        from apps.contracts.services.order_confirmation import OrderConfirmationService

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return OrderConfirmationPreviewResult(error="Contract not found")

        customer = contract.customer
        language = getattr(customer, "invoice_language", "") or "de"

        service = OrderConfirmationService(user.tenant)
        html = service.render_html(
            contract=contract,
            ab_number="PREVIEW",
            personal_message=personal_message,
            include_message_in_pdf=include_message_in_pdf,
            language=language,
        )
        return OrderConfirmationPreviewResult(html=html)
