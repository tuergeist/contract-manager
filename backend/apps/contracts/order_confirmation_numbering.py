"""Order confirmation numbering service, reusing the invoice numbering base class."""
from apps.invoices.numbering import BaseNumberService


class OrderConfirmationNumberService(BaseNumberService):
    """Generates unique sequential order confirmation numbers."""

    default_pattern = "AB-{YYYY}-{NNNN}"

    @property
    def scheme_model(self):
        from apps.contracts.order_confirmation_models import OrderConfirmationNumberScheme
        return OrderConfirmationNumberScheme
