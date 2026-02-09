"""Tests for invoice file upload: logo and reference PDF validation."""
import base64
import pytest
from unittest.mock import Mock

from django.conf import settings

from apps.core.context import Context
from apps.invoices.models import InvoiceTemplate, InvoiceTemplateReference
from config.schema import schema


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


def _b64(content: bytes) -> str:
    return base64.b64encode(content).decode()


@pytest.fixture
def template(db, tenant):
    return InvoiceTemplate.objects.create(
        tenant=tenant,
        accent_color="#2563eb",
    )


class TestLogoValidationSettings:
    """Test logo upload settings."""

    def test_accepts_png(self):
        assert ".png" in settings.ALLOWED_LOGO_EXTENSIONS

    def test_accepts_jpg(self):
        assert ".jpg" in settings.ALLOWED_LOGO_EXTENSIONS
        assert ".jpeg" in settings.ALLOWED_LOGO_EXTENSIONS

    def test_accepts_svg(self):
        assert ".svg" in settings.ALLOWED_LOGO_EXTENSIONS

    def test_rejects_gif(self):
        assert ".gif" not in settings.ALLOWED_LOGO_EXTENSIONS

    def test_rejects_pdf(self):
        assert ".pdf" not in settings.ALLOWED_LOGO_EXTENSIONS

    def test_max_size_is_5mb(self):
        assert settings.MAX_LOGO_SIZE == 5 * 1024 * 1024


class TestReferencePdfValidationSettings:
    def test_max_size_is_20mb(self):
        assert settings.MAX_REFERENCE_PDF_SIZE == 20 * 1024 * 1024


UPLOAD_LOGO_MUTATION = """
mutation($input: UploadLogoInput!) {
    uploadInvoiceLogo(input: $input) {
        success
        error
        data { hasLogo accentColor }
    }
}
"""

UPLOAD_REF_PDF_MUTATION = """
mutation($input: UploadReferencePdfInput!) {
    uploadInvoiceReferencePdf(input: $input) {
        success
        error
        data { references { originalFilename fileSize } }
    }
}
"""


class TestLogoUploadMutation:
    def test_valid_png_upload(self, db, tenant, user, template):
        ctx = make_context(user)
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "logo.png"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["uploadInvoiceLogo"]
        assert data["success"] is True
        assert data["data"]["hasLogo"] is True

    def test_valid_jpg_upload(self, db, tenant, user, template):
        ctx = make_context(user)
        content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "logo.jpg"}},
            ctx,
        )
        assert result.errors is None
        assert result.data["uploadInvoiceLogo"]["success"] is True

    def test_valid_svg_upload(self, db, tenant, user, template):
        ctx = make_context(user)
        content = b"<svg></svg>"
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "logo.svg"}},
            ctx,
        )
        assert result.errors is None
        assert result.data["uploadInvoiceLogo"]["success"] is True

    def test_rejects_gif_extension(self, db, tenant, user, template):
        ctx = make_context(user)
        content = b"GIF89a" + b"\x00" * 100
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "logo.gif"}},
            ctx,
        )
        data = result.data["uploadInvoiceLogo"]
        assert data["success"] is False
        assert ".gif" in data["error"]

    def test_rejects_oversized_file(self, db, tenant, user, template):
        ctx = make_context(user)
        # 5MB + 1 byte exceeds limit
        large = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 1)
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": _b64(large), "filename": "big.png"}},
            ctx,
        )
        data = result.data["uploadInvoiceLogo"]
        assert data["success"] is False
        assert "too large" in data["error"].lower()

    def test_rejects_invalid_base64(self, db, tenant, user, template):
        ctx = make_context(user)
        # Use truly invalid base64 (odd-length with padding issues)
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": "!!!===", "filename": "logo.png"}},
            ctx,
        )
        data = result.data["uploadInvoiceLogo"]
        assert data["success"] is False
        assert "base64" in data["error"].lower()

    def test_creates_template_if_not_exists(self, db, tenant, user):
        """Upload should create template record if none exists."""
        ctx = make_context(user)
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        result = run_graphql(
            UPLOAD_LOGO_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "logo.png"}},
            ctx,
        )
        assert result.data["uploadInvoiceLogo"]["success"] is True
        assert InvoiceTemplate.objects.filter(tenant=tenant).exists()


class TestReferencePdfUploadMutation:
    def test_valid_pdf_upload(self, db, tenant, user, template):
        ctx = make_context(user)
        content = b"%PDF-1.4" + b"\x00" * 100
        result = run_graphql(
            UPLOAD_REF_PDF_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "ref.pdf"}},
            ctx,
        )
        assert result.errors is None
        data = result.data["uploadInvoiceReferencePdf"]
        assert data["success"] is True
        refs = data["data"]["references"]
        assert len(refs) == 1
        assert refs[0]["originalFilename"] == "ref.pdf"
        assert refs[0]["fileSize"] == len(content)

    def test_rejects_non_pdf(self, db, tenant, user, template):
        ctx = make_context(user)
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = run_graphql(
            UPLOAD_REF_PDF_MUTATION,
            {"input": {"fileContent": _b64(content), "filename": "ref.png"}},
            ctx,
        )
        data = result.data["uploadInvoiceReferencePdf"]
        assert data["success"] is False
        assert "PDF" in data["error"]

    def test_rejects_oversized_pdf(self, db, tenant, user, template):
        ctx = make_context(user)
        large = b"%PDF-1.4" + b"\x00" * (20 * 1024 * 1024 + 1)
        result = run_graphql(
            UPLOAD_REF_PDF_MUTATION,
            {"input": {"fileContent": _b64(large), "filename": "big.pdf"}},
            ctx,
        )
        data = result.data["uploadInvoiceReferencePdf"]
        assert data["success"] is False
        assert "too large" in data["error"].lower()

    def test_multiple_references(self, db, tenant, user, template):
        """Multiple reference PDFs can be uploaded."""
        ctx = make_context(user)
        for i in range(3):
            content = b"%PDF-1.4" + bytes([i]) * 50
            result = run_graphql(
                UPLOAD_REF_PDF_MUTATION,
                {"input": {"fileContent": _b64(content), "filename": f"ref{i}.pdf"}},
                ctx,
            )
            assert result.data["uploadInvoiceReferencePdf"]["success"] is True

        assert InvoiceTemplateReference.objects.filter(template=template).count() == 3
