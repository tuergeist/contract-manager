"""Offer numbering service for sequential, pattern-based number generation."""
from apps.invoices.numbering import BaseNumberService


class OfferNumberService(BaseNumberService):
    """Generates unique sequential offer numbers."""

    default_pattern = "{YYYY}-{NNNN}"

    @property
    def scheme_model(self):
        from apps.offers.models import OfferNumberScheme
        return OfferNumberScheme
