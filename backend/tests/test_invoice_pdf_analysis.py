"""Tests for invoice PDF analysis service."""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.core.context import Context
from apps.invoices.models import InvoiceTemplateReference
from apps.invoices.pdf_analysis import analyze_reference, extract_from_invoice_pdf
from config.schema import schema

pytestmark = pytest.mark.django_db


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


SAMPLE_EXTRACTION_RESULT = {
    "legal_data": {
        "company_name": "Muster GmbH",
        "street": "Musterstraße 1",
        "zip_code": "80331",
        "city": "München",
        "country": "Deutschland",
        "tax_number": "143/456/78901",
        "vat_id": "DE123456789",
        "commercial_register_court": "Amtsgericht München",
        "commercial_register_number": "HRB 12345",
        "managing_directors": ["Max Mustermann", "Erika Musterfrau"],
        "bank_name": "Deutsche Bank",
        "iban": "DE89370400440532013000",
        "bic": "COBADEFFXXX",
        "phone": "+49 89 12345678",
        "email": "info@muster.de",
        "website": "https://www.muster.de",
        "share_capital": "25.000,00 EUR",
        "default_tax_rate": "19.00",
    },
    "design": {
        "accent_color": "#1a5276",
        "header_text": "Ihr Partner für Software",
        "footer_text": "Zahlbar innerhalb von 14 Tagen",
    },
    "layout": {
        "logo_position": "top-left",
        "footer_columns": 3,
        "description": "Classic two-column layout with logo top-left",
    },
}


@pytest.fixture
def tenant():
    from apps.tenants.models import Tenant

    return Tenant.objects.create(name="Test Tenant")


@pytest.fixture
def template(tenant):
    from apps.invoices.models import InvoiceTemplate

    return InvoiceTemplate.objects.create(tenant=tenant)


@pytest.fixture
def reference(template):
    from django.core.files.base import ContentFile

    ref = InvoiceTemplateReference(
        template=template,
        original_filename="test-invoice.pdf",
        file_size=1024,
    )
    ref.file.save("test.pdf", ContentFile(b"%PDF-1.4 fake content"), save=True)
    return ref


class TestExtractFromInvoicePdf:
    """Tests for the extract_from_invoice_pdf function."""

    def test_parses_valid_json_response(self):
        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(SAMPLE_EXTRACTION_RESULT))]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = extract_from_invoice_pdf(b"%PDF-1.4 fake")

        assert result["legal_data"]["company_name"] == "Muster GmbH"
        assert result["legal_data"]["vat_id"] == "DE123456789"
        assert result["design"]["accent_color"] == "#1a5276"
        assert result["layout"]["logo_position"] == "top-left"

    def test_strips_markdown_code_fences(self):
        wrapped = "```json\n" + json.dumps(SAMPLE_EXTRACTION_RESULT) + "\n```"
        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=wrapped)]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = extract_from_invoice_pdf(b"%PDF-1.4 fake")

        assert result["legal_data"]["company_name"] == "Muster GmbH"

    def test_raises_on_invalid_json(self):
        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="This is not JSON")]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                with pytest.raises(json.JSONDecodeError):
                    extract_from_invoice_pdf(b"%PDF-1.4 fake")

    def test_handles_null_fields(self):
        """Extraction result with null fields should be valid."""
        result_with_nulls = {
            "legal_data": {
                "company_name": "Test GmbH",
                "street": "Test St 1",
                "zip_code": "12345",
                "city": "Berlin",
                "country": "Deutschland",
                "tax_number": None,
                "vat_id": "DE999999999",
                "commercial_register_court": None,
                "commercial_register_number": None,
                "managing_directors": ["Test Person"],
                "bank_name": None,
                "iban": None,
                "bic": None,
                "phone": None,
                "email": None,
                "website": None,
                "share_capital": None,
                "default_tax_rate": "19.00",
            },
            "design": {"accent_color": None, "header_text": None, "footer_text": None},
            "layout": {"logo_position": None, "footer_columns": None, "description": None},
        }
        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(result_with_nulls))]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = extract_from_invoice_pdf(b"%PDF-1.4 fake")

        assert result["legal_data"]["company_name"] == "Test GmbH"
        assert result["legal_data"]["tax_number"] is None
        assert result["design"]["accent_color"] is None


class TestAnalyzeReference:
    """Tests for the analyze_reference function."""

    def test_successful_extraction_stores_results(self, reference):
        with patch("apps.invoices.pdf_analysis.extract_from_invoice_pdf") as mock_extract:
            mock_extract.return_value = SAMPLE_EXTRACTION_RESULT
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = analyze_reference(reference)

        reference.refresh_from_db()
        assert reference.extraction_status == "completed"
        assert reference.extracted_data == SAMPLE_EXTRACTION_RESULT
        assert result["legal_data"]["company_name"] == "Muster GmbH"

    def test_failed_extraction_sets_failed_status(self, reference):
        with patch("apps.invoices.pdf_analysis.extract_from_invoice_pdf") as mock_extract:
            mock_extract.side_effect = Exception("API error")
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = analyze_reference(reference)

        reference.refresh_from_db()
        assert reference.extraction_status == "failed"
        assert "error" in result
        assert "API error" in result["error"]

    def test_json_parse_error_sets_failed_status(self, reference):
        with patch("apps.invoices.pdf_analysis.extract_from_invoice_pdf") as mock_extract:
            mock_extract.side_effect = json.JSONDecodeError("bad json", "", 0)
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = analyze_reference(reference)

        reference.refresh_from_db()
        assert reference.extraction_status == "failed"
        assert "error" in result

    def test_missing_api_key_sets_failed_status(self, reference):
        with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            result = analyze_reference(reference)

        reference.refresh_from_db()
        assert reference.extraction_status == "failed"
        assert "error" in result
        assert "API key" in result["error"]

    def test_file_read_error_sets_failed_status(self, reference):
        with patch.object(reference.file, "open", side_effect=IOError("disk error")):
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = analyze_reference(reference)

        reference.refresh_from_db()
        assert reference.extraction_status == "failed"
        assert "error" in result

    def test_re_extraction_overwrites_previous_results(self, reference):
        # First extraction
        reference.extracted_data = {"old": "data"}
        reference.extraction_status = "completed"
        reference.save()

        with patch("apps.invoices.pdf_analysis.extract_from_invoice_pdf") as mock_extract:
            mock_extract.return_value = SAMPLE_EXTRACTION_RESULT
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                analyze_reference(reference)

        reference.refresh_from_db()
        assert reference.extraction_status == "completed"
        assert reference.extracted_data == SAMPLE_EXTRACTION_RESULT
        assert "old" not in reference.extracted_data


ANALYZE_MUTATION = """
    mutation AnalyzeReferencePdf($referenceId: Int!) {
        analyzeReferencePdf(referenceId: $referenceId) {
            success
            error
            extractedData
        }
    }
"""

PDF_ANALYSIS_AVAILABLE_QUERY = """
    query { pdfAnalysisAvailable }
"""


class TestAnalyzeReferencePdfMutation:
    """Tests for the analyzeReferencePdf GraphQL mutation."""

    def test_successful_extraction(self, reference, user):
        ctx = make_context(user)
        with patch("apps.invoices.pdf_analysis.extract_from_invoice_pdf") as mock_extract:
            mock_extract.return_value = SAMPLE_EXTRACTION_RESULT
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = run_graphql(
                    ANALYZE_MUTATION,
                    {"referenceId": reference.id},
                    ctx,
                )

        assert result.errors is None
        data = result.data["analyzeReferencePdf"]
        assert data["success"] is True
        assert data["error"] is None
        assert data["extractedData"]["legal_data"]["company_name"] == "Muster GmbH"

    def test_reference_not_found(self, user):
        ctx = make_context(user)
        result = run_graphql(ANALYZE_MUTATION, {"referenceId": 9999}, ctx)
        assert result.errors is None
        data = result.data["analyzeReferencePdf"]
        assert data["success"] is False
        assert "not found" in data["error"]

    def test_extraction_failure_returns_error(self, reference, user):
        ctx = make_context(user)
        with patch("apps.invoices.pdf_analysis.extract_from_invoice_pdf") as mock_extract:
            mock_extract.side_effect = Exception("Claude API down")
            with patch("apps.invoices.pdf_analysis.settings") as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                result = run_graphql(
                    ANALYZE_MUTATION,
                    {"referenceId": reference.id},
                    ctx,
                )

        assert result.errors is None
        data = result.data["analyzeReferencePdf"]
        assert data["success"] is False
        assert "Claude API" in data["error"]

    def test_permission_denied_without_role(self, reference, tenant):
        from apps.tenants.models import User

        viewer = User.objects.create_user(
            email="viewer@test.com", password="test123", tenant=tenant
        )
        # No roles assigned → no settings.write permission
        ctx = make_context(viewer)
        result = run_graphql(
            ANALYZE_MUTATION, {"referenceId": reference.id}, ctx
        )
        # Should get a permission error
        assert result.errors is not None or (
            result.data["analyzeReferencePdf"]["success"] is False
        )


class TestPdfAnalysisAvailableQuery:
    """Tests for the pdfAnalysisAvailable query field."""

    def test_returns_true_when_key_configured(self, user):
        ctx = make_context(user)
        with patch("apps.invoices.schema.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            result = run_graphql(PDF_ANALYSIS_AVAILABLE_QUERY, {}, ctx)

        assert result.errors is None
        assert result.data["pdfAnalysisAvailable"] is True

    def test_returns_false_when_key_not_configured(self, user):
        ctx = make_context(user)
        with patch("apps.invoices.schema.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            result = run_graphql(PDF_ANALYSIS_AVAILABLE_QUERY, {}, ctx)

        assert result.errors is None
        assert result.data["pdfAnalysisAvailable"] is False
