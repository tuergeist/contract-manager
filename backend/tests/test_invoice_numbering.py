"""Tests for invoice numbering service."""
import pytest
from datetime import date

from apps.invoices.models import InvoiceNumberScheme
from apps.invoices.numbering import InvoiceNumberService


@pytest.fixture
def numbering_service(tenant):
    return InvoiceNumberService(tenant)


class TestInvoiceNumberServiceFormatting:
    """Test pattern placeholder resolution."""

    def test_yyyy_placeholder(self, numbering_service):
        result = InvoiceNumberService._format_number(
            "RE-{YYYY}-{NNNN}", date(2026, 3, 15), 1
        )
        assert result == "RE-2026-0001"

    def test_yy_placeholder(self, numbering_service):
        result = InvoiceNumberService._format_number(
            "INV/{YY}/{MM}/{NNN}", date(2026, 2, 1), 42
        )
        assert result == "INV/26/02/042"

    def test_mm_placeholder(self, numbering_service):
        result = InvoiceNumberService._format_number(
            "{YYYY}{MM}{NNNNN}", date(2026, 11, 1), 7
        )
        assert result == "202611" + "00007"

    def test_counter_padding_nnn(self, numbering_service):
        result = InvoiceNumberService._format_number("{NNN}", date(2026, 1, 1), 5)
        assert result == "005"

    def test_counter_padding_nnnn(self, numbering_service):
        result = InvoiceNumberService._format_number("{NNNN}", date(2026, 1, 1), 123)
        assert result == "0123"

    def test_counter_padding_nnnnn(self, numbering_service):
        result = InvoiceNumberService._format_number("{NNNNN}", date(2026, 1, 1), 99999)
        assert result == "99999"

    def test_static_text_preserved(self, numbering_service):
        result = InvoiceNumberService._format_number(
            "RE-{YYYY}-{NNNN}", date(2026, 1, 1), 1
        )
        assert result.startswith("RE-")


class TestInvoiceNumberServiceSequential:
    """Test sequential number generation."""

    def test_first_number(self, db, numbering_service):
        number = numbering_service.get_next_number(date(2026, 1, 15))
        assert number == "2026-0001"

    def test_sequential_numbers(self, db, numbering_service):
        n1 = numbering_service.get_next_number(date(2026, 1, 15))
        n2 = numbering_service.get_next_number(date(2026, 1, 16))
        n3 = numbering_service.get_next_number(date(2026, 1, 17))
        assert n1 == "2026-0001"
        assert n2 == "2026-0002"
        assert n3 == "2026-0003"

    def test_custom_pattern(self, db, tenant, numbering_service):
        InvoiceNumberScheme.objects.create(
            tenant=tenant,
            pattern="RE-{YYYY}-{NNNN}",
            next_counter=100,
            reset_period=InvoiceNumberScheme.ResetPeriod.NEVER,
        )
        # Re-create service to pick up the new scheme
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 5, 1))
        assert number == "RE-2026-0100"


class TestInvoiceNumberServiceReset:
    """Test counter reset logic."""

    def test_yearly_reset(self, db, tenant):
        scheme = InvoiceNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
            next_counter=50,
            reset_period=InvoiceNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=2025,
            last_reset_month=12,
        )
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 1, 1))
        # Counter should have reset to 1 for new year
        assert number == "2026-0001"

    def test_no_reset_same_year(self, db, tenant):
        scheme = InvoiceNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
            next_counter=50,
            reset_period=InvoiceNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=2026,
            last_reset_month=1,
        )
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 3, 1))
        assert number == "2026-0050"

    def test_monthly_reset(self, db, tenant):
        scheme = InvoiceNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}/{MM}-{NNN}",
            next_counter=25,
            reset_period=InvoiceNumberScheme.ResetPeriod.MONTHLY,
            last_reset_year=2026,
            last_reset_month=1,
        )
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 2, 1))
        assert number == "2026/02-001"

    def test_never_reset(self, db, tenant):
        scheme = InvoiceNumberScheme.objects.create(
            tenant=tenant,
            pattern="{NNNN}",
            next_counter=999,
            reset_period=InvoiceNumberScheme.ResetPeriod.NEVER,
            last_reset_year=2020,
            last_reset_month=1,
        )
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 12, 1))
        assert number == "0999"

    def test_first_use_no_reset(self, db, tenant):
        """First use (no last_reset_year) should not trigger reset."""
        scheme = InvoiceNumberScheme.objects.create(
            tenant=tenant,
            pattern="{YYYY}-{NNNN}",
            next_counter=5,
            reset_period=InvoiceNumberScheme.ResetPeriod.YEARLY,
            last_reset_year=None,
            last_reset_month=None,
        )
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 1, 1))
        assert number == "2026-0005"


class TestInvoiceNumberServiceDefaultScheme:
    """Test default scheme creation."""

    def test_creates_default_scheme(self, db, tenant):
        assert not InvoiceNumberScheme.objects.filter(tenant=tenant).exists()
        service = InvoiceNumberService(tenant)
        number = service.get_next_number(date(2026, 1, 1))
        assert number == "2026-0001"
        scheme = InvoiceNumberScheme.objects.get(tenant=tenant)
        assert scheme.pattern == "{YYYY}-{NNNN}"
        assert scheme.reset_period == InvoiceNumberScheme.ResetPeriod.YEARLY

    def test_preview_without_incrementing(self, db, tenant):
        service = InvoiceNumberService(tenant)
        preview = service.preview_next_number(date(2026, 3, 15))
        assert preview == "2026-0001"
        # Counter should NOT have incremented
        scheme = InvoiceNumberScheme.objects.get(tenant=tenant)
        assert scheme.next_counter == 1


class TestPatternValidation:
    """Test pattern validation."""

    def test_valid_pattern(self):
        errors = InvoiceNumberService.validate_pattern("RE-{YYYY}-{NNNN}")
        assert errors == []

    def test_missing_counter(self):
        errors = InvoiceNumberService.validate_pattern("RE-{YYYY}-{MM}")
        assert len(errors) == 1
        assert "counter placeholder" in errors[0]

    def test_empty_pattern(self):
        errors = InvoiceNumberService.validate_pattern("")
        assert len(errors) == 1

    def test_unknown_placeholder(self):
        errors = InvoiceNumberService.validate_pattern("{INVALID}-{NNNN}")
        assert any("Unknown placeholder" in e for e in errors)
