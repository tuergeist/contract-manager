"""GraphQL types and mutations for order confirmations."""
from datetime import datetime

import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, require_perm, get_current_user
from apps.contracts.order_confirmation_models import OrderConfirmation, OrderConfirmationNumberScheme
from apps.tenants.schema import OperationResult


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
class OrderConfirmationNumberSchemeType:
    pattern: str
    next_counter: int
    reset_period: str
    preview: str


@strawberry.type
class OrderConfirmationNumberSchemeResult:
    success: bool = False
    error: str | None = None
    data: OrderConfirmationNumberSchemeType | None = None


@strawberry.input
class OrderConfirmationNumberSchemeInput:
    pattern: str
    reset_period: str
    next_counter: int | None = None


@strawberry.type
class ABEmailTemplate:
    language: str
    subject: str
    body: str
    is_custom: bool


@strawberry.type
class ABEmailTemplatesResult:
    success: bool = False
    error: str | None = None
    templates: list[ABEmailTemplate] | None = None


@strawberry.input
class SetABEmailTemplateInput:
    language: str
    subject: str
    body: str


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

    @strawberry.field
    def order_confirmation_number_scheme(
        self, info: Info[Context, None]
    ) -> OrderConfirmationNumberSchemeType:
        """Get the tenant's AB number scheme."""
        user = require_perm(info, "settings", "read")
        scheme, _ = OrderConfirmationNumberScheme.objects.get_or_create(
            tenant=user.tenant,
            defaults={"pattern": "AB-{YYYY}-{NNNN}", "reset_period": "yearly"},
        )
        # Generate preview
        import re
        from datetime import datetime as dt

        now = dt.now()
        preview = scheme.pattern
        preview = preview.replace("{YYYY}", str(now.year))
        preview = preview.replace("{YY}", str(now.year)[-2:])
        preview = preview.replace("{MM}", f"{now.month:02d}")
        # Replace counter placeholders
        counter = scheme.next_counter
        preview = re.sub(
            r"\{N+\}",
            lambda m: str(counter).zfill(len(m.group()) - 2),
            preview,
        )
        return OrderConfirmationNumberSchemeType(
            pattern=scheme.pattern,
            next_counter=scheme.next_counter,
            reset_period=scheme.reset_period,
            preview=preview,
        )

    @strawberry.field
    def ab_email_templates(
        self, info: Info[Context, None]
    ) -> ABEmailTemplatesResult:
        """Get AB email templates (custom or defaults) for all languages."""
        user = get_current_user(info)
        if not user.tenant:
            return ABEmailTemplatesResult(success=False, error="No tenant assigned")

        from apps.contracts.services.order_confirmation import AB_EMAIL_TEMPLATES as AB_EMAIL_DEFAULTS

        custom = (user.tenant.settings or {}).get("ab_email_templates", {})
        templates = []
        for lang in ("de", "en"):
            default = AB_EMAIL_DEFAULTS.get(lang, {})
            custom_lang = custom.get(lang, {})
            is_custom = bool(custom_lang.get("subject") and custom_lang.get("body"))
            templates.append(
                ABEmailTemplate(
                    language=lang,
                    subject=custom_lang.get("subject", "") if is_custom else default.get("subject", ""),
                    body=custom_lang.get("body", "") if is_custom else default.get("body", ""),
                    is_custom=is_custom,
                )
            )
        return ABEmailTemplatesResult(success=True, templates=templates)


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
            # Set contract OC number and create link
            from django.conf import settings as django_settings
            request = info.context.request
            origin = request.headers.get("Origin") or request.headers.get("Referer", "").rstrip("/")
            base_url = origin or getattr(django_settings, "FRONTEND_URL", "")
            OrderConfirmationService.link_to_contract(ab, user, base_url)
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
    def resend_order_confirmation(
        self,
        info: Info[Context, None],
        order_confirmation_id: strawberry.ID,
    ) -> OrderConfirmationResult:
        """Re-send an already-sent order confirmation email.

        Unlike ``send_order_confirmation`` this deliberately allows sending
        again when the OC is already SENT — e.g. after the PDF was
        re-generated with corrected data. The send service refreshes
        ``sent_at``/``sent_to`` on success.
        """
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
        language = customer.get_effective_invoice_language() if customer else "de"

        service = OrderConfirmationService(user.tenant)
        html = service.render_html(
            contract=contract,
            ab_number="PREVIEW",
            personal_message=personal_message,
            include_message_in_pdf=include_message_in_pdf,
            language=language,
        )
        return OrderConfirmationPreviewResult(html=html)

    @strawberry.mutation
    def save_order_confirmation_number_scheme(
        self,
        info: Info[Context, None],
        input: OrderConfirmationNumberSchemeInput,
    ) -> OrderConfirmationNumberSchemeResult:
        """Save AB number scheme for the tenant."""
        user = require_perm(info, "settings", "write")

        import re
        from datetime import datetime as dt

        # Validate pattern has at least one counter placeholder
        if not re.search(r"\{N+\}", input.pattern):
            return OrderConfirmationNumberSchemeResult(
                success=False, error="Pattern must contain a counter placeholder like {NNNN}"
            )

        valid_periods = [c[0] for c in OrderConfirmationNumberScheme.ResetPeriod.choices]
        if input.reset_period not in valid_periods:
            return OrderConfirmationNumberSchemeResult(
                success=False,
                error=f"Invalid reset period. Must be one of: {', '.join(valid_periods)}",
            )

        defaults = {
            "pattern": input.pattern,
            "reset_period": input.reset_period,
        }
        if input.next_counter is not None:
            if input.next_counter < 1:
                return OrderConfirmationNumberSchemeResult(
                    success=False, error="Counter must be at least 1."
                )
            defaults["next_counter"] = input.next_counter

        scheme, _ = OrderConfirmationNumberScheme.objects.update_or_create(
            tenant=user.tenant,
            defaults=defaults,
        )

        # Generate preview
        now = dt.now()
        preview = scheme.pattern
        preview = preview.replace("{YYYY}", str(now.year))
        preview = preview.replace("{YY}", str(now.year)[-2:])
        preview = preview.replace("{MM}", f"{now.month:02d}")
        counter = scheme.next_counter
        preview = re.sub(
            r"\{N+\}",
            lambda m: str(counter).zfill(len(m.group()) - 2),
            preview,
        )

        return OrderConfirmationNumberSchemeResult(
            success=True,
            data=OrderConfirmationNumberSchemeType(
                pattern=scheme.pattern,
                next_counter=scheme.next_counter,
                reset_period=scheme.reset_period,
                preview=preview,
            ),
        )

    @strawberry.mutation
    def regenerate_order_confirmation_pdf(
        self,
        info: Info[Context, None],
        order_confirmation_id: strawberry.ID,
    ) -> OrderConfirmationResult:
        """Regenerate the PDF for an order confirmation.

        Refreshes the AB language from the customer's current effective
        language (explicit invoice_language or derived from country) so a
        previously German-rendered AB for an English-speaking customer
        comes out in English on regenerate.
        """
        user, err = check_perm(info, "contracts", "write")
        if err:
            return OrderConfirmationResult(error=err)
        if not user.tenant:
            return OrderConfirmationResult(error="No tenant assigned")

        ab = OrderConfirmation.objects.filter(
            tenant=user.tenant, id=order_confirmation_id
        ).select_related("contract__customer").first()
        if not ab:
            return OrderConfirmationResult(error="Order confirmation not found")

        from django.core.files.base import ContentFile
        from apps.contracts.services.order_confirmation import OrderConfirmationService, AB_LABELS

        # Refresh language from current customer state
        customer = ab.contract.customer
        if customer:
            effective = customer.get_effective_invoice_language()
            if effective in AB_LABELS and effective != ab.language:
                ab.language = effective
                ab.save(update_fields=["language", "updated_at"])

        service = OrderConfirmationService(user.tenant)
        try:
            pdf_bytes = service.generate_pdf(
                contract=ab.contract,
                ab_number=ab.order_confirmation_number,
                personal_message=ab.personal_message or "",
                include_message_in_pdf=ab.include_message_in_pdf,
                language=ab.language,
            )
            ab.pdf_file.save(f"{ab.order_confirmation_number}.pdf", ContentFile(pdf_bytes), save=True)
            return OrderConfirmationResult(order_confirmation=ab, success=True)
        except Exception as e:
            return OrderConfirmationResult(error=str(e))

    @strawberry.mutation
    def set_ab_email_template(
        self,
        info: Info[Context, None],
        input: SetABEmailTemplateInput,
    ) -> OperationResult:
        """Save or clear a custom AB email template for a language."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")

        if input.language not in ("de", "en"):
            return OperationResult(success=False, error="Unsupported language")

        if not tenant.settings:
            tenant.settings = {}

        templates = tenant.settings.get("ab_email_templates", {})

        if input.subject.strip() and input.body.strip():
            templates[input.language] = {
                "subject": input.subject.strip(),
                "body": input.body.strip(),
            }
        else:
            templates.pop(input.language, None)

        if templates:
            tenant.settings["ab_email_templates"] = templates
        else:
            tenant.settings.pop("ab_email_templates", None)

        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)
