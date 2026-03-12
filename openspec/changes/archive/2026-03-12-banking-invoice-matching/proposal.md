## Why

When a bank transaction comes in from a linked counterparty (counterparty linked to a customer), users still have to manually search for the right invoice to match. Since we already know which customer the payment is from, we should automatically suggest their unpaid invoices as match candidates — ranked by amount proximity and filtered to invoices dated before the payment.

## What Changes

- Add a backend query that returns suggested invoice candidates for a transaction, using the counterparty → customer link to find unpaid invoices where `invoice_date <= transaction.entry_date`
- Rank candidates by amount proximity to the transaction amount (closest match first)
- Show suggested matches in the TransactionMatchSheet above the manual search, so users can one-click match without typing
- Fall back to manual search when no counterparty-customer link exists

## Capabilities

### New Capabilities
- `invoice-match-suggestions`: Backend query to compute and rank invoice candidates for a transaction based on the counterparty's linked customer, amount proximity, and date eligibility

### Modified Capabilities
- `transaction-match-view`: Add a "Suggested matches" section to the match sheet that auto-loads candidates when the counterparty is linked to a customer

## Impact

- **Backend**: New query resolver in banking or invoices schema; reads Counterparty.customer, ImportedInvoice, InvoiceRecord
- **Frontend**: TransactionMatchSheet.tsx gets a new suggestions section above the search panel
- **No model changes**: Uses existing Counterparty.customer ForeignKey
- **No breaking changes**: Manual search remains available as fallback
