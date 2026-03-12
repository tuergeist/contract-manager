"""Tests for FTE distribution snapshot and department cost center features."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.banking.models import (
    BankAccount,
    BankTransaction,
    CostCenter,
    CostCenterSplitRule,
    Counterparty,
    FteDistributionEntry,
    FteDistributionSnapshot,
    TransactionCostCenterSplit,
)
from apps.contracts.models import Department, DepartmentServiceMapping, UserCostProfile


@pytest.fixture
def cost_centers(tenant):
    cc1 = CostCenter.objects.create(tenant=tenant, code="100", name="Engineering")
    cc2 = CostCenter.objects.create(tenant=tenant, code="200", name="Marketing")
    cc3 = CostCenter.objects.create(tenant=tenant, code="300", name="Sales")
    return cc1, cc2, cc3


@pytest.fixture
def departments(tenant, cost_centers):
    cc1, cc2, cc3 = cost_centers
    d1 = Department.objects.create(tenant=tenant, name="Dev", cost_center=cc1)
    d2 = Department.objects.create(tenant=tenant, name="Marketing", cost_center=cc2)
    d3 = Department.objects.create(tenant=tenant, name="Sales", cost_center=cc3)
    return d1, d2, d3


@pytest.fixture
def bank_account(tenant):
    return BankAccount.objects.create(
        tenant=tenant,
        name="Test Account",
        iban="DE89370400440532013000",
    )


@pytest.fixture
def counterparty(tenant):
    return Counterparty.objects.create(tenant=tenant, name="Payroll Provider")


@pytest.mark.django_db
class TestDepartmentCostCenterFK:
    def test_assign_cost_center(self, tenant, cost_centers):
        cc1, _, _ = cost_centers
        dept = Department.objects.create(tenant=tenant, name="TestDept")
        assert dept.cost_center is None

        dept.cost_center = cc1
        dept.save()
        dept.refresh_from_db()
        assert dept.cost_center == cc1

    def test_clear_cost_center(self, tenant, cost_centers):
        cc1, _, _ = cost_centers
        dept = Department.objects.create(tenant=tenant, name="TestDept", cost_center=cc1)
        dept.cost_center = None
        dept.save()
        dept.refresh_from_db()
        assert dept.cost_center is None

    def test_set_null_on_cost_center_delete(self, tenant, cost_centers):
        cc1, _, _ = cost_centers
        dept = Department.objects.create(tenant=tenant, name="TestDept", cost_center=cc1)
        cc1.delete()
        dept.refresh_from_db()
        assert dept.cost_center is None


@pytest.mark.django_db
class TestSplitRuleMode:
    def test_create_fte_rule_without_allocations(self, tenant, counterparty):
        rule = CostCenterSplitRule.objects.create(
            tenant=tenant,
            counterparty=counterparty,
            mode=CostCenterSplitRule.Mode.FTE_DISTRIBUTION,
        )
        assert rule.mode == "fte_distribution"
        assert rule.allocations.count() == 0

    def test_create_percentage_rule_with_allocations(self, tenant, counterparty, cost_centers):
        cc1, cc2, _ = cost_centers
        from apps.banking.models import CostCenterSplitAllocation

        rule = CostCenterSplitRule.objects.create(
            tenant=tenant,
            counterparty=counterparty,
            mode=CostCenterSplitRule.Mode.PERCENTAGE,
        )
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc1, percentage=Decimal("60"))
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc2, percentage=Decimal("40"))
        assert rule.allocations.count() == 2

    def test_default_mode_is_percentage(self, tenant, counterparty):
        rule = CostCenterSplitRule.objects.create(
            tenant=tenant,
            counterparty=counterparty,
        )
        assert rule.mode == "percentage"


@pytest.mark.django_db
class TestFteSnapshot:
    def test_capture_snapshot(self, tenant, departments):
        d1, d2, d3 = departments

        # Create UserCostProfiles for static fallback
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u2", external_user_name="User 2",
            fte_percentage=50, monthly_income=Decimal("3000"), default_department=d2,
        )

        from apps.banking.services.fte_snapshot import capture_snapshot

        snapshot = capture_snapshot(tenant, "2026-02")
        assert snapshot.year_month == "2026-02"
        assert snapshot.entries.count() == 3  # 3 depts with cost centers

        # Check percentages add up
        total_pct = sum(e.fte_percentage for e in snapshot.entries.all())
        assert abs(total_pct - Decimal("100")) < Decimal("0.01")

    def test_reject_duplicate_snapshot(self, tenant, departments):
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=departments[0],
        )

        from apps.banking.services.fte_snapshot import capture_snapshot

        capture_snapshot(tenant, "2026-02")
        with pytest.raises(ValueError, match="already exists"):
            capture_snapshot(tenant, "2026-02")

    def test_reject_future_month(self, tenant, departments):
        from apps.banking.services.fte_snapshot import capture_snapshot

        with pytest.raises(ValueError, match="future month"):
            capture_snapshot(tenant, "2099-12")

    def test_snapshot_uses_static_fallback(self, tenant, departments):
        """When no Clockodo data, uses UserCostProfile FTE% as weights."""
        d1, d2, _ = departments
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u2", external_user_name="User 2",
            fte_percentage=100, monthly_income=Decimal("4000"), default_department=d2,
        )
        # d3 (Sales) has no users, gets 0 hours

        from apps.banking.services.fte_snapshot import capture_snapshot

        snapshot = capture_snapshot(tenant, "2026-01")
        entries = {e.department_name: e for e in snapshot.entries.all()}
        # With FTE=100 each, Dev and Marketing get 50% each
        assert entries["Dev"].fte_percentage == Decimal("50.0000")
        assert entries["Marketing"].fte_percentage == Decimal("50.0000")

    def test_reapply_splits_on_capture(
        self, tenant, departments, counterparty, bank_account, cost_centers
    ):
        """When snapshot is captured, FTE-rule-based splits are re-applied."""
        d1, d2, _ = departments
        cc1, cc2, _ = cost_centers

        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u2", external_user_name="User 2",
            fte_percentage=100, monthly_income=Decimal("4000"), default_department=d2,
        )

        rule = CostCenterSplitRule.objects.create(
            tenant=tenant,
            counterparty=counterparty,
            mode=CostCenterSplitRule.Mode.FTE_DISTRIBUTION,
        )

        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            amount=Decimal("-1000"),
            entry_date=date(2026, 1, 15),
            booking_text="Payroll",
            counterparty=counterparty,
        )

        # Create preliminary auto splits
        TransactionCostCenterSplit.objects.create(
            transaction=txn, cost_center=cc1, amount=Decimal("600"),
            is_manual=False, rule=rule,
        )
        TransactionCostCenterSplit.objects.create(
            transaction=txn, cost_center=cc2, amount=Decimal("400"),
            is_manual=False, rule=rule,
        )

        from apps.banking.services.fte_snapshot import capture_snapshot

        snapshot = capture_snapshot(tenant, "2026-01")

        # Splits should be re-created from snapshot
        splits = TransactionCostCenterSplit.objects.filter(transaction=txn).order_by("-amount")
        assert splits.count() >= 2
        total = sum(s.amount for s in splits)
        assert total == Decimal("1000")

    def test_manual_splits_preserved(
        self, tenant, departments, counterparty, bank_account, cost_centers
    ):
        """Manual splits are not touched during snapshot re-application."""
        d1, _, _ = departments
        cc1, _, _ = cost_centers

        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )

        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            amount=Decimal("-500"),
            entry_date=date(2026, 1, 10),
            booking_text="Manual",
            counterparty=counterparty,
        )

        # Manual split
        TransactionCostCenterSplit.objects.create(
            transaction=txn, cost_center=cc1, amount=Decimal("500"),
            is_manual=True,
        )

        from apps.banking.services.fte_snapshot import capture_snapshot

        capture_snapshot(tenant, "2026-01")

        # Manual split should still be there
        splits = TransactionCostCenterSplit.objects.filter(transaction=txn)
        assert splits.count() == 1
        assert splits.first().is_manual is True


@pytest.mark.django_db
class TestFteBasedSplitApplication:
    def test_apply_fte_rule_with_snapshot(
        self, tenant, departments, counterparty, bank_account, cost_centers
    ):
        d1, d2, _ = departments

        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u2", external_user_name="User 2",
            fte_percentage=100, monthly_income=Decimal("4000"), default_department=d2,
        )

        from apps.banking.services.fte_snapshot import capture_snapshot

        snapshot = capture_snapshot(tenant, "2026-02")

        rule = CostCenterSplitRule.objects.create(
            tenant=tenant,
            counterparty=counterparty,
            mode=CostCenterSplitRule.Mode.FTE_DISTRIBUTION,
        )

        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            amount=Decimal("-2000"),
            entry_date=date(2026, 2, 20),
            booking_text="Payroll",
            counterparty=counterparty,
        )

        from apps.banking.services.cost_center_split import CostCenterSplitService

        splits = CostCenterSplitService.apply_rule(txn)
        assert len(splits) >= 2
        total = sum(s.amount for s in splits)
        assert total == Decimal("2000")

    def test_apply_fte_rule_live_fallback(
        self, tenant, departments, counterparty, bank_account, cost_centers
    ):
        """Without a snapshot, falls back to live computation."""
        d1, _, _ = departments

        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )

        rule = CostCenterSplitRule.objects.create(
            tenant=tenant,
            counterparty=counterparty,
            mode=CostCenterSplitRule.Mode.FTE_DISTRIBUTION,
        )

        txn = BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            amount=Decimal("-1000"),
            entry_date=date(2026, 3, 15),
            booking_text="Payroll",
            counterparty=counterparty,
        )

        from apps.banking.services.cost_center_split import CostCenterSplitService

        splits = CostCenterSplitService.apply_rule(txn)
        # At least one split should be created (from static FTE fallback)
        assert len(splits) >= 1


@pytest.mark.django_db
class TestCeleryTask:
    def test_capture_on_correct_day(self, tenant, departments):
        d1, _, _ = departments
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )

        # Set capture day to 7
        tenant.settings = {"fte_snapshot_capture_day": 7}
        tenant.save()

        from apps.banking.tasks import capture_monthly_fte_snapshots

        with patch("apps.banking.tasks.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 7)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            capture_monthly_fte_snapshots()

        assert FteDistributionSnapshot.objects.filter(tenant=tenant, year_month="2026-02").exists()

    def test_skip_if_snapshot_exists(self, tenant, departments):
        d1, _, _ = departments
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )

        from apps.banking.services.fte_snapshot import capture_snapshot

        capture_snapshot(tenant, "2026-02")

        tenant.settings = {"fte_snapshot_capture_day": 7}
        tenant.save()

        from apps.banking.tasks import capture_monthly_fte_snapshots

        # Should not raise even though snapshot exists
        with patch("apps.banking.tasks.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 7)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            capture_monthly_fte_snapshots()

        # Still only one snapshot
        assert FteDistributionSnapshot.objects.filter(tenant=tenant, year_month="2026-02").count() == 1


@pytest.mark.django_db
class TestTenantIsolation:
    def test_snapshot_tenant_isolation(self, tenant, departments):
        from apps.tenants.models import Tenant

        d1, _, _ = departments
        UserCostProfile.objects.create(
            tenant=tenant, external_user_id="u1", external_user_name="User 1",
            fte_percentage=100, monthly_income=Decimal("5000"), default_department=d1,
        )

        other_tenant = Tenant.objects.create(name="Other Tenant")

        from apps.banking.services.fte_snapshot import capture_snapshot

        capture_snapshot(tenant, "2026-02")

        assert FteDistributionSnapshot.objects.filter(tenant=tenant).count() == 1
        assert FteDistributionSnapshot.objects.filter(tenant=other_tenant).count() == 0
