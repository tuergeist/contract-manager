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
    # New editable surface (offer-edit-and-finalize change)
    free_text_after_items: str = ""
    free_text_before_terms: str = ""
    minimum_term_months: int | None = None
    notice_period_months: int | None = None
    cloned_from_id: int | None = None
    is_locked: bool = False


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
    # Distinguish lock errors from validation errors so the frontend can
    # surface a "this offer is locked" banner directly. See
    # openspec/specs/offer-finalize/spec.md.
    is_locked_error: bool = False


@strawberry.input
class UpdateOfferInput:
    """Editable surface for the new updateOffer mutation.

    Matches OfferRecord._user_editable_fields(). Anything else is rejected
    by the service layer.
    """

    free_text_after_items: str | None = None
    free_text_before_terms: str | None = None
    valid_until: date | None = strawberry.UNSET
    minimum_term_months: int | None = strawberry.UNSET
    notice_period_months: int | None = strawberry.UNSET
    scoped_item_ids: list[int] | None = strawberry.UNSET


@strawberry.type
class FinalizeOfferResult:
    success: bool
    error: str | None = None
    offer: OfferRecordType | None = None
    is_locked_error: bool = False


@strawberry.type
class CloneOfferResult:
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
        free_text_after_items=record.free_text_after_items or "",
        free_text_before_terms=record.free_text_before_terms or "",
        minimum_term_months=record.minimum_term_months,
        notice_period_months=record.notice_period_months,
        cloned_from_id=record.cloned_from_id,
        is_locked=record.is_locked,
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
        """Deprecated. Use `finalizeOffer`, `sendOfferEmail`, or `deleteOffer`.

        Kept as a stub so existing GraphQL clients receive a clear error
        rather than an unknown-field response. The offer lifecycle is now
        `draft -> sent | finalized` and there is no manual transition.
        """
        return UpdateOfferStatusResult(
            success=False,
            error=(
                "updateOfferStatus is deprecated. The offer lifecycle is "
                "draft -> sent (via sendOfferEmail) or draft -> finalized "
                "(via finalizeOffer). Use deleteOffer to remove a draft."
            ),
        )

    @strawberry.mutation
    def update_offer(
        self,
        info: Info[Context, None],
        id: int,
        input: UpdateOfferInput,
    ) -> UpdateOfferResult:
        """Update editable fields on a draft offer.

        Accepts only the editable surface defined in
        OfferRecord._user_editable_fields(). Service layer enforces lock
        via select_for_update + _guard_writable.
        """
        from apps.offers.models import OfferRecord
        from apps.offers.services import OfferLockedError, OfferService

        user, err = check_perm(info, "offers", "write")
        if err:
            return UpdateOfferResult(success=False, error=err)

        # Build the fields dict, treating absent (UNSET) as "do not touch"
        # while letting None through explicitly for nullable fields.
        fields: dict = {}
        if input.free_text_after_items is not None:
            fields["free_text_after_items"] = input.free_text_after_items
        if input.free_text_before_terms is not None:
            fields["free_text_before_terms"] = input.free_text_before_terms
        if input.valid_until is not strawberry.UNSET:
            fields["valid_until"] = input.valid_until
        if input.minimum_term_months is not strawberry.UNSET:
            fields["minimum_term_months"] = input.minimum_term_months
        if input.notice_period_months is not strawberry.UNSET:
            fields["notice_period_months"] = input.notice_period_months
        if input.scoped_item_ids is not strawberry.UNSET:
            fields["scoped_item_ids"] = input.scoped_item_ids

        if not fields:
            return UpdateOfferResult(
                success=False, error="No fields supplied to update."
            )

        try:
            service = OfferService(user.tenant)
            record = service.update_offer(id, **fields)
        except OfferRecord.DoesNotExist:
            return UpdateOfferResult(success=False, error="Offer not found")
        except OfferLockedError as e:
            return UpdateOfferResult(
                success=False, error=str(e), is_locked_error=True
            )
        except ValueError as e:
            return UpdateOfferResult(success=False, error=str(e))

        return UpdateOfferResult(
            success=True, offer=_convert_offer_record(record)
        )

    @strawberry.mutation
    def recreate_offer_from_contract(
        self,
        info: Info[Context, None],
        id: int,
    ) -> UpdateOfferResult:
        """Re-snapshot the contract's current billing data into a draft.

        Preserves user-edited fields and the offer_number. Rejects locked
        offers via OfferLockedError. Reports NoBillingEventError when the
        contract was edited so the offer's billing_date no longer has a
        matching event.
        """
        from apps.offers.models import OfferRecord
        from apps.offers.services import (
            NoBillingEventError,
            OfferLockedError,
            OfferService,
        )

        user, err = check_perm(info, "offers", "write")
        if err:
            return UpdateOfferResult(success=False, error=err)

        try:
            service = OfferService(user.tenant)
            record = service.recreate_offer_from_contract(id)
        except OfferRecord.DoesNotExist:
            return UpdateOfferResult(success=False, error="Offer not found")
        except OfferLockedError as e:
            return UpdateOfferResult(
                success=False, error=str(e), is_locked_error=True
            )
        except NoBillingEventError as e:
            return UpdateOfferResult(success=False, error=str(e))
        except ValueError as e:
            return UpdateOfferResult(success=False, error=str(e))

        return UpdateOfferResult(
            success=True, offer=_convert_offer_record(record)
        )

    @strawberry.mutation
    def finalize_offer(
        self,
        info: Info[Context, None],
        id: int,
    ) -> FinalizeOfferResult:
        """Transition a draft offer to finalized.

        Gated on the new `offers.finalize` permission. Idempotent on
        already-finalized records. Rejects sent + legacy statuses with
        is_locked_error=True so the frontend can show a precise banner.
        """
        from apps.offers.models import OfferRecord
        from apps.offers.services import OfferLockedError, OfferService

        user, err = check_perm(info, "offers", "finalize")
        if err:
            return FinalizeOfferResult(success=False, error=err)

        try:
            service = OfferService(user.tenant)
            record = service.finalize_offer(id)
        except OfferRecord.DoesNotExist:
            return FinalizeOfferResult(success=False, error="Offer not found")
        except OfferLockedError as e:
            return FinalizeOfferResult(
                success=False, error=str(e), is_locked_error=True
            )

        return FinalizeOfferResult(
            success=True, offer=_convert_offer_record(record)
        )

    @strawberry.mutation
    def clone_offer_to_draft(
        self,
        info: Info[Context, None],
        id: int,
    ) -> CloneOfferResult:
        """Copy-to-edit a locked offer into a new draft.

        Reads the source offer's snapshots verbatim (does NOT re-read the
        contract). New offer_number; cloned_from points back to the
        source for audit.
        """
        from apps.offers.models import OfferRecord
        from apps.offers.services import OfferService

        user, err = check_perm(info, "offers", "write")
        if err:
            return CloneOfferResult(success=False, error=err)

        try:
            service = OfferService(user.tenant)
            record = service.clone_offer_to_draft(id)
        except OfferRecord.DoesNotExist:
            return CloneOfferResult(success=False, error="Offer not found")
        except ValueError as e:
            return CloneOfferResult(success=False, error=str(e))

        return CloneOfferResult(
            success=True, offer=_convert_offer_record(record)
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
