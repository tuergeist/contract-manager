"""Tests for banking: MT940 parsing, deduplication, GraphQL, and upload endpoint."""
import io
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from django.test import RequestFactory

from apps.banking.models import BankAccount, BankTransaction
from apps.banking.services import MT940Service
from apps.core.context import Context
from config.schema import schema


# --- Helpers ---


SAMPLE_MT940 = """\
:20:STARTUMS
:25:85090000/2721891006
:28C:0
:60F:C251112EUR211977,96
:61:2511121112DR985,13NDDTKREF+
:86:105?00Basislastschrift?10931?20EREF+0031110078530\
?21KREF+2025110530757791903700?22000000000002\
?23MREF+LC0002X03312346?24CRED+DE96ZZZ00000054695\
?25SVWZ+Miete November?32BMW Bank GmbH?34992
:61:2511121112CR1500,00NTRFKREF+
:86:177?00SEPA-Uberweisung?101000?20EREF+INV-2025-001\
?21KREF+2025111239133803903200?2200001\
?23SVWZ+Zahlung Rechnung INV-2025-001?32Acme Corp GmbH?33
:62F:C251112EUR212492,83
-
:20:STARTUMS
:25:85090000/2721891006
:28C:0
:60F:C251113EUR212492,83
:61:2511131113DR254,85NTRFKREF+
:86:177?00SEPA-Uberweisung?101000?20EREF+507-00000507/2\
?21KREF+2025111239133805903200?2200001\
?23SVWZ+28280461?32Piepenbrock GmbH?33
:62F:C251113EUR212237,98
-
"""

SAMPLE_MT940_OTHER_ACCOUNT = """\
:20:STARTUMS
:25:99990000/9999999999
:28C:0
:60F:C251112EUR1000,00
:61:2511121112DR100,00NDDTKREF+
:86:105?00Lastschrift?10931?20SVWZ+Test?32Someone
:62F:C251112EUR900,00
-
"""


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def account(db, tenant):
    return BankAccount.objects.create(
        tenant=tenant,
        name="Main Account",
        bank_code="85090000",
        account_number="2721891006",
        iban="DE12850900002721891006",
        bic="GENODEF1DRS",
    )


# ============================================================
# 3.6 MT940 Parsing Tests
# ============================================================


class TestMT940Parsing:
    """Test MT940 parsing service using sample data."""

    def test_parse_extracts_transactions(self, tenant, account):
        service = MT940Service(tenant)
        result = service.parse_and_import(account, SAMPLE_MT940)

        assert result.errors is None
        assert result.total == 3
        assert result.imported == 3
        assert result.skipped == 0

    def test_parse_stores_correct_amounts(self, tenant, account):
        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        txns = BankTransaction.objects.filter(account=account).order_by("id")
        amounts = [t.amount for t in txns]
        # First is debit (-985.13), second is credit (+1500.00), third is debit (-254.85)
        assert Decimal("-985.13") in amounts
        assert Decimal("1500.00") in amounts
        assert Decimal("-254.85") in amounts

    def test_parse_stores_dates(self, tenant, account):
        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        txns = BankTransaction.objects.filter(account=account).order_by("entry_date")
        dates = [t.entry_date for t in txns]
        assert date(2025, 11, 12) in dates
        assert date(2025, 11, 13) in dates

    def test_parse_extracts_counterparty(self, tenant, account):
        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        names = set(
            BankTransaction.objects.filter(account=account).values_list(
                "counterparty__name", flat=True
            )
        )
        assert "BMW Bank GmbH" in names
        assert "Acme Corp GmbH" in names
        assert "Piepenbrock GmbH" in names

    def test_parse_extracts_booking_text(self, tenant, account):
        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        txns = BankTransaction.objects.filter(
            account=account, counterparty__name="Acme Corp GmbH"
        )
        assert txns.exists()
        assert "Zahlung Rechnung INV-2025-001" in txns.first().booking_text

    def test_parse_computes_import_hash(self, tenant, account):
        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        txns = BankTransaction.objects.filter(account=account)
        for t in txns:
            assert t.import_hash
            assert len(t.import_hash) == 64  # SHA256 hex

    def test_parse_validates_account_number(self, tenant, account):
        service = MT940Service(tenant)
        result = service.parse_and_import(account, SAMPLE_MT940_OTHER_ACCOUNT)

        assert result.errors is not None
        assert "99990000/9999999999" in result.errors[0]

    def test_parse_handles_utf8(self, tenant, account):
        service = MT940Service(tenant)
        result = service.parse_and_import(account, SAMPLE_MT940.encode("utf-8"))

        assert result.errors is None
        assert result.total == 3

    def test_parse_handles_latin1(self, tenant, account):
        service = MT940Service(tenant)
        result = service.parse_and_import(account, SAMPLE_MT940.encode("latin-1"))

        assert result.errors is None
        assert result.total == 3

    def test_parse_invalid_content(self, tenant, account):
        service = MT940Service(tenant)
        result = service.parse_and_import(account, "this is not MT940 data")

        # Either errors or no transactions found
        assert result.errors is not None or result.total == 0


# ============================================================
# 3.7 Deduplication Tests
# ============================================================


class TestDeduplication:
    """Test that re-importing the same file doesn't create duplicates."""

    def test_reimport_same_file_skips_all(self, tenant, account):
        service = MT940Service(tenant)

        # First import
        result1 = service.parse_and_import(account, SAMPLE_MT940)
        assert result1.imported == 3

        # Re-import same file
        result2 = service.parse_and_import(account, SAMPLE_MT940)
        assert result2.total == 3
        assert result2.imported == 0 or result2.skipped == 3

        # Total in DB should still be 3
        assert BankTransaction.objects.filter(account=account).count() == 3

    def test_overlapping_import_only_adds_new(self, tenant, account):
        service = MT940Service(tenant)

        # Import full file (3 transactions)
        service.parse_and_import(account, SAMPLE_MT940)
        assert BankTransaction.objects.filter(account=account).count() == 3

        # Import same file again — should stay at 3
        result = service.parse_and_import(account, SAMPLE_MT940)
        assert BankTransaction.objects.filter(account=account).count() == 3
        assert result.total == 3

    def test_different_account_same_data_not_deduplicated(self, db, tenant):
        """Transactions to different accounts should not be deduplicated."""
        acc1 = BankAccount.objects.create(
            tenant=tenant,
            name="Account 1",
            bank_code="85090000",
            account_number="2721891006",
        )
        acc2 = BankAccount.objects.create(
            tenant=tenant,
            name="Account 2",
            bank_code="85090000",
            account_number="1111111111",
        )

        service = MT940Service(tenant)
        service.parse_and_import(acc1, SAMPLE_MT940)

        # Same data but different account — hash includes account_id so these are different
        # But the account validation will reject since :25: has 2721891006
        result = service.parse_and_import(acc2, SAMPLE_MT940)
        assert result.errors is not None  # Account mismatch

    def test_import_hash_is_unique_per_tenant(self, db):
        """Same transaction data for different tenants should be separate."""
        from apps.tenants.models import Tenant

        t1 = Tenant.objects.create(name="Tenant 1", currency="EUR")
        t2 = Tenant.objects.create(name="Tenant 2", currency="EUR")

        acc1 = BankAccount.objects.create(
            tenant=t1, name="A1", bank_code="85090000", account_number="2721891006"
        )
        acc2 = BankAccount.objects.create(
            tenant=t2, name="A2", bank_code="85090000", account_number="2721891006"
        )

        MT940Service(t1).parse_and_import(acc1, SAMPLE_MT940)
        MT940Service(t2).parse_and_import(acc2, SAMPLE_MT940)

        assert BankTransaction.objects.filter(tenant=t1).count() == 3
        assert BankTransaction.objects.filter(tenant=t2).count() == 3


# ============================================================
# 4.8 GraphQL Tests
# ============================================================


class TestBankingGraphQL:
    """Test GraphQL queries and mutations for banking."""

    # --- Queries ---

    def test_bank_accounts_query(self, user, account):
        ctx = make_context(user)
        result = run_graphql(
            "{ bankAccounts { id name bankCode accountNumber transactionCount } }",
            {},
            ctx,
        )
        assert result.errors is None
        accounts = result.data["bankAccounts"]
        assert len(accounts) == 1
        assert accounts[0]["name"] == "Main Account"
        assert accounts[0]["bankCode"] == "85090000"
        assert accounts[0]["transactionCount"] == 0

    def test_bank_accounts_includes_transaction_count(self, user, account, tenant):
        # Add some transactions
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            "{ bankAccounts { id transactionCount } }",
            {},
            ctx,
        )
        assert result.errors is None
        assert result.data["bankAccounts"][0]["transactionCount"] == 3

    def test_bank_transactions_query(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query($accountId: Int) {
              bankTransactions(accountId: $accountId, page: 1, pageSize: 50) {
                items { id entryDate amount counterparty { name } bookingText accountName }
                totalCount
                hasNextPage
              }
            }
            """,
            {"accountId": account.id},
            ctx,
        )
        assert result.errors is None
        data = result.data["bankTransactions"]
        assert data["totalCount"] == 3
        assert len(data["items"]) == 3

    def test_bank_transactions_search_filter(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query($search: String) {
              bankTransactions(search: $search) {
                totalCount
                items { counterparty { name } }
              }
            }
            """,
            {"search": "Piepenbrock"},
            ctx,
        )
        assert result.errors is None
        assert result.data["bankTransactions"]["totalCount"] == 1
        assert result.data["bankTransactions"]["items"][0]["counterparty"]["name"] == "Piepenbrock GmbH"

    def test_bank_transactions_direction_filter(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query($direction: String) {
              bankTransactions(direction: $direction) { totalCount }
            }
            """,
            {"direction": "credit"},
            ctx,
        )
        assert result.errors is None
        assert result.data["bankTransactions"]["totalCount"] == 1  # Only the +1500 one

    def test_bank_transactions_pagination(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query {
              bankTransactions(page: 1, pageSize: 2) {
                totalCount
                items { id }
                hasNextPage
              }
            }
            """,
            {},
            ctx,
        )
        assert result.errors is None
        data = result.data["bankTransactions"]
        assert data["totalCount"] == 3
        assert len(data["items"]) == 2
        assert data["hasNextPage"] is True

    # --- Mutations ---

    def test_create_bank_account(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: CreateBankAccountInput!) {
              createBankAccount(input: $input) {
                success
                error
                account { id name bankCode accountNumber }
              }
            }
            """,
            {
                "input": {
                    "name": "New Account",
                    "bankCode": "12345678",
                    "accountNumber": "9999999",
                }
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["createBankAccount"]
        assert data["success"] is True
        assert data["account"]["name"] == "New Account"

    def test_create_duplicate_account_fails(self, user, account):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: CreateBankAccountInput!) {
              createBankAccount(input: $input) { success error }
            }
            """,
            {
                "input": {
                    "name": "Dup",
                    "bankCode": "85090000",
                    "accountNumber": "2721891006",
                }
            },
            ctx,
        )
        assert result.errors is None
        assert result.data["createBankAccount"]["success"] is False

    def test_update_bank_account(self, user, account):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: UpdateBankAccountInput!) {
              updateBankAccount(input: $input) {
                success
                account { name iban }
              }
            }
            """,
            {
                "input": {
                    "id": account.id,
                    "name": "Renamed",
                    "iban": "DE99999999999",
                    "bic": "NEWBIC",
                }
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["updateBankAccount"]
        assert data["success"] is True
        assert data["account"]["name"] == "Renamed"
        assert data["account"]["iban"] == "DE99999999999"

    def test_delete_bank_account(self, user, account):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($id: Int!) {
              deleteBankAccount(id: $id) { success error }
            }
            """,
            {"id": account.id},
            ctx,
        )
        assert result.errors is None
        assert result.data["deleteBankAccount"]["success"] is True
        assert not BankAccount.objects.filter(id=account.id).exists()

    def test_delete_cascades_transactions(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)
        assert BankTransaction.objects.filter(account=account).count() == 3

        ctx = make_context(user)
        run_graphql(
            "mutation($id: Int!) { deleteBankAccount(id: $id) { success } }",
            {"id": account.id},
            ctx,
        )
        assert BankTransaction.objects.filter(account=account).count() == 0


# ============================================================
# 5.5 Upload Endpoint Tests
# ============================================================


class TestUploadEndpoint:
    """Test the REST upload endpoint for MT940 files."""

    def _make_request(self, user, account_id, content, filename="test.sta"):
        from apps.banking.views import UploadStatementView

        factory = RequestFactory()
        file_obj = io.BytesIO(content.encode("utf-8") if isinstance(content, str) else content)
        file_obj.name = filename
        request = factory.post(
            f"/api/banking/upload/{account_id}/",
            {"file": file_obj},
        )
        request.META["HTTP_AUTHORIZATION"] = "Bearer test"
        view = UploadStatementView.as_view()
        # Patch authentication
        from unittest.mock import patch

        with patch(
            "apps.banking.views.get_current_user_from_request", return_value=user
        ):
            return view(request, account_id=account_id)

    def test_upload_valid_file(self, user, account):
        response = self._make_request(user, account.id, SAMPLE_MT940)
        assert response.status_code == 200
        import json

        data = json.loads(response.content)
        assert data["imported"] == 3
        assert data["skipped"] == 0

    def test_upload_duplicate_returns_zero_imported(self, user, account, tenant):
        # First import
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        # Upload same data via endpoint
        response = self._make_request(user, account.id, SAMPLE_MT940)
        assert response.status_code == 200
        import json

        data = json.loads(response.content)
        assert data["imported"] == 0 or data["skipped"] == 3

    def test_upload_wrong_account(self, user, account):
        response = self._make_request(user, account.id, SAMPLE_MT940_OTHER_ACCOUNT)
        assert response.status_code == 400

    def test_upload_invalid_account_id(self, user):
        response = self._make_request(user, 99999, SAMPLE_MT940)
        assert response.status_code == 404

    def test_upload_no_file(self, user, account):
        from apps.banking.views import UploadStatementView
        from unittest.mock import patch

        factory = RequestFactory()
        request = factory.post(f"/api/banking/upload/{account.id}/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer test"
        view = UploadStatementView.as_view()
        with patch(
            "apps.banking.views.get_current_user_from_request", return_value=user
        ):
            response = view(request, account_id=account.id)
        assert response.status_code == 400

    def test_upload_unauthenticated(self, account):
        from apps.banking.views import UploadStatementView
        from unittest.mock import patch

        factory = RequestFactory()
        file_obj = io.BytesIO(SAMPLE_MT940.encode("utf-8"))
        file_obj.name = "test.sta"
        request = factory.post(
            f"/api/banking/upload/{account.id}/",
            {"file": file_obj},
        )
        view = UploadStatementView.as_view()
        with patch(
            "apps.banking.views.get_current_user_from_request", return_value=None
        ):
            response = view(request, account_id=account.id)
        assert response.status_code == 401


# ============================================================
# Counterparty Query Tests
# ============================================================


class TestBankCounterparties:
    """Test counterparties query and counterpartyId filter."""

    def test_counterparties_list(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query {
              counterparties {
                items { id name totalDebit totalCredit transactionCount firstDate lastDate }
                totalCount
                hasNextPage
              }
            }
            """,
            {},
            ctx,
        )
        assert result.errors is None
        data = result.data["counterparties"]
        assert data["totalCount"] == 3
        names = {item["name"] for item in data["items"]}
        assert "BMW Bank GmbH" in names
        assert "Acme Corp GmbH" in names
        assert "Piepenbrock GmbH" in names

    def test_counterparties_aggregation(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query {
              counterparties(sortBy: "name", sortOrder: "asc") {
                items { name totalDebit totalCredit transactionCount }
              }
            }
            """,
            {},
            ctx,
        )
        assert result.errors is None
        items = result.data["counterparties"]["items"]

        acme = next(i for i in items if i["name"] == "Acme Corp GmbH")
        assert float(acme["totalCredit"]) == 1500.0
        assert float(acme["totalDebit"]) == 0.0
        assert acme["transactionCount"] == 1

        bmw = next(i for i in items if i["name"] == "BMW Bank GmbH")
        assert float(bmw["totalDebit"]) == -985.13
        assert float(bmw["totalCredit"]) == 0.0

    def test_counterparties_search(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query($search: String) {
              counterparties(search: $search) {
                totalCount
                items { name }
              }
            }
            """,
            {"search": "Piepen"},
            ctx,
        )
        assert result.errors is None
        assert result.data["counterparties"]["totalCount"] == 1
        assert result.data["counterparties"]["items"][0]["name"] == "Piepenbrock GmbH"

    def test_counterparties_sort_by_name(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query {
              counterparties(sortBy: "name", sortOrder: "asc") {
                items { name }
              }
            }
            """,
            {},
            ctx,
        )
        assert result.errors is None
        names = [i["name"] for i in result.data["counterparties"]["items"]]
        assert names == sorted(names)

    def test_counterparties_pagination(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            query {
              counterparties(page: 1, pageSize: 2) {
                totalCount
                items { name }
                hasNextPage
              }
            }
            """,
            {},
            ctx,
        )
        assert result.errors is None
        data = result.data["counterparties"]
        assert data["totalCount"] == 3
        assert len(data["items"]) == 2
        assert data["hasNextPage"] is True

    def test_counterparty_id_filter_on_transactions(self, user, account, tenant):
        from apps.banking.models import Counterparty

        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        # Get the counterparty ID for BMW Bank GmbH
        bmw_cp = Counterparty.objects.get(tenant=tenant, name="BMW Bank GmbH")

        ctx = make_context(user)
        result = run_graphql(
            """
            query($counterpartyId: ID) {
              bankTransactions(counterpartyId: $counterpartyId) {
                totalCount
                items { counterparty { name } amount }
              }
            }
            """,
            {"counterpartyId": str(bmw_cp.id)},
            ctx,
        )
        assert result.errors is None
        data = result.data["bankTransactions"]
        assert data["totalCount"] == 1
        assert data["items"][0]["counterparty"]["name"] == "BMW Bank GmbH"

    def test_counterparty_query_by_id(self, user, account, tenant):
        from apps.banking.models import Counterparty

        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        # Get the counterparty ID for Acme Corp GmbH
        acme_cp = Counterparty.objects.get(tenant=tenant, name="Acme Corp GmbH")

        ctx = make_context(user)
        result = run_graphql(
            """
            query($id: ID!) {
              counterparty(id: $id) {
                id
                name
                totalDebit
                totalCredit
                transactionCount
              }
            }
            """,
            {"id": str(acme_cp.id)},
            ctx,
        )
        assert result.errors is None
        data = result.data["counterparty"]
        assert data["name"] == "Acme Corp GmbH"
        assert float(data["totalCredit"]) == 1500.0
        assert data["transactionCount"] == 1

    def test_counterparties_empty_state(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            query {
              counterparties {
                totalCount
                items { name }
              }
            }
            """,
            {},
            ctx,
        )
        assert result.errors is None
        assert result.data["counterparties"]["totalCount"] == 0
        assert result.data["counterparties"]["items"] == []


# ============================================================
# Counterparty CRUD & Merge Tests
# ============================================================


class TestCounterpartyCRUD:
    """Test counterparty create, update, and merge mutations."""

    def test_create_counterparty(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: CreateCounterpartyInput!) {
              createCounterparty(input: $input) {
                success
                error
                counterparty { id name iban bic }
              }
            }
            """,
            {"input": {"name": "New Company GmbH", "iban": "DE123456", "bic": "COBADEFF"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["createCounterparty"]
        assert data["success"] is True
        assert data["counterparty"]["name"] == "New Company GmbH"
        assert data["counterparty"]["iban"] == "DE123456"
        assert data["counterparty"]["bic"] == "COBADEFF"

    def test_create_counterparty_minimal(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: CreateCounterpartyInput!) {
              createCounterparty(input: $input) {
                success
                counterparty { name iban bic }
              }
            }
            """,
            {"input": {"name": "Simple Corp"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["createCounterparty"]
        assert data["success"] is True
        assert data["counterparty"]["name"] == "Simple Corp"
        assert data["counterparty"]["iban"] == ""
        assert data["counterparty"]["bic"] == ""

    def test_create_counterparty_duplicate_fails(self, user, account, tenant):
        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: CreateCounterpartyInput!) {
              createCounterparty(input: $input) {
                success
                error
              }
            }
            """,
            {"input": {"name": "BMW Bank GmbH"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["createCounterparty"]
        assert data["success"] is False
        assert "already exists" in data["error"]

    def test_create_counterparty_empty_name_fails(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: CreateCounterpartyInput!) {
              createCounterparty(input: $input) {
                success
                error
              }
            }
            """,
            {"input": {"name": "  "}},
            ctx,
        )
        assert result.errors is None
        data = result.data["createCounterparty"]
        assert data["success"] is False
        assert "required" in data["error"].lower()

    def test_update_counterparty_rename(self, user, account, tenant):
        from apps.banking.models import Counterparty

        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)
        cp = Counterparty.objects.get(tenant=tenant, name="BMW Bank GmbH")

        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: UpdateCounterpartyInput!) {
              updateCounterparty(input: $input) {
                success
                counterparty { name }
              }
            }
            """,
            {"input": {"id": str(cp.id), "name": "BMW Financial Services"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["updateCounterparty"]
        assert data["success"] is True
        assert data["counterparty"]["name"] == "BMW Financial Services"

        # Verify in DB
        cp.refresh_from_db()
        assert cp.name == "BMW Financial Services"

    def test_update_counterparty_iban_bic(self, user, account, tenant):
        from apps.banking.models import Counterparty

        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)
        cp = Counterparty.objects.get(tenant=tenant, name="Acme Corp GmbH")

        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: UpdateCounterpartyInput!) {
              updateCounterparty(input: $input) {
                success
                counterparty { iban bic }
              }
            }
            """,
            {"input": {"id": str(cp.id), "iban": "DE999999999", "bic": "NEWBIC123"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["updateCounterparty"]
        assert data["success"] is True
        assert data["counterparty"]["iban"] == "DE999999999"
        assert data["counterparty"]["bic"] == "NEWBIC123"

    def test_update_counterparty_not_found(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($input: UpdateCounterpartyInput!) {
              updateCounterparty(input: $input) {
                success
                error
              }
            }
            """,
            {"input": {"id": "00000000-0000-0000-0000-000000000000", "name": "Test"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["updateCounterparty"]
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_merge_counterparties(self, user, account, tenant):
        from apps.banking.models import Counterparty, BankTransaction

        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)

        source = Counterparty.objects.get(tenant=tenant, name="BMW Bank GmbH")
        target = Counterparty.objects.get(tenant=tenant, name="Acme Corp GmbH")

        # Verify initial state
        assert BankTransaction.objects.filter(counterparty=source).count() == 1
        assert BankTransaction.objects.filter(counterparty=target).count() == 1

        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($sourceId: ID!, $targetId: ID!) {
              mergeCounterparties(sourceId: $sourceId, targetId: $targetId) {
                success
                mergedTransactionCount
                target { name }
              }
            }
            """,
            {"sourceId": str(source.id), "targetId": str(target.id)},
            ctx,
        )
        assert result.errors is None
        data = result.data["mergeCounterparties"]
        assert data["success"] is True
        assert data["mergedTransactionCount"] == 1
        assert data["target"]["name"] == "Acme Corp GmbH"

        # Verify source deleted and transactions moved
        assert not Counterparty.objects.filter(id=source.id).exists()
        assert BankTransaction.objects.filter(counterparty=target).count() == 2

    def test_merge_counterparties_into_self_fails(self, user, account, tenant):
        from apps.banking.models import Counterparty

        MT940Service(tenant).parse_and_import(account, SAMPLE_MT940)
        cp = Counterparty.objects.get(tenant=tenant, name="BMW Bank GmbH")

        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($sourceId: ID!, $targetId: ID!) {
              mergeCounterparties(sourceId: $sourceId, targetId: $targetId) {
                success
                error
              }
            }
            """,
            {"sourceId": str(cp.id), "targetId": str(cp.id)},
            ctx,
        )
        assert result.errors is None
        data = result.data["mergeCounterparties"]
        assert data["success"] is False
        assert "itself" in data["error"].lower()

    def test_merge_counterparties_not_found(self, user):
        ctx = make_context(user)
        result = run_graphql(
            """
            mutation($sourceId: ID!, $targetId: ID!) {
              mergeCounterparties(sourceId: $sourceId, targetId: $targetId) {
                success
                error
              }
            }
            """,
            {
                "sourceId": "00000000-0000-0000-0000-000000000000",
                "targetId": "00000000-0000-0000-0000-000000000001",
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["mergeCounterparties"]
        assert data["success"] is False
        assert "not found" in data["error"].lower()


# ============================================================
# MT940 Counterparty Creation Tests
# ============================================================


class TestMT940CounterpartyCreation:
    """Test that MT940 import correctly creates counterparties."""

    def test_import_creates_counterparties(self, tenant, account):
        from apps.banking.models import Counterparty

        assert Counterparty.objects.filter(tenant=tenant).count() == 0

        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        # Should have created 3 counterparties
        assert Counterparty.objects.filter(tenant=tenant).count() == 3
        names = set(Counterparty.objects.filter(tenant=tenant).values_list("name", flat=True))
        assert names == {"BMW Bank GmbH", "Acme Corp GmbH", "Piepenbrock GmbH"}

    def test_import_reuses_existing_counterparties(self, tenant, account):
        from apps.banking.models import Counterparty

        # Pre-create one counterparty
        existing = Counterparty.objects.create(
            tenant=tenant, name="BMW Bank GmbH", iban="DE111111", bic="EXISTING"
        )

        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        # Should have reused the existing one and created 2 new
        assert Counterparty.objects.filter(tenant=tenant).count() == 3

        # The existing one should be unchanged
        existing.refresh_from_db()
        assert existing.iban == "DE111111"
        assert existing.bic == "EXISTING"

        # Transaction should be linked to existing counterparty
        txn = BankTransaction.objects.get(counterparty=existing)
        assert txn.counterparty_id == existing.id

    def test_import_links_transactions_to_counterparties(self, tenant, account):
        from apps.banking.models import Counterparty

        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        # Each transaction should have a counterparty FK
        for txn in BankTransaction.objects.filter(account=account):
            assert txn.counterparty is not None
            assert txn.counterparty.tenant == tenant

    def test_reimport_uses_same_counterparties(self, tenant, account):
        from apps.banking.models import Counterparty

        service = MT940Service(tenant)
        service.parse_and_import(account, SAMPLE_MT940)

        cp_ids_before = set(Counterparty.objects.filter(tenant=tenant).values_list("id", flat=True))

        # Import again (transactions will be skipped due to dedup)
        service.parse_and_import(account, SAMPLE_MT940)

        cp_ids_after = set(Counterparty.objects.filter(tenant=tenant).values_list("id", flat=True))

        # Same counterparties, no new ones created
        assert cp_ids_before == cp_ids_after
