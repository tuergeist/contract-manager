"""Service for matching imported invoices to bank transactions (payments)."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Protocol

from django.db.models import Q

from apps.banking.models import BankTransaction
from apps.invoices.models import ImportedInvoice, InvoicePaymentMatch


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


class MatchingStrategy(Protocol):
    """Protocol for payment matching strategies."""

    def find_matches(
        self,
        invoice: ImportedInvoice,
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
        invoice_num = invoice.invoice_number.strip()

        # Create normalized versions for matching
        # Remove common separators for fuzzy matching
        normalized_num = re.sub(r"[-_\s]", "", invoice_num.lower())

        for txn in transactions:
            # Skip debit transactions (we want incoming payments = credits)
            if txn.amount <= 0:
                continue

            booking_lower = txn.booking_text.lower()
            booking_normalized = re.sub(r"[-_\s]", "", booking_lower)

            confidence = Decimal("0")

            # Exact match in booking text
            if invoice_num.lower() in booking_lower:
                confidence = Decimal("1.0")
            # Normalized match (ignoring separators)
            elif normalized_num in booking_normalized:
                confidence = Decimal("0.9")
            # Partial match - last part of invoice number
            elif len(normalized_num) > 4:
                suffix = normalized_num[-6:]  # Last 6 chars
                if suffix in booking_normalized:
                    confidence = Decimal("0.7")

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


class AmountCustomerStrategy:
    """Match by exact amount and linked customer."""

    def find_matches(
        self,
        invoice: ImportedInvoice,
        transactions: list[BankTransaction],
    ) -> List[PaymentMatchCandidate]:
        """Find transactions with matching amount from counterparties linked to invoice's customer."""
        if not invoice.total_amount or not invoice.customer:
            return []

        matches = []

        for txn in transactions:
            # Skip debit transactions
            if txn.amount <= 0:
                continue

            # Check if amount matches exactly
            if txn.amount != invoice.total_amount:
                continue

            # Check if counterparty is linked to invoice's customer
            if txn.counterparty.customer_id != invoice.customer_id:
                continue

            matches.append(
                PaymentMatchCandidate(
                    transaction_id=txn.id,
                    transaction_date=txn.entry_date,
                    amount=txn.amount,
                    counterparty_name=txn.counterparty.name,
                    booking_text=txn.booking_text[:200],
                    match_type=InvoicePaymentMatch.MatchType.AMOUNT_CUSTOMER,
                    confidence=Decimal("0.8"),
                )
            )

        return matches


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
        ]

    def find_matches(
        self,
        invoice: ImportedInvoice,
        days_after: int = 90,
    ) -> List[PaymentMatchCandidate]:
        """
        Find potential payment matches for an invoice.

        Searches credit transactions within a date window after the invoice date.

        Args:
            invoice: The imported invoice to find payments for
            days_after: How many days after invoice date to search (default 90)

        Returns:
            List of PaymentMatchCandidate objects sorted by confidence
        """
        if not invoice.invoice_date:
            return []

        # Get candidate transactions within date window
        start_date = invoice.invoice_date
        end_date = invoice.invoice_date + timedelta(days=days_after)

        transactions = list(
            BankTransaction.objects.filter(
                tenant=invoice.tenant,
                amount__gt=0,  # Credits only
                entry_date__gte=start_date,
                entry_date__lte=end_date,
            )
            .select_related("counterparty")
            .exclude(
                # Exclude transactions already matched to this invoice
                invoice_matches__invoice=invoice
            )
        )

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
