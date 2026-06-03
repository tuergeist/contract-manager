"""Core logic for payment reminders (Mahnungen).

Pure, side-effect-free helpers: settings resolution, payment-term hierarchy,
dunning eligibility, fee/interest pre-calculation, and template lookup.
"""
from decimal import ROUND_HALF_UP, Decimal

# --- Settings ---------------------------------------------------------------

DUNNING_DEFAULTS = {
    "default_payment_term_days": 14,
    "overdue_red_threshold_days": 14,
    "mahnfaehig_threshold_days": 14,
    "interest_rate": Decimal("0"),  # annual %, configured per tenant
    "default_fee_per_stage": {"0": "0", "1": "0", "2": "0", "3": "0"},
}

# Highest supported dunning stage (0 = reminder, 1-3 = dunning notices).
MAX_STAGE = 3


def get_dunning_settings(tenant) -> dict:
    """Return effective dunning settings, tenant overrides merged over defaults."""
    stored = (getattr(tenant, "settings", None) or {}).get("dunning", {})
    settings = dict(DUNNING_DEFAULTS)
    settings.update(stored)
    # Ensure fee map always has all stages as strings.
    fees = dict(DUNNING_DEFAULTS["default_fee_per_stage"])
    fees.update(stored.get("default_fee_per_stage", {}))
    settings["default_fee_per_stage"] = fees
    return settings


def resolve_payment_term(contract, customer, tenant) -> int:
    """Resolve the payment term in days: contract -> customer -> tenant default."""
    if contract is not None and contract.payment_term_days:
        return contract.payment_term_days
    if customer is not None and customer.payment_term_days:
        return customer.payment_term_days
    return int(get_dunning_settings(tenant)["default_payment_term_days"])


# --- Eligibility ------------------------------------------------------------


def is_dunning_eligible(invoice, settings: dict | None = None) -> bool:
    """Whether an invoice may be dunned.

    Eligible when it is unpaid, not voided, an invoice (not a credit note),
    and overdue by at least the configured threshold.
    """
    if invoice.status == invoice.Status.VOIDED:
        return False
    if invoice.document_type != invoice.DocumentType.INVOICE:
        return False
    if invoice.is_paid:
        return False
    # An invoice that has been credited via a storno is no longer collectable.
    if invoice.storno_records.exists():
        return False
    if settings is None:
        settings = get_dunning_settings(invoice.tenant)
    threshold = int(settings["mahnfaehig_threshold_days"])
    return invoice.overdue_days >= threshold


def suggest_next_stage(invoice) -> int:
    """Suggest the next dunning stage for an invoice (capped at MAX_STAGE)."""
    last = (
        invoice.payment_reminders.order_by("-stage")
        .values_list("stage", flat=True)
        .first()
    )
    if last is None:
        return 0
    return min(last + 1, MAX_STAGE)


# --- Fee / interest ---------------------------------------------------------


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_fee(settings: dict, stage: int) -> Decimal:
    """Suggested dunning fee for a stage."""
    fees = settings["default_fee_per_stage"]
    return _money(fees.get(str(stage), 0))


def calculate_interest(invoice, settings: dict) -> tuple[Decimal, Decimal, int]:
    """Suggested late-payment interest for an invoice.

    Returns ``(interest_amount, annual_rate, overdue_days)``.
    Formula: total_gross * rate/100 * overdue_days/365.
    """
    rate = Decimal(str(settings["interest_rate"]))
    days = invoice.overdue_days
    if rate <= 0 or days <= 0:
        return _money(0), rate, days
    interest = invoice.total_gross * (rate / Decimal("100")) * (
        Decimal(days) / Decimal("365")
    )
    return _money(interest), rate, days


# --- Templates --------------------------------------------------------------

# One template per language and stage, used for both the PDF and the email.
DEFAULT_DUNNING_TEMPLATES = {
    "de": {
        "0": {
            "title": "Zahlungserinnerung",
            "subject": "Zahlungserinnerung zu Rechnung {invoice_number}",
            "body": (
                "Sehr geehrte Damen und Herren,\n\n"
                "sicher ist es Ihrer Aufmerksamkeit entgangen: die Rechnung "
                "{invoice_number} vom {invoice_date} über {amount} ist seit "
                "{overdue_days} Tagen überfällig (fällig am {due_date}).\n\n"
                "Wir bitten Sie, den offenen Betrag zeitnah zu begleichen. "
                "Sollten Sie die Zahlung bereits veranlasst haben, "
                "betrachten Sie dieses Schreiben als gegenstandslos.\n\n"
                "Mit freundlichen Grüßen"
            ),
        },
        "1": {
            "title": "1. Mahnung",
            "subject": "1. Mahnung zu Rechnung {invoice_number}",
            "body": (
                "Sehr geehrte Damen und Herren,\n\n"
                "trotz unserer Zahlungserinnerung ist die Rechnung "
                "{invoice_number} vom {invoice_date} über {amount} weiterhin "
                "offen (fällig am {due_date}, {overdue_days} Tage überfällig).\n\n"
                "Wir bitten Sie, den offenen Betrag umgehend zu begleichen.\n\n"
                "Mit freundlichen Grüßen"
            ),
        },
        "2": {
            "title": "2. Mahnung",
            "subject": "2. Mahnung zu Rechnung {invoice_number}",
            "body": (
                "Sehr geehrte Damen und Herren,\n\n"
                "die Rechnung {invoice_number} vom {invoice_date} über "
                "{amount} ist trotz mehrfacher Aufforderung nicht beglichen "
                "({overdue_days} Tage überfällig).\n\n"
                "Wir fordern Sie letztmalig auf, den offenen Betrag "
                "einschließlich der ausgewiesenen Mahnkosten zu zahlen.\n\n"
                "Mit freundlichen Grüßen"
            ),
        },
        "3": {
            "title": "3. Mahnung",
            "subject": "3. und letzte Mahnung zu Rechnung {invoice_number}",
            "body": (
                "Sehr geehrte Damen und Herren,\n\n"
                "die Rechnung {invoice_number} vom {invoice_date} über "
                "{amount} ist weiterhin offen ({overdue_days} Tage "
                "überfällig).\n\n"
                "Sollte der offene Betrag nicht innerhalb der gesetzten Frist "
                "eingehen, behalten wir uns weitere Schritte vor.\n\n"
                "Mit freundlichen Grüßen"
            ),
        },
    },
    "en": {
        "0": {
            "title": "Payment reminder",
            "subject": "Payment reminder for invoice {invoice_number}",
            "body": (
                "Dear Sir or Madam,\n\n"
                "this may have escaped your attention: invoice "
                "{invoice_number} dated {invoice_date} for {amount} has been "
                "overdue for {overdue_days} days (due on {due_date}).\n\n"
                "Please settle the outstanding amount soon. If you have "
                "already arranged payment, please disregard this notice.\n\n"
                "Kind regards"
            ),
        },
        "1": {
            "title": "First reminder",
            "subject": "First reminder for invoice {invoice_number}",
            "body": (
                "Dear Sir or Madam,\n\n"
                "despite our payment reminder, invoice {invoice_number} dated "
                "{invoice_date} for {amount} is still outstanding (due on "
                "{due_date}, {overdue_days} days overdue).\n\n"
                "Please settle the outstanding amount immediately.\n\n"
                "Kind regards"
            ),
        },
        "2": {
            "title": "Second reminder",
            "subject": "Second reminder for invoice {invoice_number}",
            "body": (
                "Dear Sir or Madam,\n\n"
                "invoice {invoice_number} dated {invoice_date} for {amount} "
                "remains unpaid despite repeated requests ({overdue_days} "
                "days overdue).\n\n"
                "We ask you for the last time to pay the outstanding amount "
                "including the dunning charges shown.\n\n"
                "Kind regards"
            ),
        },
        "3": {
            "title": "Final reminder",
            "subject": "Final reminder for invoice {invoice_number}",
            "body": (
                "Dear Sir or Madam,\n\n"
                "invoice {invoice_number} dated {invoice_date} for {amount} "
                "is still outstanding ({overdue_days} days overdue).\n\n"
                "If the outstanding amount is not received within the set "
                "deadline, we reserve the right to take further steps.\n\n"
                "Kind regards"
            ),
        },
    },
}


def get_dunning_template(tenant, lang: str, stage: int) -> dict:
    """Return the dunning template for a language and stage.

    Prefers a tenant-specific template, falls back to the built-in default.
    A template is ``{title, subject, body}``.
    """
    lang = lang if lang in DEFAULT_DUNNING_TEMPLATES else "de"
    stage_key = str(stage)
    default = DEFAULT_DUNNING_TEMPLATES[lang].get(
        stage_key, DEFAULT_DUNNING_TEMPLATES[lang]["1"]
    )
    custom = (
        (getattr(tenant, "settings", None) or {})
        .get("dunning_email_templates", {})
        .get(lang, {})
        .get(stage_key, {})
    )
    if custom.get("title") and custom.get("subject") and custom.get("body"):
        return {
            "title": custom["title"],
            "subject": custom["subject"],
            "body": custom["body"],
        }
    return dict(default)


# --- Draft assembly ---------------------------------------------------------


def _fmt_date(value) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


def build_reminder_draft(invoice, stage: int | None = None) -> dict:
    """Build a pre-filled reminder draft for an invoice.

    Resolves stage, language, template text (placeholders filled), and the
    suggested fee / interest. Returns a plain dict; nothing is persisted.
    """
    tenant = invoice.tenant
    settings = get_dunning_settings(tenant)
    if stage is None:
        stage = suggest_next_stage(invoice)
    stage = max(0, min(int(stage), MAX_STAGE))

    customer = invoice.customer
    lang = "de"
    if customer is not None:
        lang = customer.get_effective_invoice_language(default="de")

    template = get_dunning_template(tenant, lang, stage)
    fee = calculate_fee(settings, stage)
    interest, rate, days = calculate_interest(invoice, settings)

    placeholders = {
        "invoice_number": invoice.invoice_number,
        "invoice_date": _fmt_date(invoice.invoice_date or invoice.billing_date),
        "due_date": _fmt_date(invoice.due_date),
        "overdue_days": invoice.overdue_days,
        "amount": f"{invoice.total_gross:.2f}",
    }

    def _fill(text: str) -> str:
        try:
            return text.format(**placeholders)
        except (KeyError, ValueError, IndexError):
            return text

    return {
        "stage": stage,
        "language": lang,
        "title": template["title"],
        "subject": _fill(template["subject"]),
        "body_text": _fill(template["body"]),
        "fee_amount": fee,
        "interest_amount": interest,
        "interest_rate": rate,
        "interest_days": days,
        "overdue_days": invoice.overdue_days,
    }
