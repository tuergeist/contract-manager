"""Service for matching extracted customer names to existing customers using fuzzy matching."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import F

from apps.customers.models import Customer


@dataclass
class CustomerMatch:
    """A potential customer match with similarity score."""

    customer_id: int
    customer_name: str
    city: str | None
    similarity: Decimal
    hubspot_id: str | None


def match_customer_by_name(
    tenant,
    extracted_name: str,
    min_similarity: float = 0.3,
    limit: int = 5,
) -> List[CustomerMatch]:
    """
    Find customers that fuzzy-match the extracted name using PostgreSQL trigram similarity.

    Args:
        tenant: The tenant to search within
        extracted_name: The customer name extracted from the invoice
        min_similarity: Minimum similarity threshold (0.0-1.0), default 0.3
        limit: Maximum number of matches to return

    Returns:
        List of CustomerMatch objects sorted by similarity (highest first)
    """
    if not extracted_name or not extracted_name.strip():
        return []

    # Use pg_trgm's trigram_similarity to find matches
    matches = (
        Customer.objects.filter(tenant=tenant)
        .annotate(similarity=TrigramSimilarity("name", extracted_name))
        .filter(similarity__gte=min_similarity)
        .order_by("-similarity")[:limit]
    )

    return [
        CustomerMatch(
            customer_id=m.id,
            customer_name=m.name,
            city=(m.address or {}).get("city"),
            similarity=Decimal(str(round(m.similarity, 2))),
            hubspot_id=m.hubspot_id,
        )
        for m in matches
    ]


def find_exact_match(tenant, extracted_name: str) -> Customer | None:
    """
    Find an exact (case-insensitive) customer match.

    Args:
        tenant: The tenant to search within
        extracted_name: The customer name extracted from the invoice

    Returns:
        Customer if exact match found, None otherwise
    """
    if not extracted_name or not extracted_name.strip():
        return None

    return Customer.objects.filter(
        tenant=tenant,
        name__iexact=extracted_name.strip(),
    ).first()


def auto_match_customer(tenant, extracted_name: str, threshold: float = 0.8) -> Customer | None:
    """
    Attempt to automatically match a customer with high confidence.

    Only returns a customer if there's a single high-confidence match.

    Args:
        tenant: The tenant to search within
        extracted_name: The customer name extracted from the invoice
        threshold: Minimum similarity for auto-match (default 0.8)

    Returns:
        Customer if high-confidence match found, None otherwise
    """
    # First try exact match
    exact = find_exact_match(tenant, extracted_name)
    if exact:
        return exact

    # Try fuzzy match with high threshold
    matches = match_customer_by_name(
        tenant,
        extracted_name,
        min_similarity=threshold,
        limit=2,
    )

    # Only auto-match if there's exactly one high-confidence match
    if len(matches) == 1 and float(matches[0].similarity) >= threshold:
        return Customer.objects.get(id=matches[0].customer_id)

    return None
