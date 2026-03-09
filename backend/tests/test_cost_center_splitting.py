"""Tests for cost center splitting: rules CRUD, auto-apply, manual split, report, tenant isolation."""
import pytest
from decimal import Decimal
from unittest.mock import Mock

from apps.banking.models import (
    BankAccount, BankTransaction, CostCenter, Counterparty,
    CostCenterSplitRule, CostCenterSplitAllocation, TransactionCostCenterSplit,
)
from apps.banking.services.cost_center_split import CostCenterSplitService
from apps.core.context import Context
from apps.tenants.models import Role, Tenant, User
from config.schema import schema


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def account(db, tenant):
    return BankAccount.objects.create(
        tenant=tenant, name="Main Account", bank_code="85090000",
        account_number="2721891006", iban="DE12850900002721891006", bic="GENODEF1DRS",
    )


@pytest.fixture
def counterparty(db, tenant):
    return Counterparty.objects.create(tenant=tenant, name="Acme Corp", iban="DE89370400440532013000")


@pytest.fixture
def counterparty2(db, tenant):
    return Counterparty.objects.create(tenant=tenant, name="Beta Inc", iban="DE00000000000000000001")


@pytest.fixture
def cc_marketing(db, tenant):
    return CostCenter.objects.create(tenant=tenant, code="100", name="Marketing")


@pytest.fixture
def cc_engineering(db, tenant):
    return CostCenter.objects.create(tenant=tenant, code="200", name="Engineering")


@pytest.fixture
def cc_admin(db, tenant):
    return CostCenter.objects.create(tenant=tenant, code="300", name="Admin")


@pytest.fixture
def transaction(db, tenant, account, counterparty):
    return BankTransaction.objects.create(
        tenant=tenant, account=account, entry_date="2025-01-15",
        amount=Decimal("-1000.00"), currency="EUR", counterparty=counterparty,
        booking_text="Office rent payment", import_hash="hash1",
    )


@pytest.fixture
def viewer_user(db, tenant):
    u = User.objects.create_user(email="viewer@split.test", password="testpass123", tenant=tenant)
    u.roles.add(Role.objects.get(tenant=tenant, name="Viewer"))
    return u


@pytest.fixture
def manager_user(db, tenant):
    u = User.objects.create_user(email="manager@split.test", password="testpass123", tenant=tenant)
    u.roles.add(Role.objects.get(tenant=tenant, name="Manager"))
    return u


# ---- GraphQL Queries/Mutations ----

CREATE_RULE = """
mutation($input: CreateSplitRuleInput!) {
  createCostCenterSplitRule(input: $input) {
    success error
    rule { id counterparty { id name } bookingTextPattern priority isActive
      allocations { id costCenter { id code } percentage fixedAmount } }
  }
}
"""

UPDATE_RULE = """
mutation($input: UpdateSplitRuleInput!) {
  updateCostCenterSplitRule(input: $input) {
    success error
    rule { id priority allocations { id costCenter { id code } percentage } }
  }
}
"""

DELETE_RULE = """
mutation($id: ID!) {
  deleteCostCenterSplitRule(id: $id) { success error }
}
"""

LIST_RULES = """
query { costCenterSplitRules { id counterparty { id name } bookingTextPattern allocations { id costCenter { code } percentage } } }
"""

SPLIT_TRANSACTION = """
mutation($transactionId: Int!, $splits: [ManualSplitInput!]!) {
  splitTransactionCostCenters(transactionId: $transactionId, splits: $splits) {
    success error
    splits { id costCenter { id code } amount isManual }
  }
}
"""

REPORT = """
query($dateFrom: Date!, $dateTo: Date!) {
  costCenterReport(dateFrom: $dateFrom, dateTo: $dateTo) {
    dateFrom dateTo
    rows { label totalAmount transactionCount costCenter { id code } }
  }
}
"""


class TestSplitRuleCRUD:
    def test_create_rule_with_counterparty(self, db, user, counterparty, cc_marketing, cc_engineering):
        r = run_graphql(CREATE_RULE, {"input": {
            "counterpartyId": str(counterparty.id),
            "allocations": [
                {"costCenterId": str(cc_marketing.id), "percentage": "60"},
                {"costCenterId": str(cc_engineering.id), "percentage": "40"},
            ],
        }}, make_context(user))
        assert r.errors is None
        d = r.data["createCostCenterSplitRule"]
        assert d["success"]
        assert d["rule"]["counterparty"]["name"] == "Acme Corp"
        assert len(d["rule"]["allocations"]) == 2

    def test_create_rule_with_pattern(self, db, user, cc_marketing, cc_engineering):
        r = run_graphql(CREATE_RULE, {"input": {
            "bookingTextPattern": "rent|Miete",
            "priority": 5,
            "allocations": [
                {"costCenterId": str(cc_marketing.id), "percentage": "50"},
                {"costCenterId": str(cc_engineering.id), "percentage": "50"},
            ],
        }}, make_context(user))
        assert r.errors is None
        assert r.data["createCostCenterSplitRule"]["success"]

    def test_create_rule_rejects_no_matcher(self, db, user, cc_marketing):
        r = run_graphql(CREATE_RULE, {"input": {
            "allocations": [{"costCenterId": str(cc_marketing.id), "percentage": "100"}],
        }}, make_context(user))
        assert not r.data["createCostCenterSplitRule"]["success"]
        assert "required" in r.data["createCostCenterSplitRule"]["error"].lower()

    def test_create_rule_rejects_wrong_total(self, db, user, counterparty, cc_marketing, cc_engineering):
        r = run_graphql(CREATE_RULE, {"input": {
            "counterpartyId": str(counterparty.id),
            "allocations": [
                {"costCenterId": str(cc_marketing.id), "percentage": "60"},
                {"costCenterId": str(cc_engineering.id), "percentage": "30"},
            ],
        }}, make_context(user))
        assert not r.data["createCostCenterSplitRule"]["success"]
        assert "100%" in r.data["createCostCenterSplitRule"]["error"]

    def test_update_rule(self, db, user, counterparty, cc_marketing, cc_engineering):
        rule = CostCenterSplitRule.objects.create(tenant=user.tenant, counterparty=counterparty, priority=0)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))

        r = run_graphql(UPDATE_RULE, {"input": {
            "id": str(rule.id),
            "priority": 10,
            "allocations": [
                {"costCenterId": str(cc_marketing.id), "percentage": "70"},
                {"costCenterId": str(cc_engineering.id), "percentage": "30"},
            ],
        }}, make_context(user))
        assert r.errors is None
        d = r.data["updateCostCenterSplitRule"]
        assert d["success"]
        assert d["rule"]["priority"] == 10
        assert len(d["rule"]["allocations"]) == 2

    def test_delete_rule(self, db, user, counterparty, cc_marketing):
        rule = CostCenterSplitRule.objects.create(tenant=user.tenant, counterparty=counterparty)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))

        r = run_graphql(DELETE_RULE, {"id": str(rule.id)}, make_context(user))
        assert r.data["deleteCostCenterSplitRule"]["success"]
        assert not CostCenterSplitRule.objects.filter(id=rule.id).exists()

    def test_list_rules(self, db, user, counterparty, cc_marketing):
        rule = CostCenterSplitRule.objects.create(tenant=user.tenant, counterparty=counterparty)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))

        r = run_graphql(LIST_RULES, {}, make_context(user))
        assert r.errors is None
        assert len(r.data["costCenterSplitRules"]) == 1


class TestAutoApply:
    def test_counterparty_rule_applied(self, db, tenant, counterparty, cc_marketing, cc_engineering, transaction):
        rule = CostCenterSplitRule.objects.create(tenant=tenant, counterparty=counterparty)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("60"))
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_engineering, percentage=Decimal("40"))

        splits = CostCenterSplitService.apply_rule(transaction)
        assert len(splits) == 2
        amounts = {s.cost_center.code: s.amount for s in splits}
        assert amounts["100"] == Decimal("600.00")
        assert amounts["200"] == Decimal("400.00")

    def test_pattern_rule_applied(self, db, tenant, counterparty, cc_marketing, transaction):
        rule = CostCenterSplitRule.objects.create(tenant=tenant, booking_text_pattern="rent")
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))

        splits = CostCenterSplitService.apply_rule(transaction)
        assert len(splits) == 1
        assert splits[0].amount == Decimal("1000.00")

    def test_counterparty_takes_priority_over_pattern(self, db, tenant, counterparty, cc_marketing, cc_engineering, transaction):
        # Pattern rule
        pattern_rule = CostCenterSplitRule.objects.create(
            tenant=tenant, booking_text_pattern="rent", priority=10,
        )
        CostCenterSplitAllocation.objects.create(rule=pattern_rule, cost_center=cc_engineering, percentage=Decimal("100"))

        # Counterparty rule (lower priority number but counterparty always wins)
        cp_rule = CostCenterSplitRule.objects.create(
            tenant=tenant, counterparty=counterparty, priority=0,
        )
        CostCenterSplitAllocation.objects.create(rule=cp_rule, cost_center=cc_marketing, percentage=Decimal("100"))

        splits = CostCenterSplitService.apply_rule(transaction)
        assert len(splits) == 1
        assert splits[0].cost_center.code == "100"  # Marketing from counterparty rule

    def test_no_rule_no_splits(self, db, tenant, transaction):
        splits = CostCenterSplitService.apply_rule(transaction)
        assert len(splits) == 0

    def test_does_not_overwrite_manual(self, db, tenant, counterparty, cc_marketing, cc_engineering, transaction):
        # Create manual split
        TransactionCostCenterSplit.objects.create(
            transaction=transaction, cost_center=cc_engineering, amount=Decimal("1000.00"), is_manual=True,
        )
        # Create rule
        rule = CostCenterSplitRule.objects.create(tenant=tenant, counterparty=counterparty)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))

        splits = CostCenterSplitService.apply_rule(transaction)
        assert len(splits) == 0  # Should not overwrite manual


class TestManualSplit:
    def test_valid_split(self, db, user, transaction, cc_marketing, cc_engineering):
        r = run_graphql(SPLIT_TRANSACTION, {
            "transactionId": transaction.id,
            "splits": [
                {"costCenterId": str(cc_marketing.id), "amount": "600"},
                {"costCenterId": str(cc_engineering.id), "amount": "400"},
            ],
        }, make_context(user))
        assert r.errors is None
        d = r.data["splitTransactionCostCenters"]
        assert d["success"]
        assert len(d["splits"]) == 2
        assert all(s["isManual"] for s in d["splits"])

    def test_amount_mismatch_rejected(self, db, user, transaction, cc_marketing):
        r = run_graphql(SPLIT_TRANSACTION, {
            "transactionId": transaction.id,
            "splits": [{"costCenterId": str(cc_marketing.id), "amount": "500"}],
        }, make_context(user))
        d = r.data["splitTransactionCostCenters"]
        assert not d["success"]
        assert "1000" in d["error"]

    def test_manual_overrides_auto(self, db, user, tenant, transaction, counterparty, cc_marketing, cc_engineering):
        # Auto-apply first
        rule = CostCenterSplitRule.objects.create(tenant=tenant, counterparty=counterparty)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))
        CostCenterSplitService.apply_rule(transaction)
        assert TransactionCostCenterSplit.objects.filter(transaction=transaction).count() == 1

        # Manual split should replace
        r = run_graphql(SPLIT_TRANSACTION, {
            "transactionId": transaction.id,
            "splits": [
                {"costCenterId": str(cc_marketing.id), "amount": "700"},
                {"costCenterId": str(cc_engineering.id), "amount": "300"},
            ],
        }, make_context(user))
        assert r.data["splitTransactionCostCenters"]["success"]
        splits = TransactionCostCenterSplit.objects.filter(transaction=transaction)
        assert splits.count() == 2
        assert all(s.is_manual for s in splits)


class TestCostCenterReport:
    def test_report_aggregation(self, db, user, tenant, account, counterparty, cc_marketing, cc_engineering):
        txn = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-15",
            amount=Decimal("-1000.00"), currency="EUR", counterparty=counterparty,
            import_hash="report1",
        )
        TransactionCostCenterSplit.objects.create(
            transaction=txn, cost_center=cc_marketing, amount=Decimal("600"), is_manual=True,
        )
        TransactionCostCenterSplit.objects.create(
            transaction=txn, cost_center=cc_engineering, amount=Decimal("400"), is_manual=True,
        )

        r = run_graphql(REPORT, {"dateFrom": "2025-01-01", "dateTo": "2025-01-31"}, make_context(user))
        assert r.errors is None
        rows = r.data["costCenterReport"]["rows"]
        labels = {row["label"]: row for row in rows}
        assert "100 – Marketing" in labels
        assert "200 – Engineering" in labels

    def test_unassigned_bucket(self, db, user, tenant, account, counterparty):
        BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-02-10",
            amount=Decimal("-500.00"), currency="EUR", counterparty=counterparty,
            import_hash="unassigned1",
        )

        r = run_graphql(REPORT, {"dateFrom": "2025-02-01", "dateTo": "2025-02-28"}, make_context(user))
        assert r.errors is None
        rows = r.data["costCenterReport"]["rows"]
        unassigned = [row for row in rows if row["label"] == "Unassigned"]
        assert len(unassigned) == 1
        assert unassigned[0]["transactionCount"] == 1

    def test_date_range_filter(self, db, user, tenant, account, counterparty, cc_marketing):
        txn_jan = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-15",
            amount=Decimal("-200.00"), currency="EUR", counterparty=counterparty,
            import_hash="jan1",
        )
        TransactionCostCenterSplit.objects.create(
            transaction=txn_jan, cost_center=cc_marketing, amount=Decimal("200"),
        )
        txn_mar = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-03-15",
            amount=Decimal("-300.00"), currency="EUR", counterparty=counterparty,
            import_hash="mar1",
        )
        TransactionCostCenterSplit.objects.create(
            transaction=txn_mar, cost_center=cc_marketing, amount=Decimal("300"),
        )

        # Query only January
        r = run_graphql(REPORT, {"dateFrom": "2025-01-01", "dateTo": "2025-01-31"}, make_context(user))
        rows = r.data["costCenterReport"]["rows"]
        cc_rows = [row for row in rows if row["costCenter"]]
        assert len(cc_rows) == 1
        assert float(cc_rows[0]["totalAmount"]) == 200.0


class TestTenantIsolation:
    def test_rules_isolated(self, db, user, counterparty, cc_marketing):
        rule = CostCenterSplitRule.objects.create(tenant=user.tenant, counterparty=counterparty)
        CostCenterSplitAllocation.objects.create(rule=rule, cost_center=cc_marketing, percentage=Decimal("100"))

        # Create another tenant
        tenant2 = Tenant.objects.create(name="Other Corp", currency="EUR")
        user2 = User.objects.create_user(email="other@test.com", password="testpass123", tenant=tenant2)
        user2.roles.add(Role.objects.get(tenant=tenant2, name="Admin"))

        r = run_graphql(LIST_RULES, {}, make_context(user2))
        assert r.errors is None
        assert len(r.data["costCenterSplitRules"]) == 0

    def test_manual_split_tenant_isolation(self, db, user, transaction, cc_marketing, cc_engineering):
        # Create another tenant
        tenant2 = Tenant.objects.create(name="Other Corp", currency="EUR")
        user2 = User.objects.create_user(email="other2@test.com", password="testpass123", tenant=tenant2)
        user2.roles.add(Role.objects.get(tenant=tenant2, name="Admin"))

        r = run_graphql(SPLIT_TRANSACTION, {
            "transactionId": transaction.id,
            "splits": [{"costCenterId": str(cc_marketing.id), "amount": "1000"}],
        }, make_context(user2))
        assert not r.data["splitTransactionCostCenters"]["success"]
        assert "not found" in r.data["splitTransactionCostCenters"]["error"].lower()
