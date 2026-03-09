"""Tests for cost center feature: CRUD, assignments, auto-assign, permissions, tenant isolation."""
import pytest
from decimal import Decimal
from unittest.mock import Mock

from apps.banking.models import BankAccount, BankTransaction, CostCenter, Counterparty
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
def cost_center(db, tenant):
    return CostCenter.objects.create(tenant=tenant, code="100", name="Marketing")


@pytest.fixture
def viewer_user(db, tenant):
    u = User.objects.create_user(email="viewer@example.com", password="testpass123", tenant=tenant)
    u.roles.add(Role.objects.get(tenant=tenant, name="Viewer"))
    return u


@pytest.fixture
def manager_user(db, tenant):
    u = User.objects.create_user(email="manager@example.com", password="testpass123", tenant=tenant)
    u.roles.add(Role.objects.get(tenant=tenant, name="Manager"))
    return u


CREATE_CC = 'mutation($input: CreateCostCenterInput!) { createCostCenter(input: $input) { success error costCenter { id code name isActive } } }'
UPDATE_CC = 'mutation($input: UpdateCostCenterInput!) { updateCostCenter(input: $input) { success error costCenter { id code name isActive } } }'
DELETE_CC = 'mutation($id: ID!, $force: Boolean!) { deleteCostCenter(id: $id, force: $force) { success error inUse usageCount } }'
LIST_CC = 'query($isActive: Boolean) { costCenters(isActive: $isActive) { id code name isActive } }'
ASSIGN_TX_CC = 'mutation($transactionId: Int!, $costCenterId: ID) { assignTransactionCostCenter(transactionId: $transactionId, costCenterId: $costCenterId) { success error } }'
UPDATE_CP = 'mutation($input: UpdateCounterpartyInput!) { updateCounterparty(input: $input) { success error counterparty { id name defaultCostCenter { id code name } } } }'


class TestCostCenterCRUD:
    def test_create(self, db, user, tenant):
        r = run_graphql(CREATE_CC, {"input": {"code": "IT", "name": "IT Dept"}}, make_context(user))
        assert r.errors is None
        assert r.data["createCostCenter"]["success"]
        assert CostCenter.objects.filter(tenant=tenant, code="IT").exists()

    def test_duplicate_code_rejected(self, db, user, cost_center):
        r = run_graphql(CREATE_CC, {"input": {"code": "100", "name": "Dup"}}, make_context(user))
        assert not r.data["createCostCenter"]["success"]
        assert "already exists" in r.data["createCostCenter"]["error"]

    def test_edit(self, db, user, cost_center):
        r = run_graphql(UPDATE_CC, {"input": {"id": str(cost_center.id), "name": "Updated", "isActive": False}}, make_context(user))
        assert r.data["updateCostCenter"]["success"]
        cost_center.refresh_from_db()
        assert cost_center.name == "Updated"
        assert cost_center.is_active is False

    def test_delete(self, db, user, cost_center):
        r = run_graphql(DELETE_CC, {"id": str(cost_center.id), "force": False}, make_context(user))
        assert r.data["deleteCostCenter"]["success"]
        assert not CostCenter.objects.filter(id=cost_center.id).exists()

    def test_delete_with_assignments(self, db, user, tenant, cost_center, account, counterparty):
        txn = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-01", amount=Decimal("-100"),
            currency="EUR", transaction_type="DEBIT", counterparty=counterparty,
            cost_center=cost_center, booking_text="Test", reference="REF", import_hash="hash123",
        )
        ctx = make_context(user)
        r = run_graphql(DELETE_CC, {"id": str(cost_center.id), "force": False}, ctx)
        assert not r.data["deleteCostCenter"]["success"]
        assert r.data["deleteCostCenter"]["inUse"]

        r = run_graphql(DELETE_CC, {"id": str(cost_center.id), "force": True}, ctx)
        assert r.data["deleteCostCenter"]["success"]
        txn.refresh_from_db()
        assert txn.cost_center is None

    def test_list_with_active_filter(self, db, user, tenant):
        CostCenter.objects.create(tenant=tenant, code="A", name="Active", is_active=True)
        CostCenter.objects.create(tenant=tenant, code="I", name="Inactive", is_active=False)
        ctx = make_context(user)
        r = run_graphql(LIST_CC, {"isActive": True}, ctx)
        assert len(r.data["costCenters"]) == 1
        r = run_graphql(LIST_CC, {}, ctx)
        assert len(r.data["costCenters"]) == 2


class TestDefaultCostCenter:
    def test_set_default(self, db, user, counterparty, cost_center):
        r = run_graphql(UPDATE_CP, {"input": {"id": str(counterparty.id), "defaultCostCenterId": str(cost_center.id)}}, make_context(user))
        assert r.data["updateCounterparty"]["success"]
        assert r.data["updateCounterparty"]["counterparty"]["defaultCostCenter"]["code"] == "100"

    def test_change_default(self, db, user, tenant, counterparty, cost_center):
        counterparty.default_cost_center = cost_center
        counterparty.save()
        cc2 = CostCenter.objects.create(tenant=tenant, code="200", name="Sales")
        r = run_graphql(UPDATE_CP, {"input": {"id": str(counterparty.id), "defaultCostCenterId": str(cc2.id)}}, make_context(user))
        assert r.data["updateCounterparty"]["counterparty"]["defaultCostCenter"]["code"] == "200"

    def test_clear_default(self, db, user, counterparty, cost_center):
        counterparty.default_cost_center = cost_center
        counterparty.save()
        r = run_graphql(UPDATE_CP, {"input": {"id": str(counterparty.id), "defaultCostCenterId": None}}, make_context(user))
        assert r.data["updateCounterparty"]["counterparty"]["defaultCostCenter"] is None


class TestAutoAssignment:
    def test_auto_assign_on_import(self, db, tenant, account, cost_center):
        from apps.banking.services.mt940 import MT940Service
        cp = Counterparty.objects.create(tenant=tenant, name="BMW Bank GmbH", default_cost_center=cost_center)
        service = MT940Service(tenant)
        service._counterparty_cache["BMW Bank GmbH"] = cp
        mt940_data = ":20:STARTUMS\n:25:85090000/2721891006\n:28C:0\n:60F:C251112EUR1000,00\n:61:2511121112DR100,00NDDTKREF+\n:86:105?00Basislastschrift?20SVWZ+Test?32BMW Bank GmbH?34992\n:62F:C251112EUR900,00\n-\n"
        result = service.parse_and_import(account, mt940_data)
        assert result.imported == 1
        txn = BankTransaction.objects.filter(counterparty=cp).first()
        assert txn is not None
        assert txn.cost_center == cost_center


class TestManualAssignment:
    def test_assign(self, db, user, tenant, account, counterparty, cost_center):
        txn = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-01", amount=Decimal("-50"),
            currency="EUR", transaction_type="DEBIT", counterparty=counterparty,
            booking_text="Test", reference="REF", import_hash="hash456",
        )
        r = run_graphql(ASSIGN_TX_CC, {"transactionId": txn.id, "costCenterId": str(cost_center.id)}, make_context(user))
        assert r.data["assignTransactionCostCenter"]["success"]
        txn.refresh_from_db()
        assert txn.cost_center == cost_center

    def test_clear(self, db, user, tenant, account, counterparty, cost_center):
        txn = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-01", amount=Decimal("-50"),
            currency="EUR", transaction_type="DEBIT", counterparty=counterparty,
            cost_center=cost_center, booking_text="Test", reference="REF", import_hash="hash789",
        )
        r = run_graphql(ASSIGN_TX_CC, {"transactionId": txn.id, "costCenterId": None}, make_context(user))
        assert r.data["assignTransactionCostCenter"]["success"]
        txn.refresh_from_db()
        assert txn.cost_center is None


class TestTenantIsolation:
    def test_cannot_see_other_tenants(self, db, tenant, user):
        other = Tenant.objects.create(name="Other", currency="EUR")
        CostCenter.objects.create(tenant=other, code="999", name="Other")
        CostCenter.objects.create(tenant=tenant, code="100", name="Mine")
        r = run_graphql(LIST_CC, {}, make_context(user))
        codes = [cc["code"] for cc in r.data["costCenters"]]
        assert "100" in codes
        assert "999" not in codes


class TestPermissions:
    def test_viewer_can_read(self, db, viewer_user, cost_center):
        r = run_graphql(LIST_CC, {}, make_context(viewer_user))
        assert r.errors is None
        assert len(r.data["costCenters"]) == 1

    def test_viewer_cannot_create(self, db, viewer_user):
        r = run_graphql(CREATE_CC, {"input": {"code": "X", "name": "Test"}}, make_context(viewer_user))
        assert not r.data["createCostCenter"]["success"]

    def test_viewer_cannot_assign(self, db, viewer_user, tenant, account, counterparty, cost_center):
        txn = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-01", amount=Decimal("-50"),
            currency="EUR", transaction_type="DEBIT", counterparty=counterparty,
            booking_text="Test", reference="REF", import_hash="hashperm1",
        )
        r = run_graphql(ASSIGN_TX_CC, {"transactionId": txn.id, "costCenterId": str(cost_center.id)}, make_context(viewer_user))
        assert not r.data["assignTransactionCostCenter"]["success"]

    def test_manager_can_assign(self, db, manager_user, tenant, account, counterparty, cost_center):
        txn = BankTransaction.objects.create(
            tenant=tenant, account=account, entry_date="2025-01-01", amount=Decimal("-50"),
            currency="EUR", transaction_type="DEBIT", counterparty=counterparty,
            booking_text="Test", reference="REF", import_hash="hashperm2",
        )
        r = run_graphql(ASSIGN_TX_CC, {"transactionId": txn.id, "costCenterId": str(cost_center.id)}, make_context(manager_user))
        assert r.data["assignTransactionCostCenter"]["success"]

    def test_manager_cannot_crud(self, db, manager_user):
        r = run_graphql(CREATE_CC, {"input": {"code": "X", "name": "Test"}}, make_context(manager_user))
        assert not r.data["createCostCenter"]["success"]
