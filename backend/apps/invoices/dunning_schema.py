"""GraphQL schema for payment reminders (Mahnungen) and dunning settings."""
from decimal import Decimal
from typing import List, Optional

import strawberry
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, require_perm
from apps.invoices.dunning import (
    build_reminder_draft,
    calculate_fee,
    calculate_interest,
    get_dunning_settings,
    is_dunning_eligible,
)
from apps.invoices.models import InvoiceRecord, PaymentReminder


# =========================================================================
# Types
# =========================================================================


@strawberry.type
class PaymentReminderType:
    """A payment reminder (Mahnung) for a single invoice."""

    id: int
    invoice_record_id: int
    invoice_number: str
    customer_id: Optional[int]
    customer_name: str
    stage: int
    language: str
    title: str
    subject: str
    body_text: str
    fee_amount: Decimal
    interest_amount: Decimal
    interest_rate_snapshot: Decimal
    interest_days: int
    pdf_url: Optional[str]
    sent_at: Optional[str]
    sent_to: List[str]
    created_at: str


@strawberry.type
class PaymentReminderDraftType:
    """A pre-filled, non-persisted reminder draft."""

    invoice_record_id: int
    invoice_number: str
    stage: int
    language: str
    title: str
    subject: str
    body_text: str
    fee_amount: Decimal
    interest_amount: Decimal
    interest_rate: Decimal
    interest_days: int
    overdue_days: int


@strawberry.type
class DunningSettingsType:
    default_payment_term_days: int
    overdue_red_threshold_days: int
    mahnfaehig_threshold_days: int
    interest_rate: Decimal
    default_fee_per_stage: strawberry.scalars.JSON
    templates: strawberry.scalars.JSON


@strawberry.input
class DunningSettingsInput:
    default_payment_term_days: int
    overdue_red_threshold_days: int
    mahnfaehig_threshold_days: int
    interest_rate: Decimal
    default_fee_per_stage: strawberry.scalars.JSON
    templates: strawberry.scalars.JSON


@strawberry.type
class CreateReminderDraftResult:
    success: bool
    error: Optional[str] = None
    draft: Optional[PaymentReminderDraftType] = None


@strawberry.type
class PaymentReminderResult:
    success: bool
    error: Optional[str] = None
    reminder: Optional[PaymentReminderType] = None


@strawberry.type
class DunningSettingsResult:
    success: bool
    error: Optional[str] = None
    settings: Optional[DunningSettingsType] = None


# =========================================================================
# Converters
# =========================================================================


def _convert_reminder(reminder: PaymentReminder) -> PaymentReminderType:
    record = reminder.invoice_record
    return PaymentReminderType(
        id=reminder.id,
        invoice_record_id=reminder.invoice_record_id,
        invoice_number=record.invoice_number if record else "",
        customer_id=record.customer_id if record else None,
        customer_name=record.customer_name if record else "",
        stage=reminder.stage,
        language=reminder.language,
        title=reminder.title,
        subject=reminder.subject,
        body_text=reminder.body_text,
        fee_amount=reminder.fee_amount,
        interest_amount=reminder.interest_amount,
        interest_rate_snapshot=reminder.interest_rate_snapshot,
        interest_days=reminder.interest_days,
        pdf_url=reminder.pdf_file.url if reminder.pdf_file else None,
        sent_at=reminder.sent_at.isoformat() if reminder.sent_at else None,
        sent_to=reminder.sent_to or [],
        created_at=reminder.created_at.isoformat(),
    )


def _convert_settings(tenant) -> DunningSettingsType:
    settings = get_dunning_settings(tenant)
    templates = (tenant.settings or {}).get("dunning_email_templates", {})
    return DunningSettingsType(
        default_payment_term_days=int(settings["default_payment_term_days"]),
        overdue_red_threshold_days=int(settings["overdue_red_threshold_days"]),
        mahnfaehig_threshold_days=int(settings["mahnfaehig_threshold_days"]),
        interest_rate=Decimal(str(settings["interest_rate"])),
        default_fee_per_stage=settings["default_fee_per_stage"],
        templates=templates,
    )


# =========================================================================
# Query
# =========================================================================


@strawberry.type
class DunningQuery:
    @strawberry.field
    def dunning_settings(self, info: Info[Context, None]) -> DunningSettingsType:
        """Dunning settings for the tenant.

        Readable by anyone with invoice read access (the overdue red
        threshold is needed to render invoice tables).
        """
        user = require_perm(info, "invoices", "read")
        return _convert_settings(user.tenant)


# =========================================================================
# Mutation
# =========================================================================


@strawberry.type
class DunningMutation:
    @strawberry.mutation
    def create_payment_reminder(
        self,
        info: Info[Context, None],
        invoice_record_id: int,
        stage: Optional[int] = None,
    ) -> CreateReminderDraftResult:
        """Build a pre-filled reminder draft for an overdue invoice."""
        user, err = check_perm(info, "reminders", "send")
        if err:
            return CreateReminderDraftResult(success=False, error=err)

        try:
            invoice = InvoiceRecord.objects.select_related("customer", "tenant").get(
                id=invoice_record_id, tenant=user.tenant
            )
        except InvoiceRecord.DoesNotExist:
            return CreateReminderDraftResult(
                success=False, error="Invoice not found"
            )

        if not is_dunning_eligible(invoice):
            return CreateReminderDraftResult(
                success=False, error="Invoice is not eligible for dunning"
            )

        draft = build_reminder_draft(invoice, stage)
        return CreateReminderDraftResult(
            success=True,
            draft=PaymentReminderDraftType(
                invoice_record_id=invoice.id,
                invoice_number=invoice.invoice_number,
                **draft,
            ),
        )

    @strawberry.mutation
    def send_payment_reminder(
        self,
        info: Info[Context, None],
        invoice_record_id: int,
        stage: int,
        language: str,
        title: str,
        subject: str,
        body_text: str,
        include_fee: bool = True,
        include_interest: bool = True,
    ) -> PaymentReminderResult:
        """Create and dispatch a payment reminder for an overdue invoice."""
        user, err = check_perm(info, "reminders", "send")
        if err:
            return PaymentReminderResult(success=False, error=err)

        try:
            invoice = InvoiceRecord.objects.select_related("customer", "tenant").get(
                id=invoice_record_id, tenant=user.tenant
            )
        except InvoiceRecord.DoesNotExist:
            return PaymentReminderResult(success=False, error="Invoice not found")

        # Re-check payment status immediately before sending.
        if invoice.is_paid:
            return PaymentReminderResult(
                success=False, error="Invoice is already paid"
            )
        if not is_dunning_eligible(invoice):
            return PaymentReminderResult(
                success=False, error="Invoice is not eligible for dunning"
            )

        settings = get_dunning_settings(user.tenant)
        stage = max(0, min(int(stage), 3))
        fee = calculate_fee(settings, stage) if include_fee else Decimal("0")
        interest, rate, days = calculate_interest(invoice, settings)
        if not include_interest:
            interest, rate, days = Decimal("0"), Decimal("0"), 0

        reminder = PaymentReminder.objects.create(
            tenant=user.tenant,
            invoice_record=invoice,
            stage=stage,
            language=language or "de",
            title=title,
            subject=subject,
            body_text=body_text,
            fee_amount=fee,
            interest_amount=interest,
            interest_rate_snapshot=rate,
            interest_days=days,
            created_by=user,
        )

        from apps.invoices.tasks import send_dunning_email_task

        send_dunning_email_task.delay(reminder.id, user.id)

        return PaymentReminderResult(
            success=True, reminder=_convert_reminder(reminder)
        )

    @strawberry.mutation
    def save_dunning_settings(
        self, info: Info[Context, None], input: DunningSettingsInput
    ) -> DunningSettingsResult:
        """Save dunning settings (templates, interest rate, fees, thresholds)."""
        user, err = check_perm(info, "reminders", "settings")
        if err:
            return DunningSettingsResult(success=False, error=err)

        tenant = user.tenant
        tenant_settings = dict(tenant.settings or {})
        tenant_settings["dunning"] = {
            "default_payment_term_days": int(input.default_payment_term_days),
            "overdue_red_threshold_days": int(input.overdue_red_threshold_days),
            "mahnfaehig_threshold_days": int(input.mahnfaehig_threshold_days),
            "interest_rate": str(input.interest_rate),
            "default_fee_per_stage": {
                str(k): str(v)
                for k, v in (input.default_fee_per_stage or {}).items()
            },
        }
        tenant_settings["dunning_email_templates"] = input.templates or {}
        tenant.settings = tenant_settings
        tenant.save(update_fields=["settings"])

        return DunningSettingsResult(
            success=True, settings=_convert_settings(tenant)
        )
