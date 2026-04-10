"""Tests for absence report feature."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.core.files.base import ContentFile

from apps.contracts.models import AbsenceReport, AbsenceReportEntry, Contract
from apps.contracts.services.absence_report import AbsenceReportService, ABSENCE_LABELS
from apps.contracts.services.time_tracking import TimeTrackingProvider
from apps.contracts.services.clockodo_provider import ClockodoProvider
from apps.customers.models import Customer


# ---- Provider Normalization ----

class TestAbsenceTypeNormalization:
    def test_base_provider_returns_other(self):
        """ABC default normalize_absence_type returns 'other'."""
        class DummyProvider(TimeTrackingProvider):
            def test_connection(self): return {"success": True}
            def get_projects(self): return []
            def get_time_summary(self, *a, **kw): return None

        provider = DummyProvider()
        assert provider.normalize_absence_type(0) == "other"
        assert provider.normalize_absence_type(99) == "other"

    def test_clockodo_sick(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(1) == "sick"

    def test_clockodo_sick_child(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(6) == "sick_child"

    def test_clockodo_sick_certificate(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(3) == "sick_certificate"
        assert provider.normalize_absence_type(4) == "sick_certificate"

    def test_clockodo_vacation(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(0) == "vacation"

    def test_clockodo_special_leave(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(5) == "special_leave"

    def test_clockodo_education(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(8) == "education"

    def test_clockodo_overtime_reduction(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(7) == "overtime_reduction"

    def test_clockodo_home_office(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(9) == "other"

    def test_clockodo_unknown_type(self):
        provider = ClockodoProvider({"api_user": "x", "api_key": "y"})
        assert provider.normalize_absence_type(999) == "other"


# ---- Model ----

class TestAbsenceReportModel:
    def test_create(self, db, tenant):
        report = AbsenceReport.objects.create(
            tenant=tenant,
            year=2026,
            month=2,
        )
        assert str(report) == "Absence Report 2026-02 (Draft)"
        assert report.status == AbsenceReport.Status.DRAFT

    def test_unique_constraint(self, db, tenant):
        AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)
        with pytest.raises(Exception):
            AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)

    def test_entry_creation(self, db, tenant):
        report = AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)
        entry = AbsenceReportEntry.objects.create(
            tenant=tenant,
            report=report,
            user_name="Alice",
            external_user_id="123",
            absence_type="sick",
            date_from=date(2026, 2, 3),
            date_to=date(2026, 2, 5),
            days_count=Decimal("3.00"),
            raw_data={"type": 1, "status": 1},
        )
        assert str(entry) == "Alice: Sick (2026-02-03 - 2026-02-05)"
        assert report.entries.count() == 1


# ---- Service ----

def _make_mock_provider(absences=None, users=None):
    """Create a mock provider with given absences and users."""
    provider = MagicMock()
    provider.get_absences.return_value = absences or []
    provider.get_users.return_value = users or []
    # Use real Clockodo mapping for normalize_absence_type
    clockodo = ClockodoProvider({"api_user": "x", "api_key": "y"})
    provider.normalize_absence_type.side_effect = clockodo.normalize_absence_type
    return provider


class TestAbsenceReportService:
    def test_generate_report_basic(self, db, tenant):
        """Generate a report with one sick absence."""
        provider = _make_mock_provider(
            absences=[{
                "user_id": "1",
                "date_since": "2026-02-03",
                "date_until": "2026-02-05",
                "count_days": 3,
                "type": 1,  # sick
                "status": 1,  # approved
            }],
            users=[{"id": "1", "name": "Alice"}],
        )

        service = AbsenceReportService(tenant)
        with patch.object(service, '_get_provider', return_value=provider):
            report = service.generate_report(2026, 2)

        assert report.year == 2026
        assert report.month == 2
        assert report.status == AbsenceReport.Status.DRAFT
        assert report.entries.count() == 1
        entry = report.entries.first()
        assert entry.user_name == "Alice"
        assert entry.absence_type == "sick"
        assert entry.days_count == Decimal("3.00")

    def test_generate_excludes_declined(self, db, tenant):
        """Declined absences are excluded."""
        provider = _make_mock_provider(
            absences=[{
                "user_id": "1",
                "date_since": "2026-02-03",
                "date_until": "2026-02-05",
                "count_days": 3,
                "type": 1,
                "status": 2,  # declined
            }],
            users=[{"id": "1", "name": "Alice"}],
        )

        service = AbsenceReportService(tenant)
        with patch.object(service, '_get_provider', return_value=provider):
            report = service.generate_report(2026, 2)

        assert report.entries.count() == 0

    def test_generate_excludes_home_office(self, db, tenant):
        """Home office (type=9) is excluded."""
        provider = _make_mock_provider(
            absences=[{
                "user_id": "1",
                "date_since": "2026-02-03",
                "date_until": "2026-02-05",
                "count_days": 3,
                "type": 9,  # home office
                "status": 1,
            }],
            users=[{"id": "1", "name": "Alice"}],
        )

        service = AbsenceReportService(tenant)
        with patch.object(service, '_get_provider', return_value=provider):
            report = service.generate_report(2026, 2)

        assert report.entries.count() == 0

    def test_generate_prorates_cross_month(self, db, tenant):
        """Absence spanning Jan 28 - Feb 3 is pro-rated for February."""
        provider = _make_mock_provider(
            absences=[{
                "user_id": "1",
                "date_since": "2026-01-28",
                "date_until": "2026-02-03",
                "count_days": 5,  # 5 working days across 7 calendar days
                "type": 1,
                "status": 1,
            }],
            users=[{"id": "1", "name": "Alice"}],
        )

        service = AbsenceReportService(tenant)
        with patch.object(service, '_get_provider', return_value=provider):
            report = service.generate_report(2026, 2)

        assert report.entries.count() == 1
        entry = report.entries.first()
        # 7 calendar days total, 3 in Feb (Feb 1-3), pro-rated: 5 * 3/7 ≈ 2.14
        assert entry.days_count == Decimal("2.14")
        assert entry.date_from == date(2026, 2, 1)
        assert entry.date_to == date(2026, 2, 3)

    def test_cannot_regenerate_finalized_without_permission(self, db, tenant):
        """Cannot regenerate a finalized report without allow_reset_finalized."""
        AbsenceReport.objects.create(
            tenant=tenant, year=2026, month=2,
            status=AbsenceReport.Status.FINALIZED,
        )

        service = AbsenceReportService(tenant)
        with pytest.raises(ValueError, match="already finalized"):
            service.generate_report(2026, 2)

    def test_regenerate_finalized_with_permission_resets_status(self, db, tenant):
        """Regenerating a finalized report with allow_reset_finalized resets to draft."""
        report = AbsenceReport.objects.create(
            tenant=tenant, year=2026, month=2,
            status=AbsenceReport.Status.FINALIZED,
        )

        service = AbsenceReportService(tenant)
        # Will reset to draft, then fail on provider — but status should be reset
        try:
            service.generate_report(2026, 2, allow_reset_finalized=True)
        except ValueError as e:
            if "provider" in str(e):
                pass  # Expected — no provider in test
            else:
                raise

        report.refresh_from_db()
        assert report.status == AbsenceReport.Status.DRAFT

    def test_regenerate_draft_replaces_entries(self, db, tenant):
        """Regenerating a draft replaces old entries."""
        report = AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)
        AbsenceReportEntry.objects.create(
            tenant=tenant, report=report, user_name="Old",
            external_user_id="99", absence_type="sick",
            date_from=date(2026, 2, 1), date_to=date(2026, 2, 1),
            days_count=Decimal("1"),
        )

        provider = _make_mock_provider(
            absences=[{
                "user_id": "1",
                "date_since": "2026-02-10",
                "date_until": "2026-02-12",
                "count_days": 3,
                "type": 1,
                "status": 1,
            }],
            users=[{"id": "1", "name": "Bob"}],
        )

        service = AbsenceReportService(tenant)
        with patch.object(service, '_get_provider', return_value=provider):
            updated = service.generate_report(2026, 2)

        assert updated.id == report.id
        assert updated.entries.count() == 1
        assert updated.entries.first().user_name == "Bob"

    def test_render_html_german(self, db, tenant):
        """German HTML rendering contains expected labels."""
        report = AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)
        AbsenceReportEntry.objects.create(
            tenant=tenant, report=report, user_name="Alice",
            external_user_id="1", absence_type="sick",
            date_from=date(2026, 2, 3), date_to=date(2026, 2, 5),
            days_count=Decimal("3.00"),
        )

        service = AbsenceReportService(tenant)
        html = service.render_html(report, language="de")
        assert "Fehlzeiten-Report" in html
        assert "Februar" in html
        assert "Alice" in html
        assert "Krank" in html

    def test_render_html_english(self, db, tenant):
        """English HTML rendering contains expected labels."""
        report = AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)
        AbsenceReportEntry.objects.create(
            tenant=tenant, report=report, user_name="Alice",
            external_user_id="1", absence_type="sick_child",
            date_from=date(2026, 2, 10), date_to=date(2026, 2, 11),
            days_count=Decimal("2.00"),
        )

        service = AbsenceReportService(tenant)
        html = service.render_html(report, language="en")
        assert "Absence Report" in html
        assert "February" in html
        assert "Alice" in html
        assert "Sick (child)" in html

    def test_finalize_report(self, db, tenant, user):
        """Finalizing locks the report."""
        report = AbsenceReport.objects.create(tenant=tenant, year=2026, month=3)
        AbsenceReportEntry.objects.create(
            tenant=tenant, report=report, user_name="Alice",
            external_user_id="1", absence_type="vacation",
            date_from=date(2026, 3, 1), date_to=date(2026, 3, 5),
            days_count=Decimal("5.00"),
        )

        service = AbsenceReportService(tenant)
        with patch.object(service, 'generate_pdf', return_value=b'%PDF-fake'):
            finalized = service.finalize_report(report.id, user)

        assert finalized.status == AbsenceReport.Status.FINALIZED
        assert finalized.finalized_at is not None
        assert finalized.finalized_by == user
        assert finalized.pdf_file

    def test_cannot_finalize_twice(self, db, tenant, user):
        """Cannot finalize an already finalized report."""
        report = AbsenceReport.objects.create(
            tenant=tenant, year=2026, month=3,
            status=AbsenceReport.Status.FINALIZED,
        )

        service = AbsenceReportService(tenant)
        with pytest.raises(ValueError, match="already finalized"):
            service.finalize_report(report.id, user)

    @patch("apps.core.m365.send_mail")
    def test_send_report(self, mock_send_mail, db, tenant):
        """Send a finalized report."""
        mock_send_mail.return_value = "msg-123"
        report = AbsenceReport.objects.create(
            tenant=tenant, year=2026, month=2,
            status=AbsenceReport.Status.FINALIZED,
        )
        report.pdf_file.save("test.pdf", ContentFile(b"%PDF-fake"), save=True)

        service = AbsenceReportService(tenant)
        result = service.send_report(report.id, ["hr@example.com"])
        assert result is True
        mock_send_mail.assert_called_once()

    def test_cannot_send_draft(self, db, tenant):
        """Cannot send a draft report."""
        report = AbsenceReport.objects.create(tenant=tenant, year=2026, month=2)

        service = AbsenceReportService(tenant)
        with pytest.raises(ValueError, match="finalized"):
            service.send_report(report.id, ["hr@example.com"])
