"""MT940 parsing and bank transaction import service."""
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import mt940

from apps.banking.models import BankAccount, BankTransaction, Counterparty
from apps.tenants.models import Tenant


@dataclass
class ImportResult:
    total: int = 0
    imported: int = 0
    skipped: int = 0
    errors: list[str] | None = None


class MT940Service:
    """Service for parsing MT940 files and importing transactions."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self._counterparty_cache: dict[str, Counterparty] = {}

    def _get_or_create_counterparty(
        self,
        name: str,
        iban: str = "",
        bic: str = "",
    ) -> Counterparty:
        """Find or create a Counterparty for the given name.

        Uses a cache to avoid repeated lookups within a single import.
        Updates IBAN/BIC if the existing record has empty values and new ones are provided.
        """
        if not name:
            name = "(Bank Fees / Unknown)"

        if name in self._counterparty_cache:
            cp = self._counterparty_cache[name]
            # Update IBAN/BIC if we have new data and old is empty
            update_fields = []
            if iban and not cp.iban:
                cp.iban = iban
                update_fields.append("iban")
            if bic and not cp.bic:
                cp.bic = bic
                update_fields.append("bic")
            if update_fields:
                cp.save(update_fields=update_fields)
            return cp

        cp, created = Counterparty.objects.get_or_create(
            tenant=self.tenant,
            name=name,
            defaults={"iban": iban, "bic": bic},
        )

        if not created:
            # Update IBAN/BIC if we have new data and old is empty
            update_fields = []
            if iban and not cp.iban:
                cp.iban = iban
                update_fields.append("iban")
            if bic and not cp.bic:
                cp.bic = bic
                update_fields.append("bic")
            if update_fields:
                cp.save(update_fields=update_fields)

        self._counterparty_cache[name] = cp
        return cp

    def parse_and_import(
        self,
        account: BankAccount,
        file_content: bytes | str,
    ) -> ImportResult:
        """Parse an MT940 file and import transactions into the given account.

        Deduplicates using import_hash. Returns stats about the import.
        """
        # Clear the cache for each new import
        self._counterparty_cache = {}

        # Parse the MT940 content
        if isinstance(file_content, bytes):
            # Try UTF-8 first, fall back to latin-1 (common for German banks)
            try:
                text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                text = file_content.decode("latin-1")
        else:
            text = file_content

        # Validate account identification from file
        account_ids = set(re.findall(r":25:(\S+)", text))
        expected_id = f"{account.bank_code}/{account.account_number}"
        if account_ids and expected_id not in account_ids:
            return ImportResult(
                errors=[
                    f"File contains account {', '.join(account_ids)} "
                    f"but target account is {expected_id}"
                ]
            )

        # Parse statements
        try:
            statements = list(mt940.parse(text))
        except Exception as e:
            return ImportResult(errors=[f"Failed to parse MT940 file: {e}"])

        if not statements:
            return ImportResult(errors=["No transactions found in file"])

        # Extract opening/closing balances per statement
        # The mt940 lib flattens into statements where each has transactions
        transactions_to_create = []
        total = 0

        for stmt in statements:
            # Get balances from statement data
            opening_bal = None
            closing_bal = None
            ob = stmt.data.get("final_opening_balance")
            cb = stmt.data.get("final_closing_balance")
            if ob:
                opening_bal = ob.amount.amount
            if cb:
                closing_bal = cb.amount.amount

            for tx in stmt.transactions:
                total += 1
                data = tx.data

                # Extract amount (mt940 Amount object)
                amount_obj = data.get("amount")
                if amount_obj is None:
                    continue
                amount = Decimal(str(amount_obj.amount))
                currency = data.get("currency", "EUR")

                # Extract dates
                entry_date = data.get("date")
                value_date = data.get("entry_date")
                if entry_date:
                    entry_date = date(entry_date.year, entry_date.month, entry_date.day)
                else:
                    continue  # Skip transactions without a date
                if value_date:
                    value_date = date(value_date.year, value_date.month, value_date.day)

                # Extract counterparty info
                counterparty_name = data.get("applicant_name") or ""
                counterparty_iban = data.get("applicant_iban") or ""
                counterparty_bic = data.get("applicant_bin") or ""

                # Get or create the Counterparty entity
                counterparty = self._get_or_create_counterparty(
                    name=counterparty_name,
                    iban=counterparty_iban,
                    bic=counterparty_bic,
                )

                # Extract booking text (purpose + additional_purpose)
                purpose = data.get("purpose") or ""
                additional = data.get("additional_purpose") or ""
                booking_text = f"{purpose} {additional}".strip()

                # Extract references
                eref = data.get("end_to_end_reference") or ""
                kref = ""
                cust_ref = data.get("customer_reference") or ""
                if cust_ref.startswith("KREF+"):
                    kref = cust_ref[5:].replace("\n", " ").strip()
                mref = data.get("additional_position_reference") or ""
                ref_parts = [p for p in [eref, kref, mref] if p]
                reference = " | ".join(ref_parts)

                # Transaction type
                tx_type = data.get("id") or ""

                # Build raw data from all available fields
                raw_parts = []
                if data.get("posting_text"):
                    raw_parts.append(f"posting: {data['posting_text']}")
                if purpose:
                    raw_parts.append(f"purpose: {purpose}")
                if additional:
                    raw_parts.append(f"additional: {additional}")
                raw_data = "; ".join(raw_parts)

                # Compute dedup hash (still uses counterparty_name for backwards compat)
                import_hash = BankTransaction.compute_hash(
                    account_id=account.id,
                    entry_date=entry_date,
                    amount=amount,
                    currency=currency,
                    reference=reference,
                    counterparty_name=counterparty_name,
                )

                transactions_to_create.append(
                    BankTransaction(
                        tenant=self.tenant,
                        account=account,
                        entry_date=entry_date,
                        value_date=value_date,
                        amount=amount,
                        currency=currency,
                        transaction_type=tx_type,
                        counterparty=counterparty,
                        booking_text=booking_text,
                        reference=reference,
                        raw_data=raw_data,
                        opening_balance=opening_bal,
                        closing_balance=closing_bal,
                        import_hash=import_hash,
                    )
                )

        if not transactions_to_create:
            return ImportResult(total=total)

        # Deduplicate within the parsed batch itself (mt940 lib can produce
        # duplicate transaction objects across flattened statements)
        seen_hashes = {}
        for tx in transactions_to_create:
            seen_hashes[tx.import_hash] = tx
        unique_transactions = list(seen_hashes.values())
        unique_total = len(unique_transactions)

        # Count before insert so we can compute actual new rows
        count_before = BankTransaction.objects.filter(
            tenant=self.tenant, account=account
        ).count()

        # Bulk insert with dedup (ignore conflicts on unique import_hash)
        batch_size = 500
        for i in range(0, len(unique_transactions), batch_size):
            batch = unique_transactions[i : i + batch_size]
            BankTransaction.objects.bulk_create(batch, ignore_conflicts=True)

        count_after = BankTransaction.objects.filter(
            tenant=self.tenant, account=account
        ).count()
        imported = count_after - count_before

        return ImportResult(
            total=unique_total,
            imported=imported,
            skipped=unique_total - imported,
        )
