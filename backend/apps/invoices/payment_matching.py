"""Service for matching invoices to bank transactions (payments).

Supports both ImportedInvoice and InvoiceRecord via duck typing.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Protocol, Union

from django.db.models import Q
from rapidfuzz import fuzz

from apps.banking.models import BankTransaction
from apps.invoices.models import ImportedInvoice, InvoicePaymentMatch, InvoiceRecord


@dataclass
class PaymentMatchCandidate:
    """A potential payment match with confidence score."""

    transaction_id: int
    transaction_date: date
    amount: Decimal
    counterparty_name: str
    booking_text: str
    match_type: str
    confidence: Decimal


class InvoiceRecordAdapter:
    """Adapter to make InvoiceRecord duck-type compatible with ImportedInvoice for matching."""

    def __init__(self, record: InvoiceRecord):
        self._record = record
        self.invoice_number = record.invoice_number
        self.invoice_date = record.billing_date
        self.total_amount = record.total_gross
        self.customer = record.customer
        self.customer_id = record.customer_id
        self.tenant = record.tenant


class MatchingStrategy(Protocol):
    """Protocol for payment matching strategies."""

    def find_matches(
        self,
        invoice: Union[ImportedInvoice, InvoiceRecordAdapter],
        transactions: list[BankTransaction],
    ) -> List[PaymentMatchCandidate]:
        """Find matching transactions for the given invoice."""
        ...


class InvoiceNumberStrategy:
    """Match by finding invoice number in booking text."""

    def find_matches(
        self,
        invoice: ImportedInvoice,
        transactions: list[BankTransaction],
    ) -> List[PaymentMatchCandidate]:
        """Search for invoice number in booking_text using fuzzy matching."""
        if not invoice.invoice_number:
            return []

        matches = []

        for txn in transactions:
            if txn.amount <= 0:
                continue

            confidence = _extract_invoice_number_from_text(txn.booking_text, invoice.invoice_number)
            if confidence > 0:
                matches.append(
                    PaymentMatchCandidate(
                        transaction_id=txn.id,
                        transaction_date=txn.entry_date,
                        amount=txn.amount,
                        counterparty_name=txn.counterparty.name,
                        booking_text=txn.booking_text[:200],
                        match_type=InvoicePaymentMatch.MatchType.INVOICE_NUMBER,
                        confidence=confidence,
                    )
                )

        return sorted(matches, key=lambda m: m.confidence, reverse=True)


def _get_fee_tolerance(tenant) -> tuple[Decimal, Decimal]:
    """Get fee tolerance settings from tenant banking config."""
    config = (tenant.settings or {}).get("banking", {})
    return (
        Decimal(config.get("fee_tolerance_fixed", "0")),
        Decimal(config.get("fee_tolerance_percent", "0")),
    )


def _amount_within_tolerance(
    transaction_amount: Decimal,
    invoice_amount: Decimal,
    tolerance_fixed: Decimal,
    tolerance_percent: Decimal,
) -> bool:
    """Check if transaction amount is within tolerance of invoice amount.

    The transaction may be less than the invoice by up to the tolerance
    (e.g. bank fees deducted), but not more.
    """
    if transaction_amount == invoice_amount:
        return True

    max_tolerance = tolerance_fixed
    if tolerance_percent > 0:
        percent_tolerance = invoice_amount * tolerance_percent / Decimal("100")
        max_tolerance = max(max_tolerance, percent_tolerance)

    if max_tolerance <= 0:
        return False

    # Transaction can be up to max_tolerance less than invoice amount
    diff = invoice_amount - transaction_amount
    return Decimal("0") <= diff <= max_tolerance


def _extract_invoice_number_from_text(booking_text: str, invoice_number: str) -> Decimal:
    """Try to find the invoice number (or a recognizable part) in booking text.

    Returns confidence score (0 = no match, 0.7-1.0 = match found).
    """
    if not invoice_number or not booking_text:
        return Decimal("0")

    inv_num = invoice_number.strip().lower()
    booking_lower = booking_text.lower()
    normalized_num = re.sub(r"[-_\s]", "", inv_num)
    booking_normalized = re.sub(r"[-_\s]", "", booking_lower)

    # Exact match
    if inv_num in booking_lower:
        return Decimal("1.0")
    # Normalized match (ignoring separators like INV-VSX-26-0009 vs INVVSX260009)
    if normalized_num in booking_normalized:
        return Decimal("0.9")
    # Partial: extract the numeric core (e.g. "26-0009" from "INV-VSX-26-0009")
    # and search for it with flexible separators
    numeric_parts = re.findall(r"\d+", inv_num)
    if len(numeric_parts) >= 2:
        # Try last two numeric segments (year + counter, e.g. "26" + "0009")
        core = "".join(numeric_parts[-2:])
        if len(core) >= 4 and core in booking_normalized:
            return Decimal("0.8")
        # Try with separator pattern between segments (e.g. "26-009" matching "26-0009")
        # Strip leading zeros from counter for flexible matching
        last_seg = numeric_parts[-1].lstrip("0") or "0"
        second_last = numeric_parts[-2]
        pattern = re.escape(second_last) + r"[-_\s./]*0*" + re.escape(last_seg)
        if re.search(pattern, booking_lower):
            return Decimal("0.7")
    # Last 6 chars fallback
    if len(normalized_num) > 4:
        suffix = normalized_num[-6:]
        if suffix in booking_normalized:
            return Decimal("0.7")

    return Decimal("0")


class AmountCustomerStrategy:
    """Match by amount (with tolerance) and linked customer."""

    def find_matches(
        self,
        invoice: ImportedInvoice,
        transactions: list[BankTransaction],
    ) -> List[PaymentMatchCandidate]:
        """Find transactions with matching amount from counterparties linked to invoice's customer."""
        if not invoice.total_amount or not invoice.customer:
            return []

        tolerance_fixed, tolerance_percent = _get_fee_tolerance(invoice.tenant)
        matches = []

        for txn in transactions:
            if txn.amount <= 0:
                continue

            if not _amount_within_tolerance(txn.amount, invoice.total_amount, tolerance_fixed, tolerance_percent):
                continue

            if txn.counterparty.customer_id != invoice.customer_id:
                continue

            # Exact amount = 0.8, within tolerance = 0.7
            confidence = Decimal("0.8") if txn.amount == invoice.total_amount else Decimal("0.7")

            matches.append(
                PaymentMatchCandidate(
                    transaction_id=txn.id,
                    transaction_date=txn.entry_date,
                    amount=txn.amount,
                    counterparty_name=txn.counterparty.name,
                    booking_text=txn.booking_text[:200],
                    match_type=InvoicePaymentMatch.MatchType.AMOUNT_CUSTOMER,
                    confidence=confidence,
                )
            )

        return matches


class UnlinkedCounterpartyStrategy:
    """Match transactions where counterparty is not linked to a customer.

    Combines three signals:
    1. Invoice number found in booking text
    2. Amount within fee tolerance
    3. Fuzzy match of counterparty name to customer name

    Requires at least invoice number OR (amount match + name match).
    """

    COUNTERPARTY_NAME_THRESHOLD = 60  # rapidfuzz score 0-100

    def find_matches(
        self,
        invoice: Union[ImportedInvoice, InvoiceRecordAdapter],
        transactions: list[BankTransaction],
    ) -> List[PaymentMatchCandidate]:
        if not invoice.total_amount:
            return []

        customer_name = self._get_customer_name(invoice)
        if not customer_name:
            return []

        tolerance_fixed, tolerance_percent = _get_fee_tolerance(invoice.tenant)
        matches = []

        for txn in transactions:
            if txn.amount <= 0:
                continue

            # Only consider transactions where counterparty is NOT linked to a customer
            if txn.counterparty.customer_id is not None:
                continue

            # Signal 1: invoice number in booking text
            inv_num_confidence = _extract_invoice_number_from_text(
                txn.booking_text, invoice.invoice_number
            )

            # Signal 2: amount match (exact or within tolerance)
            amount_ok = _amount_within_tolerance(
                txn.amount, invoice.total_amount, tolerance_fixed, tolerance_percent
            )

            # Signal 3: fuzzy counterparty name match
            name_score = fuzz.token_set_ratio(
                txn.counterparty.name.lower(), customer_name.lower()
            )
            name_ok = name_score >= self.COUNTERPARTY_NAME_THRESHOLD

            # Require meaningful combination of signals
            if inv_num_confidence > 0:
                # Invoice number found — strong signal; boost if amount/name also match
                confidence = inv_num_confidence
                if amount_ok:
                    confidence = min(confidence + Decimal("0.05"), Decimal("1.0"))
                if name_ok:
                    confidence = min(confidence + Decimal("0.05"), Decimal("1.0"))
            elif amount_ok and name_ok:
                # No invoice number but amount + name match
                name_factor = Decimal(str(round(name_score / 100, 2)))
                confidence = Decimal("0.5") + name_factor * Decimal("0.2")
                if txn.amount == invoice.total_amount:
                    confidence += Decimal("0.05")
            else:
                continue

            matches.append(
                PaymentMatchCandidate(
                    transaction_id=txn.id,
                    transaction_date=txn.entry_date,
                    amount=txn.amount,
                    counterparty_name=txn.counterparty.name,
                    booking_text=txn.booking_text[:200],
                    match_type=InvoicePaymentMatch.MatchType.FUZZY_COMPOSITE,
                    confidence=confidence,
                )
            )

        return sorted(matches, key=lambda m: m.confidence, reverse=True)

    def _get_customer_name(self, invoice) -> str | None:
        if hasattr(invoice, "customer_name") and invoice.customer_name:
            return invoice.customer_name
        if invoice.customer:
            return invoice.customer.name
        return None


class PaymentMatcher:
    """
    Service for finding potential payment matches for invoices.

    Uses pluggable matching strategies to find candidates.
    """

    def __init__(self, strategies: Optional[List[MatchingStrategy]] = None):
        """
        Initialize with matching strategies.

        Args:
            strategies: List of strategies to use. Defaults to standard strategies.
        """
        self.strategies = strategies or [
            InvoiceNumberStrategy(),
            AmountCustomerStrategy(),
            UnlinkedCounterpartyStrategy(),
        ]

    def find_matches(
        self,
        invoice: Union[ImportedInvoice, InvoiceRecordAdapter],
        days_after: int = 90,
    ) -> List[PaymentMatchCandidate]:
        """
        Find potential payment matches for an invoice.

        Searches credit transactions within a date window after the invoice date.

        Args:
            invoice: The imported invoice or adapted record to find payments for
            days_after: How many days after invoice date to search (default 90)

        Returns:
            List of PaymentMatchCandidate objects sorted by confidence
        """
        if not invoice.invoice_date:
            return []

        # Get candidate transactions within date window
        start_date = invoice.invoice_date
        end_date = invoice.invoice_date + timedelta(days=days_after)

        qs = BankTransaction.objects.filter(
            tenant=invoice.tenant,
            amount__gt=0,  # Credits only
            entry_date__gte=start_date,
            entry_date__lte=end_date,
        ).select_related("counterparty")

        # Exclude transactions already matched to this invoice
        if isinstance(invoice, InvoiceRecordAdapter):
            qs = qs.exclude(invoice_matches__invoice_record=invoice._record)
        else:
            qs = qs.exclude(invoice_matches__invoice=invoice)

        transactions = list(qs)

        # Run all strategies and collect matches
        all_matches: dict[int, PaymentMatchCandidate] = {}

        for strategy in self.strategies:
            strategy_matches = strategy.find_matches(invoice, transactions)
            for match in strategy_matches:
                # Keep the highest confidence match for each transaction
                existing = all_matches.get(match.transaction_id)
                if not existing or match.confidence > existing.confidence:
                    all_matches[match.transaction_id] = match

        # Sort by confidence descending
        return sorted(all_matches.values(), key=lambda m: m.confidence, reverse=True)

    def find_all_unmatched(
        self,
        tenant,
        days_after: int = 90,
    ) -> dict[int, List[PaymentMatchCandidate]]:
        """
        Find matches for all unmatched invoices.

        Args:
            tenant: The tenant to search within
            days_after: How many days after invoice date to search

        Returns:
            Dict mapping invoice_id to list of potential matches
        """
        unmatched_invoices = ImportedInvoice.objects.filter(
            tenant=tenant,
            extraction_status__in=[
                ImportedInvoice.ExtractionStatus.EXTRACTED,
                ImportedInvoice.ExtractionStatus.CONFIRMED,
            ],
        ).exclude(payment_matches__isnull=False)

        results = {}
        for invoice in unmatched_invoices:
            matches = self.find_matches(invoice, days_after=days_after)
            if matches:
                results[invoice.id] = matches

        return results
