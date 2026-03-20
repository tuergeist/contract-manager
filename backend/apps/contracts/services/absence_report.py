"""Absence report service — generation, PDF rendering, finalization, and email sending."""
import logging
from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.contracts.models import AbsenceReport, AbsenceReportEntry

logger = logging.getLogger(__name__)

ABSENCE_LABELS = {
    "de": {
        "title": "Fehlzeiten-Report",
        "employee": "Mitarbeiter",
        "absence_type": "Art",
        "date_from": "Von",
        "date_to": "Bis",
        "days": "Tage",
        "total_days": "Gesamt Fehltage",
        "month_label": "Monat",
        "generated_at": "Erstellt am",
        "status_draft": "Entwurf",
        "status_finalized": "Festgeschrieben",
        # Absence type labels
        "type_sick": "Krank",
        "type_sick_child": "Krank (Kind)",
        "type_sick_certificate": "Krank (AU)",
        "type_vacation": "Urlaub",
        "type_special_leave": "Sonderurlaub",
        "type_education": "Fortbildung",
        "type_overtime_reduction": "Überstundenabbau",
        "type_other": "Sonstige",
    },
    "en": {
        "title": "Absence Report",
        "employee": "Employee",
        "absence_type": "Type",
        "date_from": "From",
        "date_to": "To",
        "days": "Days",
        "total_days": "Total Absence Days",
        "month_label": "Month",
        "generated_at": "Generated",
        "status_draft": "Draft",
        "status_finalized": "Finalized",
        # Absence type labels
        "type_sick": "Sick",
        "type_sick_child": "Sick (child)",
        "type_sick_certificate": "Sick (certificate)",
        "type_vacation": "Vacation",
        "type_special_leave": "Special leave",
        "type_education": "Education",
        "type_overtime_reduction": "Overtime reduction",
        "type_other": "Other",
    },
}

MONTH_NAMES = {
    "de": [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ],
    "en": [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
}


class AbsenceReportService:
    """Service for generating, rendering, finalizing, and sending absence reports."""

    def __init__(self, tenant):
        self.tenant = tenant

    def _get_provider(self):
        from apps.contracts.services.time_tracking import get_provider
        return get_provider(self.tenant)

    def _filter_and_prorate_absences(
        self, absences: list[dict], year: int, month: int, provider
    ) -> list[dict]:
        """Filter absences to the target month, pro-rate cross-month absences."""
        from calendar import monthrange

        last_day = monthrange(year, month)[1]
        period_start = date(year, month, 1)
        period_end = date(year, month, last_day)

        entries = []
        for ab in absences:
            # Exclude declined/cancelled
            if ab.get("status") in (2, 3, 4):
                continue
            # Exclude home office (Clockodo type=9)
            if ab.get("type") == 9:
                continue

            ab_start_str = ab.get("date_since", "")[:10]
            ab_end_str = ab.get("date_until", "")[:10]
            if not ab_start_str or not ab_end_str:
                continue

            ab_start = date.fromisoformat(ab_start_str)
            ab_end = date.fromisoformat(ab_end_str)

            # Check overlap
            if ab_end < period_start or ab_start > period_end:
                continue

            total_days = ab.get("count_days", 0) or 0
            if total_days <= 0:
                continue

            # Pro-rate if absence spans month boundaries
            if ab_start >= period_start and ab_end <= period_end:
                prorated_days = total_days
            else:
                absence_span = (ab_end - ab_start).days + 1
                overlap_start = max(ab_start, period_start)
                overlap_end = min(ab_end, period_end)
                overlap_days = (overlap_end - overlap_start).days + 1
                prorated_days = total_days * (overlap_days / absence_span) if absence_span > 0 else 0

            if prorated_days <= 0:
                continue

            entries.append({
                "user_id": ab["user_id"],
                "absence_type": provider.normalize_absence_type(ab.get("type", 0)),
                "date_from": max(ab_start, period_start),
                "date_to": min(ab_end, period_end),
                "days_count": Decimal(str(round(prorated_days, 2))),
                "raw_data": ab,
            })

        return entries

    def _get_user_names(self, provider) -> dict[str, str]:
        """Build user_id -> user_name mapping from provider."""
        try:
            users = provider.get_users()
            return {str(u["id"]): u.get("name", f"User {u['id']}") for u in users}
        except Exception:
            return {}

    def generate_report(self, year: int, month: int) -> AbsenceReport:
        """Generate or regenerate a draft absence report for the given month."""
        # Check for existing finalized report
        existing = AbsenceReport.objects.filter(
            tenant=self.tenant, year=year, month=month,
        ).first()

        if existing and existing.status == AbsenceReport.Status.FINALIZED:
            raise ValueError(f"Report for {year}-{month:02d} is already finalized")

        provider = self._get_provider()
        if not provider:
            raise ValueError("No time tracking provider configured")

        # Fetch absences and user names
        raw_absences = provider.get_absences(year)
        user_names = self._get_user_names(provider)
        entries = self._filter_and_prorate_absences(raw_absences, year, month, provider)

        # Create or update report
        if existing:
            report = existing
            report.entries.all().delete()
        else:
            report = AbsenceReport.objects.create(
                tenant=self.tenant, year=year, month=month,
            )

        # Create entries
        for entry_data in entries:
            AbsenceReportEntry.objects.create(
                tenant=self.tenant,
                report=report,
                user_name=user_names.get(entry_data["user_id"], f"User {entry_data['user_id']}"),
                external_user_id=entry_data["user_id"],
                absence_type=entry_data["absence_type"],
                date_from=entry_data["date_from"],
                date_to=entry_data["date_to"],
                days_count=entry_data["days_count"],
                raw_data=entry_data["raw_data"],
            )

        return report

    def _get_template_context(self) -> dict:
        """Load template settings and legal data (reuses invoice template settings)."""
        from apps.invoices.models import CompanyLegalData, InvoiceTemplate

        try:
            legal_data_obj = self.tenant.legal_data
            company = legal_data_obj.to_snapshot()
        except CompanyLegalData.DoesNotExist:
            company = {
                "company_name": self.tenant.name,
                "street": "", "zip_code": "", "city": "", "country": "",
            }

        logo_url = ""
        accent_color = "#2563eb"
        try:
            template = InvoiceTemplate.objects.get(tenant=self.tenant)
            accent_color = template.accent_color or "#2563eb"
            if template.logo and template.logo.name:
                import base64
                import mimetypes
                try:
                    mime_type = mimetypes.guess_type(template.logo.name)[0] or "image/png"
                    logo_data = template.logo.read()
                    logo_url = f"data:{mime_type};base64,{base64.b64encode(logo_data).decode()}"
                except Exception:
                    logo_url = ""
        except InvoiceTemplate.DoesNotExist:
            pass

        return {"company": company, "logo_url": logo_url, "accent_color": accent_color}

    def _build_grouped_entries(self, report: AbsenceReport, language: str) -> list[dict]:
        """Group entries by employee for rendering."""
        labels = ABSENCE_LABELS.get(language, ABSENCE_LABELS["de"])
        entries = report.entries.all().order_by("user_name", "date_from")

        grouped: dict[str, list] = {}
        for entry in entries:
            if entry.user_name not in grouped:
                grouped[entry.user_name] = []
            type_label = labels.get(f"type_{entry.absence_type}", entry.get_absence_type_display())
            grouped[entry.user_name].append({
                "type_label": type_label,
                "date_from": entry.date_from,
                "date_to": entry.date_to,
                "days_count": entry.days_count,
            })

        result = []
        for user_name, user_entries in grouped.items():
            total = sum(e["days_count"] for e in user_entries)
            result.append({
                "user_name": user_name,
                "entries": user_entries,
                "total_days": total,
            })
        return result

    def render_html(self, report: AbsenceReport, language: str = "de") -> str:
        """Render the absence report as HTML."""
        labels = ABSENCE_LABELS.get(language, ABSENCE_LABELS["de"])
        template_ctx = self._get_template_context()
        grouped = self._build_grouped_entries(report, language)
        month_name = MONTH_NAMES.get(language, MONTH_NAMES["de"])[report.month]
        total_days = sum(g["total_days"] for g in grouped)

        ctx = {
            "labels": labels,
            "language": language,
            "report": report,
            "month_name": month_name,
            "grouped_entries": grouped,
            "total_days": total_days,
            "generated_date": date.today(),
            **template_ctx,
        }
        return render_to_string("contracts/absence_report.html", ctx)

    def generate_pdf(self, report: AbsenceReport, language: str = "de") -> bytes:
        """Generate the absence report PDF."""
        from weasyprint import HTML

        html = self.render_html(report, language)
        return HTML(string=html).render().write_pdf()

    def finalize_report(self, report_id: int, user) -> AbsenceReport:
        """Finalize a draft report: lock it and generate PDF."""
        report = AbsenceReport.objects.get(id=report_id, tenant=self.tenant)

        if report.status == AbsenceReport.Status.FINALIZED:
            raise ValueError("Report is already finalized")

        language = "de"  # Default to German
        pdf_bytes = self.generate_pdf(report, language)

        report.status = AbsenceReport.Status.FINALIZED
        report.finalized_at = timezone.now()
        report.finalized_by = user
        report.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])

        filename = f"absence-report-{report.year}-{report.month:02d}.pdf"
        report.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        return report

    def send_report(self, report_id: int, recipients: list[str]) -> bool:
        """Send a finalized absence report via email."""
        from apps.core.m365 import M365Error, send_mail

        report = AbsenceReport.objects.get(id=report_id, tenant=self.tenant)

        if report.status != AbsenceReport.Status.FINALIZED:
            raise ValueError("Can only send finalized reports")

        if not report.pdf_file:
            raise ValueError("Report has no PDF file")

        if not recipients:
            raise ValueError("No recipients specified")

        language = "de"
        labels = ABSENCE_LABELS.get(language, ABSENCE_LABELS["de"])
        month_name = MONTH_NAMES.get(language, MONTH_NAMES["de"])[report.month]

        subject = f"{labels['title']} {month_name} {report.year}"
        body_html = f"<p>{labels['title']} für {month_name} {report.year} im Anhang.</p>"

        pdf_bytes = report.pdf_file.read()
        attachments = [{
            "name": f"absence-report-{report.year}-{report.month:02d}.pdf",
            "content_type": "application/pdf",
            "content_bytes": pdf_bytes,
        }]

        try:
            send_mail(
                self.tenant,
                to=recipients,
                subject=subject,
                body_html=body_html,
                attachments=attachments,
            )
            logger.info("Absence report %s sent to %s", report.id, recipients)
            return True
        except M365Error as e:
            logger.error("Failed to send absence report %s: %s", report.id, e)
            return False
