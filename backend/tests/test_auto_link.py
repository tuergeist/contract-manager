"""Tests for time tracking auto-link rules and background sync."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from apps.contracts.models import (
    AutoLinkRule,
    Contract,
    ContractItem,
    TimeTrackingProjectMapping,
)
from apps.contracts.services.time_tracking import matches_project_name, TimeTrackingProject
from apps.core.context import Context
from config.schema import schema


# --- Helpers ---


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


# --- Fixtures ---


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Test Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval="monthly",
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_item(db, tenant, contract):
    return ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        description="Development Services",
        quantity=1,
        unit_price=Decimal("5000.00"),
        price_period="monthly",
    )


@pytest.fixture
def customer(db, tenant):
    from apps.customers.models import Customer
    return Customer.objects.create(
        tenant=tenant,
        name="Acme Corp",
        is_active=True,
    )


# --- matches_project_name tests ---


class TestMatchesProjectName:
    def test_contains_match(self):
        assert matches_project_name("[KSB DL-Vertrag]", "contains", "[KSB DL-Vertrag] Maintenance") is True

    def test_contains_no_match(self):
        assert matches_project_name("[KSB DL-Vertrag]", "contains", "Other Project") is False

    def test_contains_case_insensitive(self):
        assert matches_project_name("[ksb dl-vertrag]", "contains", "[KSB DL-Vertrag] Q1") is True

    def test_starts_with_match(self):
        assert matches_project_name("KSB-", "starts_with", "KSB-Maintenance") is True

    def test_starts_with_no_match(self):
        assert matches_project_name("KSB-", "starts_with", "Other-KSB-Project") is False

    def test_starts_with_case_insensitive(self):
        assert matches_project_name("ksb-", "starts_with", "KSB-Project") is True

    def test_unknown_match_type_returns_false(self):
        assert matches_project_name("test", "regex", "test project") is False


# --- Auto-link task tests ---


MOCK_PROJECTS = [
    TimeTrackingProject(id="p1", name="[KSB DL-Vertrag] Maintenance", customer_name="KSB", active=True),
    TimeTrackingProject(id="p2", name="[KSB DL-Vertrag] Dev Q1", customer_name="KSB", active=True),
    TimeTrackingProject(id="p3", name="Other Project", customer_name="Other", active=True),
]


@pytest.mark.django_db
class TestAutoLinkTask:

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_creates_mapping_for_matching_project(self, mock_sync, tenant, contract):
        AutoLinkRule.objects.create(
            tenant=tenant, contract=contract,
            pattern="[KSB DL-Vertrag]", match_type="contains",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            from apps.contracts.tasks import auto_link_time_tracking_projects
            result = auto_link_time_tracking_projects()

        assert result == 2  # p1 and p2 match
        assert TimeTrackingProjectMapping.objects.filter(tenant=tenant).count() == 2
        m = TimeTrackingProjectMapping.objects.get(external_project_id="p1")
        assert m.link_source == "auto"
        assert m.contract == contract

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_skips_already_linked(self, mock_sync, tenant, contract):
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant, contract=contract,
            external_project_id="p1", external_project_name="Already linked",
        )
        AutoLinkRule.objects.create(
            tenant=tenant, contract=contract,
            pattern="[KSB DL-Vertrag]", match_type="contains",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            from apps.contracts.tasks import auto_link_time_tracking_projects
            result = auto_link_time_tracking_projects()

        assert result == 1  # only p2, p1 already linked
        assert TimeTrackingProjectMapping.objects.filter(tenant=tenant).count() == 2

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_skips_cancelled_contracts(self, mock_sync, tenant, contract):
        contract.status = Contract.Status.CANCELLED
        contract.save()
        AutoLinkRule.objects.create(
            tenant=tenant, contract=contract,
            pattern="[KSB DL-Vertrag]", match_type="contains",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            from apps.contracts.tasks import auto_link_time_tracking_projects
            result = auto_link_time_tracking_projects()

        assert result == 0

    def test_skips_tenants_without_provider(self, tenant, contract):
        AutoLinkRule.objects.create(
            tenant=tenant, contract=contract,
            pattern="[KSB DL-Vertrag]", match_type="contains",
        )

        with patch("apps.contracts.services.time_tracking.get_provider", return_value=None):
            from apps.contracts.tasks import auto_link_time_tracking_projects
            result = auto_link_time_tracking_projects()

        assert result == 0

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_links_to_contract_item(self, mock_sync, tenant, contract, contract_item):
        AutoLinkRule.objects.create(
            tenant=tenant, contract=contract, contract_item=contract_item,
            pattern="[KSB DL-Vertrag]", match_type="contains",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS[:1]
            mock_provider.return_value = provider

            from apps.contracts.tasks import auto_link_time_tracking_projects
            auto_link_time_tracking_projects()

        m = TimeTrackingProjectMapping.objects.get(external_project_id="p1")
        assert m.contract_item == contract_item


# --- GraphQL mutation tests ---


CREATE_RULE_MUTATION = """
mutation($contractId: ID!, $pattern: String!, $matchType: String!, $contractItemId: ID) {
  createAutoLinkRule(
    contractId: $contractId
    pattern: $pattern
    matchType: $matchType
    contractItemId: $contractItemId
  ) {
    success
    error
  }
}
"""

DELETE_RULE_MUTATION = """
mutation($ruleId: ID!) {
  deleteAutoLinkRule(ruleId: $ruleId) {
    success
    error
  }
}
"""


@pytest.mark.django_db
class TestCreateAutoLinkRule:

    def test_creates_rule(self, user, contract):
        result = run_graphql(CREATE_RULE_MUTATION, {
            "contractId": str(contract.id),
            "pattern": "[KSB DL-Vertrag]",
            "matchType": "contains",
        }, make_context(user))
        assert result.errors is None
        assert result.data["createAutoLinkRule"]["success"] is True
        assert AutoLinkRule.objects.filter(contract=contract).count() == 1
        rule = AutoLinkRule.objects.first()
        assert rule.pattern == "[KSB DL-Vertrag]"
        assert rule.match_type == "contains"

    def test_validates_contract_item_belongs(self, user, tenant, contract, customer):
        other_contract = Contract.objects.create(
            tenant=tenant, customer=customer, name="Other",
            status=Contract.Status.ACTIVE, start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1), billing_interval="monthly",
            billing_anchor_day=1,
        )
        other_item = ContractItem.objects.create(
            tenant=tenant, contract=other_contract, description="Other item",
            quantity=1, unit_price=Decimal("100"), price_period="monthly",
        )
        result = run_graphql(CREATE_RULE_MUTATION, {
            "contractId": str(contract.id),
            "pattern": "test",
            "matchType": "contains",
            "contractItemId": str(other_item.id),
        }, make_context(user))
        assert result.data["createAutoLinkRule"]["success"] is False
        assert "Item not found" in result.data["createAutoLinkRule"]["error"]

    def test_rejects_empty_pattern(self, user, contract):
        result = run_graphql(CREATE_RULE_MUTATION, {
            "contractId": str(contract.id),
            "pattern": "  ",
            "matchType": "contains",
        }, make_context(user))
        assert result.data["createAutoLinkRule"]["success"] is False
        assert "empty" in result.data["createAutoLinkRule"]["error"].lower()

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_applies_rule_immediately_creating_mappings(
        self, mock_sync, user, tenant, contract
    ):
        """Creating a rule must match existing projects right away, not wait 24h."""
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            result = run_graphql(CREATE_RULE_MUTATION, {
                "contractId": str(contract.id),
                "pattern": "[KSB DL-Vertrag]",
                "matchType": "contains",
            }, make_context(user))

        assert result.data["createAutoLinkRule"]["success"] is True
        # p1 and p2 match and should be linked immediately
        mappings = TimeTrackingProjectMapping.objects.filter(tenant=tenant)
        assert mappings.count() == 2
        assert {m.external_project_id for m in mappings} == {"p1", "p2"}
        assert all(m.link_source == "auto" for m in mappings)

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_immediate_apply_uses_contract_item(
        self, mock_sync, user, tenant, contract
    ):
        """Rule with contract_item_id passes it through to created mappings."""
        item = ContractItem.objects.create(
            tenant=tenant, contract=contract, description="Wartung",
            quantity=1, unit_price=Decimal("100"), price_period="monthly",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            run_graphql(CREATE_RULE_MUTATION, {
                "contractId": str(contract.id),
                "pattern": "[KSB DL-Vertrag]",
                "matchType": "contains",
                "contractItemId": str(item.id),
            }, make_context(user))

        mappings = TimeTrackingProjectMapping.objects.filter(tenant=tenant)
        assert mappings.count() == 2
        assert all(m.contract_item_id == item.id for m in mappings)

    @patch("apps.contracts.tasks.sync_time_tracking_mapping_task")
    def test_immediate_apply_failure_does_not_fail_mutation(
        self, mock_sync, user, tenant, contract
    ):
        """If the provider call fails, the rule is still saved for the daily task."""
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.side_effect = Exception("Clockodo down")
            mock_provider.return_value = provider

            result = run_graphql(CREATE_RULE_MUTATION, {
                "contractId": str(contract.id),
                "pattern": "[KSB DL-Vertrag]",
                "matchType": "contains",
            }, make_context(user))

        assert result.data["createAutoLinkRule"]["success"] is True
        assert AutoLinkRule.objects.filter(contract=contract).count() == 1
        assert TimeTrackingProjectMapping.objects.filter(tenant=tenant).count() == 0


@pytest.mark.django_db
class TestDeleteAutoLinkRule:

    def test_deletes_rule(self, user, contract):
        rule = AutoLinkRule.objects.create(
            tenant=user.tenant, contract=contract,
            pattern="test", match_type="contains",
        )
        result = run_graphql(DELETE_RULE_MUTATION, {
            "ruleId": str(rule.id),
        }, make_context(user))
        assert result.errors is None
        assert result.data["deleteAutoLinkRule"]["success"] is True
        assert not AutoLinkRule.objects.filter(id=rule.id).exists()

    def test_mappings_retained_after_rule_delete(self, user, tenant, contract):
        rule = AutoLinkRule.objects.create(
            tenant=tenant, contract=contract,
            pattern="test", match_type="contains",
        )
        mapping = TimeTrackingProjectMapping.objects.create(
            tenant=tenant, contract=contract,
            external_project_id="p1", external_project_name="Test",
            link_source="auto", auto_link_rule=rule,
        )

        run_graphql(DELETE_RULE_MUTATION, {"ruleId": str(rule.id)}, make_context(user))

        mapping.refresh_from_db()
        assert mapping.auto_link_rule is None  # SET_NULL
        assert TimeTrackingProjectMapping.objects.filter(id=mapping.id).exists()


# --- Preview query tests ---


PREVIEW_QUERY = """
query($pattern: String!, $matchType: String!) {
  previewAutoLinkMatches(pattern: $pattern, matchType: $matchType) {
    id
    name
    customerName
  }
}
"""


@pytest.mark.django_db
class TestPreviewAutoLinkMatches:

    def test_returns_matching_unlinked(self, user, tenant):
        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            result = run_graphql(PREVIEW_QUERY, {
                "pattern": "[KSB DL-Vertrag]",
                "matchType": "contains",
            }, make_context(user))

        assert result.errors is None
        matches = result.data["previewAutoLinkMatches"]
        assert len(matches) == 2
        assert matches[0]["name"] == "[KSB DL-Vertrag] Maintenance"

    def test_excludes_already_linked(self, user, tenant, contract):
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant, contract=contract,
            external_project_id="p1", external_project_name="Already linked",
        )

        with patch("apps.contracts.services.time_tracking.get_provider") as mock_provider:
            provider = Mock()
            provider.get_projects.return_value = MOCK_PROJECTS
            mock_provider.return_value = provider

            result = run_graphql(PREVIEW_QUERY, {
                "pattern": "[KSB DL-Vertrag]",
                "matchType": "contains",
            }, make_context(user))

        assert len(result.data["previewAutoLinkMatches"]) == 1
        assert result.data["previewAutoLinkMatches"][0]["id"] == "p2"


# --- link_source field test ---


SUMMARY_QUERY = """
query($contractId: ID!) {
  timeTrackingSummary(contractId: $contractId) {
    mappings {
      id
      linkSource
    }
    autoLinkRules {
      id
      pattern
      matchType
      createdMappingsCount
    }
  }
}
"""


@pytest.mark.django_db
class TestLinkSourceField:

    def test_manual_mapping_shows_manual(self, user, tenant, contract):
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant, contract=contract,
            external_project_id="p1", external_project_name="Test",
            link_source="manual",
        )
        result = run_graphql(SUMMARY_QUERY, {
            "contractId": str(contract.id),
        }, make_context(user))
        assert result.errors is None
        assert result.data["timeTrackingSummary"]["mappings"][0]["linkSource"] == "manual"

    def test_auto_mapping_shows_auto(self, user, tenant, contract):
        rule = AutoLinkRule.objects.create(
            tenant=tenant, contract=contract,
            pattern="test", match_type="contains",
        )
        TimeTrackingProjectMapping.objects.create(
            tenant=tenant, contract=contract,
            external_project_id="p1", external_project_name="Test",
            link_source="auto", auto_link_rule=rule,
        )
        result = run_graphql(SUMMARY_QUERY, {
            "contractId": str(contract.id),
        }, make_context(user))
        assert result.errors is None
        assert result.data["timeTrackingSummary"]["mappings"][0]["linkSource"] == "auto"
        rules = result.data["timeTrackingSummary"]["autoLinkRules"]
        assert len(rules) == 1
        assert rules[0]["pattern"] == "test"
        assert rules[0]["createdMappingsCount"] == 1
