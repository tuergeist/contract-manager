"""Service for analyzing contract PDFs using the Claude API."""

import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache as django_cache
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

PDF_EXTRACTION_CACHE_TTL = 60 * 60 * 24  # 24 hours

from apps.contracts.models import Contract, ContractAttachment, ContractItem
from apps.products.models import Product
from apps.tenants.models import Tenant


@dataclass
class ExtractedLineItem:
    """A line item extracted from a PDF."""

    description: str
    quantity: int
    unit_price: Decimal
    price_period: str  # monthly, quarterly, annual, etc.
    is_one_off: bool = False


@dataclass
class ExtractedMetadata:
    """Contract metadata extracted from a PDF."""

    po_number: str | None = None
    order_confirmation_number: str | None = None
    min_duration_months: int | None = None


@dataclass
class ProductMatch:
    """Result of fuzzy-matching an extracted item to a product."""

    product_id: int
    product_name: str
    confidence: float  # 0.0 to 1.0


@dataclass
class ComparisonItem:
    """An extracted item compared against existing contract items."""

    extracted: ExtractedLineItem
    product_match: ProductMatch | None = None
    status: str = "new"  # "new" or "existing"
    existing_item_id: int | None = None
    price_differs: bool = False


@dataclass
class MetadataComparison:
    """Comparison of extracted vs existing metadata."""

    field_name: str
    extracted_value: str | None
    current_value: str | None
    differs: bool = False


@dataclass
class PdfAnalysisResult:
    """Full result of analyzing a PDF attachment."""

    items: list[ComparisonItem] = field(default_factory=list)
    metadata: ExtractedMetadata = field(default_factory=ExtractedMetadata)
    metadata_comparisons: list[MetadataComparison] = field(default_factory=list)
    error: str | None = None


EXTRACTION_PROMPT = """\
Analyze this PDF document (a purchase order confirmation or contract document) and extract structured data.

Return a JSON object with exactly this structure:
{
  "line_items": [
    {
      "description": "Item description/name",
      "quantity": 1,
      "unit_price": "123.45",
      "price_period": "monthly",
      "is_one_off": false
    }
  ],
  "metadata": {
    "po_number": "PO-12345 or null",
    "order_confirmation_number": "AB-12345 or null",
    "min_duration_months": 36
  }
}

Rules:
- price_period must be one of: "monthly", "quarterly", "semi_annual", "annual"
- For one-time fees (setup, installation, etc.), set is_one_off to true
- unit_price is the price per single unit per period (NOT total)
- quantity is the number of units
- Discounts (negative amounts, "discount", "Rabatt", "Nachlass") SHALL be included as regular \
line_items with a NEGATIVE unit_price and quantity 1. Keep the original description.
- If a field is not found in the document, use null
- min_duration_months should be an integer (e.g., 36 for "36 months" or "3 years")
- Support both English and German documents
- Return ONLY valid JSON, no markdown formatting
"""


def _get_cache_key(attachment: ContractAttachment) -> str:
    """Build a cache key from attachment ID and file size."""
    return f"pdf_extraction:{attachment.id}:{attachment.file_size}"


def _extract_from_pdf(pdf_data: bytes) -> dict:
    """Send PDF to Claude API and return parsed JSON. No caching here."""
    import anthropic

    pdf_base64 = base64.standard_b64encode(pdf_data).decode("utf-8")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    return json.loads(response_text)


def analyze_pdf_attachment(
    attachment: ContractAttachment,
    tenant: Tenant,
) -> PdfAnalysisResult:
    """Analyze a PDF attachment and return extraction results with product matches."""
    if not settings.ANTHROPIC_API_KEY:
        return PdfAnalysisResult(error="PDF analysis is not configured")

    if not attachment.original_filename.lower().endswith(".pdf"):
        return PdfAnalysisResult(error="Only PDF files can be analyzed")

    # Check cache for extraction result
    cache_key = _get_cache_key(attachment)
    cached_data = django_cache.get(cache_key)

    if cached_data is not None:
        logger.info("PDF extraction cache hit for attachment %s", attachment.id)
        data = cached_data
    else:
        # Read PDF
        try:
            pdf_data = attachment.file.read()
        except Exception as e:
            return PdfAnalysisResult(error=f"Failed to read PDF file: {e}")

        # Call Claude API
        try:
            data = _extract_from_pdf(pdf_data)
        except json.JSONDecodeError as e:
            return PdfAnalysisResult(error=f"Failed to parse extraction result: {e}")
        except Exception as e:
            return PdfAnalysisResult(error=f"Claude API error: {e}")

        # Cache the raw extraction (not product matches — those depend on current catalog)
        django_cache.set(cache_key, data, PDF_EXTRACTION_CACHE_TTL)
        logger.info("PDF extraction cached for attachment %s", attachment.id)

    # Build extracted items
    extracted_items = _parse_line_items(data.get("line_items", []))
    extracted_metadata = _parse_metadata(data.get("metadata", {}))

    # Match products (always fresh against current catalog)
    contract = attachment.contract
    comparison_items = _match_and_compare(
        extracted_items, extracted_metadata, contract, tenant
    )

    # Build metadata comparisons
    metadata_comparisons = _compare_metadata(extracted_metadata, contract)

    return PdfAnalysisResult(
        items=comparison_items,
        metadata=extracted_metadata,
        metadata_comparisons=metadata_comparisons,
    )


def _parse_line_items(raw_items: list[dict]) -> list[ExtractedLineItem]:
    """Parse raw JSON line items into dataclasses."""
    items = []
    for raw in raw_items:
        try:
            items.append(
                ExtractedLineItem(
                    description=str(raw.get("description", "")),
                    quantity=int(raw.get("quantity", 1)),
                    unit_price=Decimal(str(raw.get("unit_price", "0"))),
                    price_period=str(raw.get("price_period", "monthly")),
                    is_one_off=bool(raw.get("is_one_off", False)),
                )
            )
        except (ValueError, TypeError):
            continue
    return items


def _parse_metadata(raw_metadata: dict) -> ExtractedMetadata:
    """Parse raw JSON metadata into a dataclass."""
    metadata = ExtractedMetadata(
        po_number=raw_metadata.get("po_number"),
        order_confirmation_number=raw_metadata.get("order_confirmation_number"),
    )

    min_dur = raw_metadata.get("min_duration_months")
    if min_dur is not None:
        try:
            metadata.min_duration_months = int(min_dur)
        except (ValueError, TypeError):
            pass

    return metadata


def _match_products(
    items: list[ExtractedLineItem], tenant: Tenant
) -> dict[int, ProductMatch | None]:
    """Fuzzy-match extracted items against tenant's product catalog."""
    products = list(Product.objects.filter(tenant=tenant, is_active=True))
    matches: dict[int, ProductMatch | None] = {}

    for idx, item in enumerate(items):
        # Skip product matching for discount lines (negative price)
        if item.unit_price < 0:
            matches[idx] = None
            continue

        best_match: ProductMatch | None = None
        best_score = 0.0

        # First try exact match by netsuite_item_name
        for product in products:
            if (
                product.netsuite_item_name
                and product.netsuite_item_name.lower() == item.description.lower()
            ):
                best_match = ProductMatch(
                    product_id=product.id,
                    product_name=product.name,
                    confidence=1.0,
                )
                break

        if not best_match:
            # Fuzzy match against product name and netsuite_item_name
            for product in products:
                score_name = fuzz.WRatio(
                    item.description.lower(), product.name.lower()
                ) / 100.0

                score_netsuite = 0.0
                if product.netsuite_item_name:
                    score_netsuite = fuzz.WRatio(
                        item.description.lower(),
                        product.netsuite_item_name.lower(),
                    ) / 100.0

                score = max(score_name, score_netsuite)
                if score > best_score and score >= 0.8:
                    best_score = score
                    best_match = ProductMatch(
                        product_id=product.id,
                        product_name=product.name,
                        confidence=score,
                    )

        matches[idx] = best_match

    return matches


def _match_and_compare(
    extracted_items: list[ExtractedLineItem],
    metadata: ExtractedMetadata,
    contract: Contract,
    tenant: Tenant,
) -> list[ComparisonItem]:
    """Match products and compare against existing contract items."""
    product_matches = _match_products(extracted_items, tenant)
    existing_items = list(ContractItem.objects.filter(contract=contract).select_related("product"))

    comparison_items = []
    for idx, item in enumerate(extracted_items):
        match = product_matches.get(idx)
        comp = ComparisonItem(extracted=item, product_match=match)

        # Check if this item already exists on the contract
        for existing in existing_items:
            if match and existing.product_id == match.product_id:
                comp.status = "existing"
                comp.existing_item_id = existing.id
                if existing.unit_price != item.unit_price:
                    comp.price_differs = True
                break

        comparison_items.append(comp)

    return comparison_items


def _compare_metadata(
    extracted: ExtractedMetadata, contract: Contract
) -> list[MetadataComparison]:
    """Compare extracted metadata against existing contract fields."""
    comparisons = []

    fields = [
        ("po_number", extracted.po_number, contract.po_number),
        (
            "order_confirmation_number",
            extracted.order_confirmation_number,
            contract.order_confirmation_number,
        ),
        (
            "min_duration_months",
            str(extracted.min_duration_months) if extracted.min_duration_months else None,
            str(contract.min_duration_months) if contract.min_duration_months else None,
        ),
    ]

    for field_name, extracted_val, current_val in fields:
        if extracted_val is not None:
            comparisons.append(
                MetadataComparison(
                    field_name=field_name,
                    extracted_value=extracted_val,
                    current_value=current_val,
                    differs=extracted_val != current_val,
                )
            )

    return comparisons
