"""GraphQL schema for offers."""
from datetime import date
from decimal import Decimal
from typing import List

import strawberry
from django.db.models import Q
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, require_perm
from apps.core.schema import DeleteResult


# =========================================================================
# Types
# =========================================================================


@strawberry.type
class OfferRecordType:
    """A persisted offer record."""

    id: int
    offer_number: str
    contract_id: int | None
    contract_name: str
    customer_id: int | None
    customer_name: str
    offer_date: date
    valid_until: date | None
    billing_date: date
    period_start: date
    period_end: date
    total_net: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_gross: Decimal
    status: str
    created_at: str
    line_items_snapshot: strawberry.scalars.JSON
    notes: str
    pdf_url: str | None
    vat_sentence: str
    customer_billing_emails: list[str]
    email_sent_at: str | None
    email_sent_to: list[str]
    email_message_id: str
    scoped_item_ids: list[int] | None = None


@strawberry.type
class OfferRecordConnection:
    """Paginated list of offer records."""

    items: List[OfferRecordType]
    total_count: int
    has_next_page: bool


@strawberry.type
class CreateOfferResult:
    success: bool
    error: str | None = None
    offer: OfferRecordType | None = None


@strawberry.type
class UpdateOfferStatusResult:
    success: bool
    error: str | None = None
    offer: OfferRecordType | None = None


@strawberry.type
class UpdateOfferResult:
    success: bool
    error: str | None = None
    offer: OfferRecordType | None = None


# =========================================================================
# Offer Number Scheme types
# =========================================================================


@strawberry.type
class OfferNumberSchemeType:
    """Offer number scheme configuration."""

    pattern: str
    next_counter: int
    reset_period: str
    preview: str


@strawberry.input
class OfferNumberSchemeInput:
    """Input for saving offer number scheme."""

    pattern: str
    reset_period: str = "yearly"
    next_counter: int | None = None


@strawberry.type
class OfferNumberSchemeResult:
    success: bool
    error: str | None = None
    data: OfferNumberSchemeType | None = None


# =========================================================================
# Helpers
# =========================================================================


def _convert_offer_record(record) -> OfferRecordType:
    return OfferRecordType(
        id=record.id,
        offer_number=record.offer_number,
        contract_id=record.contract_id,
        contract_name=record.contract_name,
        customer_id=record.customer_id,
        customer_name=record.customer_name,
        offer_date=record.offer_date,
        valid_until=record.valid_until,
        billing_date=record.billing_date,
        period_start=record.period_start,
        period_end=record.period_end,
        total_net=record.total_net,
        tax_rate=record.tax_rate,
        tax_amount=record.tax_amount,
        total_gross=record.total_gross,
        status=record.status,
        created_at=record.created_at.isoformat(),
        line_items_snapshot=record.line_items_snapshot,
        notes=record.notes or "",
        pdf_url=record.pdf_file.url if record.pdf_file else None,
        vat_sentence=record.vat_sentence or "",
        customer_billing_emails=(record.customer.billing_emails or []) if record.customer else [],
        email_sent_at=record.email_sent_at.isoformat() if record.email_sent_at else None,
        email_sent_to=record.email_sent_to or [],
        email_message_id=record.email_message_id or "",
        scoped_item_ids=record.scoped_item_ids,
    )


# =========================================================================
# Query
# =========================================================================


@strawberry.type
class OfferQuery:
    """Offer-related queries."""

    @strawberry.field
    def offer(self, info: Info, id: int) -> OfferRecordType | None:
        """Get a single offer record by ID."""
        from apps.offers.models import OfferRecord

        user = require_perm(info, "offers", "read")
        try:
            record = OfferRecord.objects.select_related("customer").get(
                id=id, tenant=user.tenant
            )
        except OfferRecord.DoesNotExist:
            return None
        return _convert_offer_record(record)

    @strawberry.field
    def offers(
        self,
        info: Info,
        search: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = None,
        sort_order: str | None = "desc",
        offset: int = 0,
        limit: int = 50,
    ) -> OfferRecordConnection:
        """Get paginated offer records."""
        from apps.offers.models import OfferRecord

        user = require_perm(info, "offers", "read")

        qs = OfferRecord.objects.filter(
            tenant=user.tenant,
        ).select_related("customer")

        if status:
            qs = qs.filter(status=status)

        if date_from:
            qs = qs.filter(offer_date__gte=date_from)

        if date_to:
            qs = qs.filter(offer_date__lte=date_to)

        if search:
            qs = qs.filter(
                Q(offer_number__icontains=search)
                | Q(customer_name__icontains=search)
                | Q(contract_name__icontains=search)
            )

        allowed_sort_fields = {
            "offerNumber": "offer_number",
            "offerDate": "offer_date",
            "customerName": "customer_name",
            "totalGross": "total_gross",
            "validUntil": "valid_until",
            "status": "status",
        }
        if sort_by and sort_by in allowed_sort_fields:
            order_field = allowed_sort_fields[sort_by]
            if sort_order == "desc":
                order_field = f"-{order_field}"
            qs = qs.order_by(order_field)
        else:
            qs = qs.order_by("-offer_date", "-created_at")

        total_count = qs.count()
        items = qs[offset : offset + limit]
        has_next_page = offset + limit < total_count

        return OfferRecordConnection(
            items=[_convert_offer_record(r) for r in items],
            total_count=total_count,
            has_next_page=has_next_page,
        )

    @strawberry.field
    def offer_number_scheme(self, info: Info) -> OfferNumberSchemeType | None:
        """Get the tenant's offer number scheme."""
        user = require_perm(info, "settings", "read")
        from apps.offers.numbering import OfferNumberService

        service = OfferNumberService(user.tenant)
        scheme = service._get_or_create_scheme()
        preview = service.preview_next_number()
        return OfferNumberSchemeType(
            pattern=scheme.pattern,
            next_counter=scheme.next_counter,
            reset_period=scheme.reset_period,
            preview=preview,
        )

    @strawberry.field
    def offers_for_contract(
        self,
        info: Info,
        contract_id: int,
    ) -> List[OfferRecordType]:
        """Get all offers for a specific contract (used for forecast tab matching)."""
        from apps.offers.models import OfferRecord

        user = require_perm(info, "offers", "read")
        records = OfferRecord.objects.filter(
            tenant=user.tenant,
            contract_id=contract_id,
        ).select_related("customer").order_by("-billing_date")
        return [_convert_offer_record(r) for r in records]


# =========================================================================
# Mutation
# =========================================================================


# Valid status transitions
_VALID_TRANSITIONS = {
    "draft": {"sent", "cancelled"},
    "sent": {"accepted", "rejected", "cancelled"},
}


@strawberry.type
class OfferMutation:
    """Offer-related mutations."""

    @strawberry.mutation
    def create_offer(
        self, info: Info[Context, None], contract_id: int, billing_date: date,
        item_ids: list[int] | None = None,
    ) -> CreateOfferResult:
        """Create an offer from a contract billing event."""
        user, err = check_perm(info, "offers", "write")
        if err:
            return CreateOfferResult(success=False, error=err)

        from apps.offers.services import OfferService

        try:
            service = OfferService(user.tenant)
            record = service.create_offer(contract_id, billing_date, item_ids=item_ids)
            return CreateOfferResult(
                success=True,
                offer=_convert_offer_record(record),
            )
        except Exception as e:
            return CreateOfferResult(success=False, error=str(e))

    @strawberry.mutation
    def update_offer_status(
        self, info: Info[Context, None], id: int, status: str
    ) -> UpdateOfferStatusResult:
        """Update an offer's status with transition validation."""
        from apps.offers.models import OfferRecord

        user, err = check_perm(info, "offers", "write")
        if err:
            return UpdateOfferStatusResult(success=False, error=err)

        try:
            record = OfferRecord.objects.get(id=id, tenant=user.tenant)
        except OfferRecord.DoesNotExist:
            return UpdateOfferStatusResult(success=False, error="Offer not found")

        valid_statuses = {c[0] for c in OfferRecord.Status.choices}
        if status not in valid_statuses:
            return UpdateOfferStatusResult(
                success=False,
                error=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
            )

        allowed_next = _VALID_TRANSITIONS.get(record.status, set())
        if status not in allowed_next:
            return UpdateOfferStatusResult(
                success=False,
                error=f"Cannot transition from '{record.status}' to '{status}'.",
            )

        record.status = status
        record.save(update_fields=["status", "updated_at"])
        record.refresh_from_db()
        return UpdateOfferStatusResult(
            success=True,
            offer=_convert_offer_record(record),
        )

    @strawberry.mutation
    def update_offer(
        self,
        info: Info[Context, None],
        id: int,
        valid_until: date | None = None,
        notes: str | None = None,
    ) -> UpdateOfferResult:
        """Update editable fields on a draft offer."""
        from apps.offers.models import OfferRecord

        user, err = check_perm(info, "offers", "write")
        if err:
            return UpdateOfferResult(success=False, error=err)

        try:
            record = OfferRecord.objects.get(id=id, tenant=user.tenant)
        except OfferRecord.DoesNotExist:
            return UpdateOfferResult(success=False, error="Offer not found")

        if record.status != OfferRecord.Status.DRAFT:
            return UpdateOfferResult(
                success=False, error="Only draft offers can be edited."
            )

        update_fields = ["updated_at"]
        if valid_until is not None:
            record.valid_until = valid_until
            update_fields.append("valid_until")
        if notes is not None:
            record.notes = notes
            update_fields.append("notes")

        record.save(update_fields=update_fields)
        record.refresh_from_db()
        return UpdateOfferResult(
            success=True,
            offer=_convert_offer_record(record),
        )

    @strawberry.mutation
    def delete_offer(self, info: Info[Context, None], id: int) -> DeleteResult:
        """Delete a draft offer."""
        from apps.offers.models import OfferRecord

        user, err = check_perm(info, "offers", "delete")
        if err:
            return DeleteResult(success=False, error=err)

        try:
            record = OfferRecord.objects.get(id=id, tenant=user.tenant)
        except OfferRecord.DoesNotExist:
            return DeleteResult(success=False, error="Offer not found")

        if record.status != OfferRecord.Status.DRAFT:
            return DeleteResult(
                success=False, error="Only draft offers can be deleted."
            )

        record.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def send_offer_email(
        self,
        info: Info[Context, None],
        id: int,
        recipients: List[str],
    ) -> UpdateOfferStatusResult:
        """Send offer email to specified recipients."""
        from apps.offers.models import OfferRecord

        user, err = check_perm(info, "offers", "write")
        if err:
            return UpdateOfferStatusResult(success=False, error=err)

        try:
            record = OfferRecord.objects.get(id=id, tenant=user.tenant)
        except OfferRecord.DoesNotExist:
            return UpdateOfferStatusResult(success=False, error="Offer not found")

        if not record.pdf_file:
            return UpdateOfferStatusResult(
                success=False, error="Offer has no PDF file."
            )

        if not recipients:
            return UpdateOfferStatusResult(
                success=False, error="At least one recipient is required."
            )

        from apps.offers.tasks import send_offer_email_task

        send_offer_email_task.delay(record.id, recipients, user.id)
        return UpdateOfferStatusResult(
            success=True,
            offer=_convert_offer_record(record),
        )

    @strawberry.mutation
    def save_offer_number_scheme(
        self, info: Info[Context, None], input: OfferNumberSchemeInput
    ) -> OfferNumberSchemeResult:
        """Save offer number scheme for the tenant."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return OfferNumberSchemeResult(success=False, error=err)

        from apps.offers.models import OfferNumberScheme
        from apps.offers.numbering import OfferNumberService

        errors = OfferNumberService.validate_pattern(input.pattern)
        if errors:
            return OfferNumberSchemeResult(
                success=False, error="; ".join(errors)
            )

        valid_periods = [c[0] for c in OfferNumberScheme.ResetPeriod.choices]
        if input.reset_period not in valid_periods:
            return OfferNumberSchemeResult(
                success=False,
                error=f"Invalid reset period. Must be one of: {', '.join(valid_periods)}",
            )

        defaults = {
            "pattern": input.pattern,
            "reset_period": input.reset_period,
        }
        if input.next_counter is not None:
            if input.next_counter < 1:
                return OfferNumberSchemeResult(
                    success=False, error="Counter must be at least 1."
                )
            defaults["next_counter"] = input.next_counter

        scheme, _ = OfferNumberScheme.objects.update_or_create(
            tenant=user.tenant,
            defaults=defaults,
        )

        service = OfferNumberService(user.tenant)
        preview = service.preview_next_number()

        return OfferNumberSchemeResult(
            success=True,
            data=OfferNumberSchemeType(
                pattern=scheme.pattern,
                next_counter=scheme.next_counter,
                reset_period=scheme.reset_period,
                preview=preview,
            ),
        )
