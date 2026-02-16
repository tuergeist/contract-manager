from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def money(value, language="de"):
    """Format a number with thousand separators and 2 decimal places.

    German (de): 15.105,00
    English (en): 15,105.00
    """
    try:
        num = Decimal(str(value))
    except Exception:
        return value

    if language == "en":
        thousands_sep = ","
        decimal_sep = "."
    else:
        thousands_sep = "."
        decimal_sep = ","

    # Format with 2 decimal places
    formatted = f"{abs(num):,.2f}"
    # Replace default separators (comma=thousand, dot=decimal) with target
    # Use placeholder to avoid double-replace
    formatted = formatted.replace(",", "THOU").replace(".", decimal_sep).replace("THOU", thousands_sep)

    if num < 0:
        formatted = "-" + formatted

    return formatted
