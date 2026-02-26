"""DATEV Buchungsstapel CSV export."""
import csv
import io
from datetime import date
from decimal import Decimal

from apps.accounting.models import AccountingExport, BookingEntry
from apps.tenants.models import Tenant


# DATEV Buchungsstapel header row (116 columns, semicolon-separated)
# Only the first ~20 fields are typically used, rest are empty.
DATEV_HEADER_FIELDS = [
    "Umsatz (ohne Soll/Haben-Kz)",
    "Soll/Haben-Kennzeichen",
    "WKZ Umsatz",
    "Kurs",
    "Basis-Umsatz",
    "WKZ Basis-Umsatz",
    "Konto",
    "Gegenkonto (ohne BU-Schlüssel)",
    "BU-Schlüssel",
    "Belegdatum",
    "Belegfeld 1",
    "Belegfeld 2",
    "Skonto",
    "Buchungstext",
    "Postensperre",
    "Diverse Adressnummer",
    "Geschäftspartnerbank",
    "Sachverhalt",
    "Zinssperre",
    "Beleglink",
    # Beleginfo 1-8 (Art + Inhalt = 16 fields)
    "Beleginfo - Art 1", "Beleginfo - Inhalt 1",
    "Beleginfo - Art 2", "Beleginfo - Inhalt 2",
    "Beleginfo - Art 3", "Beleginfo - Inhalt 3",
    "Beleginfo - Art 4", "Beleginfo - Inhalt 4",
    "Beleginfo - Art 5", "Beleginfo - Inhalt 5",
    "Beleginfo - Art 6", "Beleginfo - Inhalt 6",
    "Beleginfo - Art 7", "Beleginfo - Inhalt 7",
    "Beleginfo - Art 8", "Beleginfo - Inhalt 8",
    "KOST1 - Kostenstelle",
    "KOST2 - Kostenstelle",
    "Kost-Menge",
    "EU-Land u. UStID",
    "EU-Steuersatz",
    "Abw. Versteuerungsart",
    "Sachverhalt L+L",
    "Funktionsergänzung L+L",
    "BU 49 Hauptfunktionstyp",
    "BU 49 Hauptfunktionsnummer",
    "BU 49 Funktionsergänzung",
    # Zusatzinformation 1-20 (Art + Inhalt = 40 fields)
    "Zusatzinformation - Art 1", "Zusatzinformation - Inhalt 1",
    "Zusatzinformation - Art 2", "Zusatzinformation - Inhalt 2",
    "Zusatzinformation - Art 3", "Zusatzinformation - Inhalt 3",
    "Zusatzinformation - Art 4", "Zusatzinformation - Inhalt 4",
    "Zusatzinformation - Art 5", "Zusatzinformation - Inhalt 5",
    "Zusatzinformation - Art 6", "Zusatzinformation - Inhalt 6",
    "Zusatzinformation - Art 7", "Zusatzinformation - Inhalt 7",
    "Zusatzinformation - Art 8", "Zusatzinformation - Inhalt 8",
    "Zusatzinformation - Art 9", "Zusatzinformation - Inhalt 9",
    "Zusatzinformation - Art 10", "Zusatzinformation - Inhalt 10",
    "Zusatzinformation - Art 11", "Zusatzinformation - Inhalt 11",
    "Zusatzinformation - Art 12", "Zusatzinformation - Inhalt 12",
    "Zusatzinformation - Art 13", "Zusatzinformation - Inhalt 13",
    "Zusatzinformation - Art 14", "Zusatzinformation - Inhalt 14",
    "Zusatzinformation - Art 15", "Zusatzinformation - Inhalt 15",
    "Zusatzinformation - Art 16", "Zusatzinformation - Inhalt 16",
    "Zusatzinformation - Art 17", "Zusatzinformation - Inhalt 17",
    "Zusatzinformation - Art 18", "Zusatzinformation - Inhalt 18",
    "Zusatzinformation - Art 19", "Zusatzinformation - Inhalt 19",
    "Zusatzinformation - Art 20", "Zusatzinformation - Inhalt 20",
    "Stück",
    "Gewicht",
    "Zahlweise",
    "Forderungsart",
    "Veranlagungsjahr",
    "Zugeordnete Fälligkeit",
    "Skontotyp",
    "Auftragsnummer",
    "Buchungstyp",
    "Ust-Schlüssel (Anzahlungen)",
    "EU-Land (Anzahlungen)",
    "Sachverhalt L+L (Anzahlungen)",
    "EU-Steuersatz (Anzahlungen)",
    "Erlöskonto (Anzahlungen)",
    "Herkunft-Kz",
    "Buchungs GUID",
    "KOST-Datum",
    "SEPA-Mandatsreferenz",
    "Skontosperre",
    "Gesellschaftername",
    "Beteiligtennummer",
    "Identifikationsnummer",
    "Zeichnernummer",
    "Postensperre bis",
    "Bezeichnung SoBil-Sachverhalt",
    "Kennzeichen SoBil-Buchung",
    "Festschreibung",
    "Leistungsdatum",
    "Datum Zuord. Steuerperiode",
]

NUM_DATEV_FIELDS = len(DATEV_HEADER_FIELDS)


def _format_amount(amount: Decimal) -> str:
    """Format amount in German notation (comma as decimal separator)."""
    abs_amount = abs(amount)
    return f"{abs_amount:.2f}".replace(".", ",")


def _format_belegdatum(d: date) -> str:
    """Format date as TTMM (day + month, no year — DATEV convention)."""
    return f"{d.day:02d}{d.month:02d}"


def _get_eu_ustid_field(invoice_record) -> str:
    """Build 'EU-Land u. UStID' field for EU customers.

    Format: 'NL NL123456789' (ISO code + space + full VAT ID).
    """
    if not invoice_record or not invoice_record.customer:
        return ""

    customer = invoice_record.customer
    address = customer.address or {}
    vat_id = customer.vat_id or ""

    country_raw = address.get("country", "")
    if not country_raw or not vat_id:
        return ""

    from apps.invoices.services import _get_country_iso, EU_COUNTRY_CODES
    iso = _get_country_iso(country_raw)

    # Only for EU countries (not domestic)
    if iso not in EU_COUNTRY_CODES or iso == "DE":
        return ""

    return f"{iso} {vat_id}"


def generate_datev_csv(
    tenant: Tenant,
    period_start: date,
    period_end: date,
) -> tuple[str, int, Decimal]:
    """Generate DATEV Buchungsstapel CSV content.

    Returns: (csv_content, entry_count, total_amount)
    """
    entries = BookingEntry.objects.filter(
        tenant=tenant,
        booking_date__gte=period_start,
        booking_date__lte=period_end,
    ).select_related("invoice_record", "invoice_record__customer").order_by(
        "booking_date", "invoice_record__invoice_number", "id",
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")

    # Write header row
    writer.writerow(DATEV_HEADER_FIELDS)

    entry_count = 0
    total_amount = Decimal("0.00")

    for entry in entries:
        amount = entry.amount
        is_negative = amount < 0

        # Build the row — only populate the fields we need, rest empty
        row = [""] * NUM_DATEV_FIELDS

        # Umsatz (absolute value, German decimal format)
        row[0] = _format_amount(amount)

        # Soll/Haben-Kennzeichen: S=Soll(debit), H=Haben(credit)
        # For standard revenue booking: debitor(Soll) → revenue(Haben)
        # Negative (storno): flip
        if is_negative:
            row[1] = "H"
        else:
            row[1] = "S"

        # WKZ Umsatz (currency)
        row[2] = "EUR"

        # Konto (debit account = debitor)
        row[6] = entry.debit_account

        # Gegenkonto (credit account = revenue account)
        row[7] = entry.credit_account

        # BU-Schlüssel (tax key)
        row[8] = entry.tax_key

        # Belegdatum (TTMM)
        row[9] = _format_belegdatum(entry.booking_date)

        # Belegfeld 1 (invoice number)
        invoice_number = ""
        if entry.invoice_record:
            invoice_number = entry.invoice_record.invoice_number
        row[10] = invoice_number

        # Buchungstext
        row[13] = entry.description[:60]  # DATEV limit: 60 chars

        # KOST1 (cost center)
        if entry.cost_center:
            row[36] = entry.cost_center

        # EU-Land u. UStID
        eu_field = _get_eu_ustid_field(entry.invoice_record)
        if eu_field:
            row[39] = eu_field

        # Leistungsdatum (service date = billing period start)
        if entry.invoice_record and entry.invoice_record.period_start:
            row[NUM_DATEV_FIELDS - 2] = _format_belegdatum(entry.invoice_record.period_start)

        writer.writerow(row)
        entry_count += 1
        total_amount += abs(amount)

    return output.getvalue(), entry_count, total_amount


def create_datev_export(
    tenant: Tenant,
    period_start: date,
    period_end: date,
    user=None,
) -> AccountingExport:
    """Generate DATEV CSV and create an AccountingExport record."""
    from django.core.files.base import ContentFile

    csv_content, entry_count, total_amount = generate_datev_csv(
        tenant, period_start, period_end,
    )

    export = AccountingExport(
        tenant=tenant,
        period_start=period_start,
        period_end=period_end,
        export_format=AccountingExport.ExportFormat.DATEV_CSV,
        entry_count=entry_count,
        total_amount=total_amount,
        exported_by=user,
    )

    filename = f"DATEV_Buchungsstapel_{period_start.isoformat()}_{period_end.isoformat()}.csv"
    export.file.save(filename, ContentFile(csv_content.encode("cp1252", errors="replace")))
    export.save()

    return export
