"""Tests for PDF contract analysis service and GraphQL endpoints."""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.contracts.models import Contract, ContractAttachment, ContractItem, ContractAmendment
from apps.contracts.services.pdf_analysis import (
    ComparisonItem,
    ExtractedLineItem,
    ExtractedMetadata,
    PdfAnalysisResult,
    ProductMatch,
    _compare_metadata,
    _match_and_compare,
    _match_products,
    _parse_line_items,
    _parse_metadata,
    analyze_pdf_attachment,
)
from apps.core.context import Context
from apps.customers.models import Customer
from apps.products.models import Product
from apps.tenants.models import Role, Tenant, User
from config.schema import schema


# --- Fixtures ---


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        email="pdf-test@example.com", password="testpass123", tenant=tenant
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(tenant=tenant, name="Test Customer", is_active=True)


@pytest.fixture
def product_hosting(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Hosting + Maintenance",
        netsuite_item_name="Hosting + Maintenance : Software Maintenance",
        is_active=True,
    )


@pytest.fixture
def product_license(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Software License",
        netsuite_item_name="Software License : SaaS",
        is_active=True,
    )


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Test Contract",
        status=Contract.Status.DRAFT,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
    )


@pytest.fixture
def active_contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Active Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
    )


@pytest.fixture
def attachment(db, tenant, contract):
    att = ContractAttachment.objects.create(
        tenant=tenant,
        contract=contract,
        original_filename="order_confirmation.pdf",
        file_size=12345,
        content_type="application/pdf",
    )
    # Mock file field
    att.file = MagicMock()
    att.file.read.return_value = b"%PDF-1.4 fake content"
    att.save = MagicMock()
    return att


SAMPLE_CLAUDE_RESPONSE = {
    "line_items": [
        {
            "description": "Hosting + Maintenance : Software Maintenance",
            "quantity": 2,
            "unit_price": "150.00",
            "price_period": "monthly",
            "is_one_off": False,
        },
        {
            "description": "Software License : SaaS",
            "quantity": 5,
            "unit_price": "49.99",
            "price_period": "monthly",
            "is_one_off": False,
        },
        {
            "description": "Setup Fee",
            "quantity": 1,
            "unit_price": "500.00",
            "price_period": "monthly",
            "is_one_off": True,
        },
        {
            "description": "Volume discount",
            "quantity": 1,
            "unit_price": "-100.00",
            "price_period": "monthly",
            "is_one_off": False,
        },
    ],
    "metadata": {
        "po_number": "PO-2025-001",
        "order_confirmation_number": "AB-12345",
        "min_duration_months": 36,
    },
}


# --- Unit tests: parsing ---


class TestParseLineItems:
    def test_parses_recurring_items(self):
        items = _parse_line_items(SAMPLE_CLAUDE_RESPONSE["line_items"])
        assert len(items) == 4
        assert items[0].description == "Hosting + Maintenance : Software Maintenance"
        assert items[0].quantity == 2
        assert items[0].unit_price == Decimal("150.00")
        assert items[0].price_period == "monthly"
        assert items[0].is_one_off is False

    def test_parses_one_off_items(self):
        items = _parse_line_items(SAMPLE_CLAUDE_RESPONSE["line_items"])
        setup = items[2]
        assert setup.description == "Setup Fee"
        assert setup.is_one_off is True
        assert setup.unit_price == Decimal("500.00")

    def test_parses_discount_as_negative_line_item(self):
        items = _parse_line_items(SAMPLE_CLAUDE_RESPONSE["line_items"])
        discount = items[3]
        assert discount.description == "Volume discount"
        assert discount.unit_price == Decimal("-100.00")
        assert discount.quantity == 1

    def test_handles_empty_list(self):
        assert _parse_line_items([]) == []

    def test_skips_malformed_items(self):
        items = _parse_line_items([
            {"description": "Good item", "quantity": 1, "unit_price": "10.00"},
            {"description": "Bad item", "quantity": "not_a_number", "unit_price": "abc"},
        ])
        assert len(items) == 1
        assert items[0].description == "Good item"


class TestParseMetadata:
    def test_parses_all_fields(self):
        meta = _parse_metadata(SAMPLE_CLAUDE_RESPONSE["metadata"])
        assert meta.po_number == "PO-2025-001"
        assert meta.order_confirmation_number == "AB-12345"
        assert meta.min_duration_months == 36

    def test_handles_null_fields(self):
        meta = _parse_metadata(
            {"po_number": None, "order_confirmation_number": None, "min_duration_months": None},
        )
        assert meta.po_number is None
        assert meta.order_confirmation_number is None
        assert meta.min_duration_months is None


# --- Unit tests: product matching ---


class TestProductMatching:
    def test_exact_netsuite_match(self, tenant, product_hosting, product_license):
        items = [
            ExtractedLineItem(
                description="Hosting + Maintenance : Software Maintenance",
                quantity=1,
                unit_price=Decimal("100"),
                price_period="monthly",
            )
        ]
        matches = _match_products(items, tenant)
        assert matches[0] is not None
        assert matches[0].product_id == product_hosting.id
        assert matches[0].confidence == 1.0

    def test_fuzzy_match_high_confidence(self, tenant, product_hosting, product_license):
        items = [
            ExtractedLineItem(
                description="Hosting and Maintenance",
                quantity=1,
                unit_price=Decimal("100"),
                price_period="monthly",
            )
        ]
        matches = _match_products(items, tenant)
        assert matches[0] is not None
        assert matches[0].product_id == product_hosting.id
        assert matches[0].confidence >= 0.8

    def test_no_match_below_threshold(self, tenant, product_hosting):
        items = [
            ExtractedLineItem(
                description="Completely Unrelated Service XYZ",
                quantity=1,
                unit_price=Decimal("100"),
                price_period="monthly",
            )
        ]
        matches = _match_products(items, tenant)
        assert matches[0] is None

    def test_discount_items_skipped(self, tenant, product_hosting):
        items = [
            ExtractedLineItem(
                description="Volume discount",
                quantity=1,
                unit_price=Decimal("-100"),
                price_period="monthly",
            )
        ]
        matches = _match_products(items, tenant)
        assert matches[0] is None


# --- Unit tests: comparison ---


class TestCompareMetadata:
    def test_detects_differences(self, contract):
        contract.po_number = "OLD-PO"
        meta = ExtractedMetadata(po_number="NEW-PO")
        comparisons = _compare_metadata(meta, contract)
        po_comp = next(c for c in comparisons if c.field_name == "po_number")
        assert po_comp.differs is True
        assert po_comp.extracted_value == "NEW-PO"
        assert po_comp.current_value == "OLD-PO"

    def test_detects_no_difference(self, contract):
        contract.po_number = "SAME-PO"
        meta = ExtractedMetadata(po_number="SAME-PO")
        comparisons = _compare_metadata(meta, contract)
        po_comp = next(c for c in comparisons if c.field_name == "po_number")
        assert po_comp.differs is False

    def test_skips_null_extracted(self, contract):
        meta = ExtractedMetadata()
        comparisons = _compare_metadata(meta, contract)
        assert len(comparisons) == 0


class TestMatchAndCompare:
    def test_marks_existing_items(self, contract, tenant, product_hosting):
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product_hosting,
            quantity=2,
            unit_price=Decimal("150.00"),
            price_period="monthly",
        )
        items = [
            ExtractedLineItem(
                description="Hosting + Maintenance : Software Maintenance",
                quantity=2,
                unit_price=Decimal("150.00"),
                price_period="monthly",
            )
        ]
        meta = ExtractedMetadata()
        results = _match_and_compare(items, meta, contract, tenant)
        assert len(results) == 1
        assert results[0].status == "existing"
        assert results[0].price_differs is False

    def test_marks_new_items(self, contract, tenant, product_hosting):
        items = [
            ExtractedLineItem(
                description="Brand New Service",
                quantity=1,
                unit_price=Decimal("999.00"),
                price_period="monthly",
            )
        ]
        meta = ExtractedMetadata()
        results = _match_and_compare(items, meta, contract, tenant)
        assert len(results) == 1
        assert results[0].status == "new"

    def test_detects_price_differences(self, contract, tenant, product_hosting):
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product_hosting,
            quantity=2,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        items = [
            ExtractedLineItem(
                description="Hosting + Maintenance : Software Maintenance",
                quantity=2,
                unit_price=Decimal("150.00"),
                price_period="monthly",
            )
        ]
        meta = ExtractedMetadata()
        results = _match_and_compare(items, meta, contract, tenant)
        assert results[0].status == "existing"
        assert results[0].price_differs is True


# --- Unit tests: full analysis with mocked API ---


class TestAnalyzePdfAttachment:
    @patch("apps.contracts.services.pdf_analysis.settings")
    def test_error_when_no_api_key(self, mock_settings, attachment, tenant):
        mock_settings.ANTHROPIC_API_KEY = ""
        result = analyze_pdf_attachment(attachment, tenant)
        assert result.error == "PDF analysis is not configured"

    def test_error_when_not_pdf(self, tenant, contract):
        att = MagicMock(spec=ContractAttachment)
        att.original_filename = "data.xlsx"
        att.contract = contract
        with patch("apps.contracts.services.pdf_analysis.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            result = analyze_pdf_attachment(att, tenant)
        assert result.error == "Only PDF files can be analyzed"

    @patch("apps.contracts.services.pdf_analysis.settings")
    def test_successful_analysis(self, mock_settings, attachment, tenant, product_hosting, product_license):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(SAMPLE_CLAUDE_RESPONSE))]

        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_module.Anthropic.return_value = mock_client

        import sys
        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            result = analyze_pdf_attachment(attachment, tenant)

        assert result.error is None
        assert len(result.items) == 4
        assert result.metadata.po_number == "PO-2025-001"
        # Discount is now a line item with negative price, not metadata
        discount_items = [i for i in result.items if i.extracted.unit_price < 0]
        assert len(discount_items) == 1
        assert discount_items[0].product_match is None


# --- Integration tests: GraphQL ---


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    request = Mock()
    return Context(request=request, user=user)


ANALYZE_QUERY = """
    query AnalyzePdf($attachmentId: ID!) {
        analyzePdfAttachment(attachmentId: $attachmentId) {
            error
            items {
                extracted {
                    description
                    quantity
                    unitPrice
                    pricePeriod
                    isOneOff
                }
                productMatch {
                    productId
                    productName
                    confidence
                }
                status
                existingItemId
                priceDiffers
            }
            metadata {
                poNumber
                orderConfirmationNumber
                minDurationMonths
            }
            metadataComparisons {
                fieldName
                extractedValue
                currentValue
                differs
            }
        }
    }
"""


IMPORT_MUTATION = """
    mutation ImportPdf($input: ImportPdfAnalysisInput!) {
        importPdfAnalysis(input: $input) {
            success
            error
            createdItemsCount
        }
    }
"""


class TestAnalyzeGraphQL:
    @patch("apps.contracts.services.pdf_analysis.settings")
    def test_analyze_attachment_not_found(self, mock_settings, user):
        mock_settings.ANTHROPIC_API_KEY = "test-key"
        ctx = make_context(user)
        result = run_graphql(ANALYZE_QUERY, {"attachmentId": "99999"}, ctx)
        assert result.errors is None
        data = result.data["analyzePdfAttachment"]
        assert data["error"] == "Attachment not found"

    def test_analyze_success(
        self, user, tenant, contract, product_hosting, product_license
    ):
        # Create a real attachment
        att = ContractAttachment.objects.create(
            tenant=tenant,
            contract=contract,
            original_filename="test.pdf",
            file_size=100,
            content_type="application/pdf",
        )

        # Mock the entire analyze_pdf_attachment service to bypass file I/O and API
        from apps.contracts.services.pdf_analysis import (
            PdfAnalysisResult as ServiceResult,
            ComparisonItem as ServiceComp,
            ExtractedLineItem as ServiceItem,
            ExtractedMetadata as ServiceMeta,
            MetadataComparison as ServiceMetaComp,
            ProductMatch as ServiceMatch,
        )

        mock_result = ServiceResult(
            items=[
                ServiceComp(
                    extracted=ServiceItem(
                        description="Hosting + Maintenance",
                        quantity=2,
                        unit_price=Decimal("150.00"),
                        price_period="monthly",
                    ),
                    product_match=ServiceMatch(
                        product_id=product_hosting.id,
                        product_name=product_hosting.name,
                        confidence=1.0,
                    ),
                    status="new",
                ),
            ],
            metadata=ServiceMeta(
                po_number="PO-2025-001",
                order_confirmation_number="AB-12345",
                min_duration_months=36,
            ),
            metadata_comparisons=[
                ServiceMetaComp(
                    field_name="po_number",
                    extracted_value="PO-2025-001",
                    current_value=None,
                    differs=True,
                ),
            ],
        )

        with patch(
            "apps.contracts.services.pdf_analysis.analyze_pdf_attachment",
            return_value=mock_result,
        ):
            ctx = make_context(user)
            result = run_graphql(ANALYZE_QUERY, {"attachmentId": str(att.id)}, ctx)

        assert result.errors is None
        data = result.data["analyzePdfAttachment"]
        assert data["error"] is None
        assert len(data["items"]) == 1
        assert data["metadata"]["poNumber"] == "PO-2025-001"


class TestImportMutationGraphQL:
    def test_import_creates_items(self, user, contract, tenant, product_hosting):
        ctx = make_context(user)
        result = run_graphql(
            IMPORT_MUTATION,
            {
                "input": {
                    "contractId": str(contract.id),
                    "items": [
                        {
                            "description": "Hosting + Maintenance",
                            "quantity": 2,
                            "unitPrice": "150.00",
                            "pricePeriod": "monthly",
                            "isOneOff": False,
                            "productId": str(product_hosting.id),
                        }
                    ],
                    "metadata": {
                        "poNumber": "PO-2025-001",
                        "minDurationMonths": 36,
                    },
                }
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["importPdfAnalysis"]
        assert data["success"] is True
        assert data["createdItemsCount"] == 1

        # Verify DB
        items = ContractItem.objects.filter(contract=contract)
        assert items.count() == 1
        assert items.first().product_id == product_hosting.id
        assert items.first().unit_price == Decimal("150.00")

        contract.refresh_from_db()
        assert contract.po_number == "PO-2025-001"
        assert contract.min_duration_months == 36

    def test_import_creates_amendments_for_active_contract(
        self, user, active_contract, tenant, product_hosting
    ):
        ctx = make_context(user)
        result = run_graphql(
            IMPORT_MUTATION,
            {
                "input": {
                    "contractId": str(active_contract.id),
                    "items": [
                        {
                            "description": "Hosting Service",
                            "quantity": 1,
                            "unitPrice": "100.00",
                            "pricePeriod": "monthly",
                            "isOneOff": False,
                            "productId": str(product_hosting.id),
                        }
                    ],
                }
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["importPdfAnalysis"]
        assert data["success"] is True

        # Verify amendment created
        amendments = ContractAmendment.objects.filter(contract=active_contract)
        assert amendments.count() == 1
        assert "PDF import" in amendments.first().description

    def test_import_updates_metadata_only(self, user, contract, tenant):
        ctx = make_context(user)
        result = run_graphql(
            IMPORT_MUTATION,
            {
                "input": {
                    "contractId": str(contract.id),
                    "items": [],
                    "metadata": {
                        "poNumber": "PO-999",
                        "minDurationMonths": 24,
                    },
                }
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["importPdfAnalysis"]
        assert data["success"] is True
        assert data["createdItemsCount"] == 0

        contract.refresh_from_db()
        assert contract.po_number == "PO-999"
        assert contract.min_duration_months == 24

    def test_import_contract_not_found(self, user):
        ctx = make_context(user)
        result = run_graphql(
            IMPORT_MUTATION,
            {
                "input": {
                    "contractId": "99999",
                    "items": [],
                }
            },
            ctx,
        )
        assert result.errors is None
        data = result.data["importPdfAnalysis"]
        assert data["success"] is False
        assert data["error"] == "Contract not found"
