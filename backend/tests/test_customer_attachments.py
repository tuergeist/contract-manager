"""Tests for the upload_customer_attachment GraphQL mutation."""
import base64
from unittest.mock import Mock

import pytest
from django.conf import settings

from apps.core.context import Context
from apps.customers.models import Customer, CustomerAttachment
from apps.tenants.models import Role, Tenant, User
from config.schema import schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UPLOAD_MUTATION = """
    mutation UploadCustomerAttachment($input: UploadCustomerAttachmentInput!) {
        uploadCustomerAttachment(input: $input) {
            success
            error
            attachment {
                id
                originalFilename
                fileSize
                contentType
                description
                category
                uploadedAt
                uploadedByName
                downloadUrl
            }
        }
    }
"""


def run_graphql(query, variables, context):
    """Execute a GraphQL operation synchronously."""
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    """Build a Context object suitable for GraphQL testing."""
    request = Mock()
    return Context(request=request, user=user)


def _b64(content: bytes = b"hello world") -> str:
    """Return a base64-encoded string from raw bytes."""
    return base64.b64encode(content).decode()


def _upload_variables(customer_id, **overrides):
    """Build the standard mutation variables dict, with sensible defaults."""
    defaults = {
        "customerId": str(customer_id),
        "fileContent": _b64(),
        "filename": "report.pdf",
        "contentType": "application/pdf",
        "description": "",
        "category": "",
    }
    defaults.update(overrides)
    return {"input": defaults}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant(db):
    """Create a test tenant (post_save creates default roles)."""
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def user(db, tenant):
    """Create a user with Admin role (full permissions)."""
    u = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def viewer_user(db, tenant):
    """Create a user with Viewer role (customers.read only, no write)."""
    u = User.objects.create_user(
        email="viewer@example.com",
        password="testpass123",
        tenant=tenant,
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    u.roles.add(viewer_role)
    return u


@pytest.fixture
def customer(db, tenant):
    """Create a test customer belonging to the default tenant."""
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
    )


@pytest.fixture
def other_tenant(db):
    """Create a second, separate tenant."""
    return Tenant.objects.create(name="Other Company", currency="USD")


@pytest.fixture
def other_tenant_customer(db, other_tenant):
    """Create a customer belonging to the other tenant."""
    return Customer.objects.create(
        tenant=other_tenant,
        name="Other Customer",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Tests -- happy path
# ---------------------------------------------------------------------------


class TestUploadCustomerAttachmentSuccess:
    """Successful upload scenarios."""

    def test_upload_with_category(self, user, customer):
        """Category is persisted in the DB and returned in the response."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id, category="contract"),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is True
        assert data["error"] is None
        assert data["attachment"]["category"] == "contract"

        # Verify DB state
        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.category == "contract"

    def test_upload_without_category_defaults_to_empty(self, user, customer):
        """When no category is supplied the default empty string is stored."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is True
        assert data["attachment"]["category"] == ""

        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.category == ""

    def test_upload_with_description(self, user, customer):
        """Description is persisted and returned."""
        desc = "Q4 signed contract scan"
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id, description=desc),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is True
        assert data["attachment"]["description"] == desc

        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.description == desc

    def test_upload_returns_all_expected_fields(self, user, customer):
        """All CustomerAttachmentType fields are present and correct."""
        file_bytes = b"PDF-like-content"
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(
                customer.id,
                fileContent=_b64(file_bytes),
                filename="invoice.pdf",
                contentType="application/pdf",
                description="Monthly invoice",
                category="order",
            ),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is True

        att = data["attachment"]
        assert att["id"] is not None
        assert att["originalFilename"] == "invoice.pdf"
        assert att["fileSize"] == len(file_bytes)
        assert att["contentType"] == "application/pdf"
        assert att["description"] == "Monthly invoice"
        assert att["category"] == "order"
        assert att["uploadedAt"] is not None
        assert att["uploadedByName"] == user.email
        assert att["downloadUrl"] == f"/api/customer-attachments/{att['id']}/download/"

    def test_upload_different_allowed_extensions(self, user, customer):
        """Various allowed file types are accepted."""
        allowed_samples = [
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("photo.png", "image/png"),
            ("archive.zip", "application/zip"),
            ("data.csv", "text/csv"),
            ("image.jpg", "image/jpeg"),
        ]
        for filename, content_type in allowed_samples:
            result = run_graphql(
                UPLOAD_MUTATION,
                _upload_variables(customer.id, filename=filename, contentType=content_type),
                make_context(user),
            )
            assert result.errors is None
            data = result.data["uploadCustomerAttachment"]
            assert data["success"] is True, f"Expected success for {filename}"
            assert data["attachment"]["originalFilename"] == filename

    def test_upload_stores_correct_file_size(self, user, customer):
        """file_size matches the decoded byte length, not the base64 length."""
        raw = b"x" * 1234
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id, fileContent=_b64(raw)),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["attachment"]["fileSize"] == 1234


# ---------------------------------------------------------------------------
# Tests -- validation errors
# ---------------------------------------------------------------------------


class TestUploadCustomerAttachmentValidation:
    """Input validation and rejection scenarios."""

    def test_invalid_file_extension_rejected(self, user, customer):
        """Files with disallowed extensions are rejected."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id, filename="malware.exe"),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is False
        assert ".exe" in data["error"]
        assert data["attachment"] is None

        # No attachment created in DB
        assert CustomerAttachment.objects.count() == 0

    def test_multiple_disallowed_extensions(self, user, customer):
        """Several disallowed extensions are all rejected."""
        bad_names = ["script.js", "binary.bin", "page.html", "style.css", "app.py"]
        for filename in bad_names:
            result = run_graphql(
                UPLOAD_MUTATION,
                _upload_variables(customer.id, filename=filename),
                make_context(user),
            )
            assert result.errors is None
            data = result.data["uploadCustomerAttachment"]
            assert data["success"] is False, f"Expected rejection for {filename}"
            assert "not allowed" in data["error"]

    def test_file_too_large_rejected(self, user, customer):
        """Files exceeding MAX_UPLOAD_SIZE are rejected."""
        oversized = b"x" * (settings.MAX_UPLOAD_SIZE + 1)
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id, fileContent=_b64(oversized)),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is False
        assert "too large" in data["error"].lower()
        assert data["attachment"] is None
        assert CustomerAttachment.objects.count() == 0

    def test_file_exactly_at_limit_accepted(self, user, customer):
        """A file whose size equals MAX_UPLOAD_SIZE is accepted."""
        exact = b"x" * settings.MAX_UPLOAD_SIZE
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id, fileContent=_b64(exact)),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is True

    def test_invalid_base64_rejected(self, user, customer):
        """Garbage (non-base64) file_content returns a clear error."""
        result = run_graphql(
            UPLOAD_MUTATION,
            {"input": {
                "customerId": str(customer.id),
                "fileContent": "!!!not-valid-base64!!!",
                "filename": "report.pdf",
                "contentType": "application/pdf",
            }},
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is False
        assert "base64" in data["error"].lower()
        assert data["attachment"] is None
        assert CustomerAttachment.objects.count() == 0


# ---------------------------------------------------------------------------
# Tests -- permission / authorisation
# ---------------------------------------------------------------------------


class TestUploadCustomerAttachmentPermissions:
    """Permission and authorisation checks."""

    def test_viewer_cannot_upload(self, viewer_user, customer):
        """A user without customers.write receives a permission error."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id),
            make_context(viewer_user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is False
        assert "permission" in data["error"].lower()
        assert data["attachment"] is None
        assert CustomerAttachment.objects.count() == 0

    def test_unauthenticated_user_raises_error(self):
        """No user in context causes a GraphQL-level error (PermissionError)."""
        ctx = Context(request=Mock(), user=None)
        result = run_graphql(
            UPLOAD_MUTATION,
            {"input": {
                "customerId": "1",
                "fileContent": _b64(),
                "filename": "report.pdf",
                "contentType": "application/pdf",
            }},
            ctx,
        )

        # check_perm calls get_current_user which raises PermissionError
        # Strawberry surfaces this as a GraphQL error
        assert result.errors is not None


# ---------------------------------------------------------------------------
# Tests -- customer lookup / tenant isolation
# ---------------------------------------------------------------------------


class TestUploadCustomerAttachmentTenantIsolation:
    """Customer lookup and cross-tenant isolation."""

    def test_customer_not_found_returns_error(self, user):
        """A non-existent customer ID yields a clear error."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(999999),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is False
        assert data["error"] == "Customer not found"
        assert data["attachment"] is None

    def test_cannot_upload_to_other_tenants_customer(self, user, other_tenant_customer):
        """A user cannot upload attachments to a customer in another tenant."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(other_tenant_customer.id),
            make_context(user),
        )

        assert result.errors is None
        data = result.data["uploadCustomerAttachment"]
        assert data["success"] is False
        assert data["error"] == "Customer not found"
        assert data["attachment"] is None
        assert CustomerAttachment.objects.count() == 0

    def test_user_without_tenant_returns_error(self, db):
        """A user with no tenant assigned gets a specific error."""
        u = User.objects.create_user(
            email="notenant@example.com",
            password="testpass123",
            tenant=None,
        )
        result = run_graphql(
            UPLOAD_MUTATION,
            {"input": {
                "customerId": "1",
                "fileContent": _b64(),
                "filename": "report.pdf",
                "contentType": "application/pdf",
            }},
            make_context(u),
        )

        # get_current_user in check_perm will raise because user lacks any
        # role and therefore has no permission; alternatively the tenant
        # guard fires. Either way, it should not succeed.
        if result.errors is None:
            data = result.data["uploadCustomerAttachment"]
            assert data["success"] is False
        # If it raised a GraphQL error that is also acceptable
        # (permission denied before reaching the tenant check)


# ---------------------------------------------------------------------------
# Tests -- DB record integrity
# ---------------------------------------------------------------------------


class TestUploadCustomerAttachmentDBIntegrity:
    """Verify that the database record is correctly written."""

    def test_attachment_linked_to_correct_customer(self, user, customer):
        """The attachment FK points to the right customer."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id),
            make_context(user),
        )

        data = result.data["uploadCustomerAttachment"]
        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.customer_id == customer.id

    def test_attachment_linked_to_correct_tenant(self, user, customer):
        """The attachment inherits the user's tenant."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id),
            make_context(user),
        )

        data = result.data["uploadCustomerAttachment"]
        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.tenant_id == user.tenant_id

    def test_uploaded_by_is_current_user(self, user, customer):
        """uploaded_by FK is set to the authenticated user."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id),
            make_context(user),
        )

        data = result.data["uploadCustomerAttachment"]
        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.uploaded_by_id == user.id

    def test_file_is_saved_to_storage(self, user, customer):
        """The FileField is populated after upload."""
        result = run_graphql(
            UPLOAD_MUTATION,
            _upload_variables(customer.id),
            make_context(user),
        )

        data = result.data["uploadCustomerAttachment"]
        att = CustomerAttachment.objects.get(id=data["attachment"]["id"])
        assert att.file is not None
        assert att.file.name != ""
