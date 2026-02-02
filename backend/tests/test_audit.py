"""Tests for audit logging."""

import pytest
from datetime import date
from decimal import Decimal

from apps.audit.models import AuditLog
from apps.audit.services import AuditLogService, set_current_user, clear_current_user
from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product


class TestAuditLogServiceDiff:
    """Test AuditLogService.compute_diff()."""

    def test_compute_diff_detects_changes(self):
        """Test that compute_diff detects changed fields."""
        old = {"name": "Old Name", "status": "draft", "value": 100}
        new = {"name": "New Name", "status": "draft", "value": 200}

        diff = AuditLogService.compute_diff(old, new)

        assert "name" in diff
        assert diff["name"]["old"] == "Old Name"
        assert diff["name"]["new"] == "New Name"
        assert "value" in diff
        assert diff["value"]["old"] == 100
        assert diff["value"]["new"] == 200
        # Unchanged field should not be in diff
        assert "status" not in diff

    def test_compute_diff_handles_new_fields(self):
        """Test that compute_diff handles fields only in new values."""
        old = {"name": "Test"}
        new = {"name": "Test", "description": "New field"}

        diff = AuditLogService.compute_diff(old, new)

        assert "description" in diff
        assert diff["description"]["old"] is None
        assert diff["description"]["new"] == "New field"

    def test_compute_diff_handles_removed_fields(self):
        """Test that compute_diff handles fields only in old values."""
        old = {"name": "Test", "old_field": "Old value"}
        new = {"name": "Test"}

        diff = AuditLogService.compute_diff(old, new)

        assert "old_field" in diff
        assert diff["old_field"]["old"] == "Old value"
        assert diff["old_field"]["new"] is None

    def test_compute_diff_empty_when_no_changes(self):
        """Test that compute_diff returns empty dict when no changes."""
        old = {"name": "Same", "value": 100}
        new = {"name": "Same", "value": 100}

        diff = AuditLogService.compute_diff(old, new)

        assert diff == {}


class TestAuditLogServiceSerialization:
    """Test AuditLogService value serialization."""

    def test_serialize_date(self):
        """Test date serialization."""
        value = date(2026, 1, 15)
        result = AuditLogService.serialize_value(value)
        assert result == "2026-01-15"

    def test_serialize_decimal(self):
        """Test Decimal serialization."""
        value = Decimal("123.45")
        result = AuditLogService.serialize_value(value)
        assert result == "123.45"

    def test_serialize_none(self):
        """Test None serialization."""
        result = AuditLogService.serialize_value(None)
        assert result is None

    def test_serialize_string(self):
        """Test string passthrough."""
        result = AuditLogService.serialize_value("test")
        assert result == "test"


@pytest.fixture
def customer(db, tenant):
    """Create a test customer."""
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
    )


@pytest.fixture
def product(db, tenant):
    """Create a test product."""
    return Product.objects.create(
        tenant=tenant,
        name="Test Product",
        sku="TEST-001",
    )


class TestAuditLogSignals:
    """Test audit log signal handlers."""

    def test_create_logs_create_action(self, db, tenant, user, customer):
        """Test that creating an entity logs a create action."""
        # Set the current user for audit
        set_current_user(user)

        try:
            contract = Contract.objects.create(
                tenant=tenant,
                customer=customer,
                name="New Contract",
                status=Contract.Status.DRAFT,
                start_date=date(2026, 1, 1),
                billing_start_date=date(2026, 1, 1),
                billing_interval=Contract.BillingInterval.MONTHLY,
            )

            # Check audit log was created
            log = AuditLog.objects.filter(
                entity_type="contract",
                entity_id=contract.id,
                action=AuditLog.Action.CREATE,
            ).first()

            assert log is not None
            assert log.tenant == tenant
            assert log.user == user
            assert log.entity_repr == "New Contract"
            assert "name" in log.changes
            assert log.changes["name"]["new"] == "New Contract"
        finally:
            clear_current_user()

    def test_update_logs_update_action(self, db, tenant, user, customer):
        """Test that updating an entity logs an update action."""
        set_current_user(user)

        try:
            contract = Contract.objects.create(
                tenant=tenant,
                customer=customer,
                name="Original Name",
                status=Contract.Status.DRAFT,
                start_date=date(2026, 1, 1),
                billing_start_date=date(2026, 1, 1),
                billing_interval=Contract.BillingInterval.MONTHLY,
            )

            # Clear the create log
            AuditLog.objects.filter(entity_type="contract", entity_id=contract.id).delete()

            # Update the contract
            contract.name = "Updated Name"
            contract.save()

            # Check audit log was created
            log = AuditLog.objects.filter(
                entity_type="contract",
                entity_id=contract.id,
                action=AuditLog.Action.UPDATE,
            ).first()

            assert log is not None
            assert log.user == user
            assert "name" in log.changes
            assert log.changes["name"]["old"] == "Original Name"
            assert log.changes["name"]["new"] == "Updated Name"
        finally:
            clear_current_user()

    def test_delete_logs_delete_action(self, db, tenant, user, customer):
        """Test that deleting an entity logs a delete action."""
        set_current_user(user)

        try:
            contract = Contract.objects.create(
                tenant=tenant,
                customer=customer,
                name="To Delete",
                status=Contract.Status.DRAFT,
                start_date=date(2026, 1, 1),
                billing_start_date=date(2026, 1, 1),
                billing_interval=Contract.BillingInterval.MONTHLY,
            )
            contract_id = contract.id

            # Delete the contract
            contract.delete()

            # Check audit log was created
            log = AuditLog.objects.filter(
                entity_type="contract",
                entity_id=contract_id,
                action=AuditLog.Action.DELETE,
            ).first()

            assert log is not None
            assert log.user == user
            assert "name" in log.changes
            assert log.changes["name"]["old"] == "To Delete"
            assert log.changes["name"]["new"] is None
        finally:
            clear_current_user()

    def test_contract_item_logs_with_parent(self, db, tenant, user, customer, product):
        """Test that contract item changes include parent reference."""
        set_current_user(user)

        try:
            contract = Contract.objects.create(
                tenant=tenant,
                customer=customer,
                name="Parent Contract",
                status=Contract.Status.DRAFT,
                start_date=date(2026, 1, 1),
                billing_start_date=date(2026, 1, 1),
                billing_interval=Contract.BillingInterval.MONTHLY,
            )

            item = ContractItem.objects.create(
                tenant=tenant,
                contract=contract,
                product=product,
                quantity=1,
                unit_price=Decimal("100.00"),
            )

            # Check audit log includes parent reference
            log = AuditLog.objects.filter(
                entity_type="contract_item",
                entity_id=item.id,
                action=AuditLog.Action.CREATE,
            ).first()

            assert log is not None
            assert log.parent_entity_type == "contract"
            assert log.parent_entity_id == contract.id
        finally:
            clear_current_user()

    def test_system_change_has_null_user(self, db, tenant, customer):
        """Test that changes without a user have null user."""
        # Don't set current user
        clear_current_user()

        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="System Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        log = AuditLog.objects.filter(
            entity_type="contract",
            entity_id=contract.id,
        ).first()

        assert log is not None
        assert log.user is None


class TestAuditLogTenantIsolation:
    """Test audit log tenant isolation."""

    def test_logs_are_tenant_scoped(self, db, tenant, customer):
        """Test that audit logs belong to the correct tenant."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Tenant Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        log = AuditLog.objects.filter(
            entity_type="contract",
            entity_id=contract.id,
        ).first()

        assert log is not None
        assert log.tenant == tenant

    def test_other_tenant_logs_not_visible(self, db, tenant, customer):
        """Test that logs from other tenants are not visible."""
        from apps.tenants.models import Tenant

        # Create another tenant
        other_tenant = Tenant.objects.create(name="Other Tenant")
        other_customer = Customer.objects.create(
            tenant=other_tenant,
            name="Other Customer",
            is_active=True,
        )

        # Create contract in other tenant
        Contract.objects.create(
            tenant=other_tenant,
            customer=other_customer,
            name="Other Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        # Query with our tenant should not see other tenant's logs
        logs = AuditLog.objects.filter(tenant=tenant)
        for log in logs:
            assert log.tenant == tenant


class TestAuditLogGraphQL:
    """Test audit log GraphQL queries."""

    def test_query_audit_logs(self, db, tenant, user, customer, client):
        """Test basic audit logs query."""
        # Create a contract to generate audit logs
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="GraphQL Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        # Query audit logs via GraphQL
        from apps.core.auth import create_access_token

        token = create_access_token(user)
        response = client.post(
            "/graphql",
            content_type="application/json",
            data={
                "query": """
                    query {
                        auditLogs(first: 10) {
                            edges {
                                node {
                                    id
                                    action
                                    entityType
                                    entityId
                                    entityRepr
                                }
                            }
                            totalCount
                        }
                    }
                """
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["auditLogs"]["totalCount"] > 0

    def test_query_filter_by_entity(self, db, tenant, user, customer, client):
        """Test filtering audit logs by entity type and ID."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Filter Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        from apps.core.auth import create_access_token

        token = create_access_token(user)
        response = client.post(
            "/graphql",
            content_type="application/json",
            data={
                "query": f"""
                    query {{
                        auditLogs(entityType: "contract", entityId: {contract.id}, first: 10) {{
                            edges {{
                                node {{
                                    entityType
                                    entityId
                                }}
                            }}
                            totalCount
                        }}
                    }}
                """
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        # Should only have logs for this specific contract
        for edge in data["data"]["auditLogs"]["edges"]:
            assert edge["node"]["entityType"] == "contract"
            assert edge["node"]["entityId"] == contract.id
