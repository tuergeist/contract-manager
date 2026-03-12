## Why

Payment matching currently starts from the invoice side (PaymentMatchModal opened per invoice). There is no transaction-centric view that shows a bank transaction alongside its matched invoices with running totals, differences, and overbooking detection. For reconciliation workflows, users need to start from the transaction, see what's already matched, add more invoices, and immediately see whether the transaction is fully covered, underpaid, or overpaid.

## What Changes

- New **Transaction Match View** — a split-pane UI (left: transaction details, right: matched invoices + search) accessible from the banking transaction list
- **Multi-invoice matching** — one transaction can be matched to multiple invoices; the view shows a running total and remaining difference (e.g. transaction €5,000 - invoice €3,200 - invoice €1,800 = €0 difference)
- **Multi-transaction matching** — one invoice can have multiple transaction matches (partial payments); the view shows this relationship from both sides
- **Overbooking guard** — warns when matched invoice totals exceed the transaction amount beyond a configurable tolerance (default ~3% for banking fees)
- **Running balance display** — each matched invoice row shows the cumulative matched amount and remaining unmatched amount on the transaction
- Reuses existing `InvoicePaymentMatch` model and `createPaymentMatch`/`createPaymentMatchForRecord` mutations

## Capabilities

### New Capabilities
- `transaction-match-view`: Split-pane reconciliation view — select a transaction, see/manage its invoice matches with running totals, difference calculation, and overbooking warnings

### Modified Capabilities
- `bank-transactions`: Transaction list gets a "Match" action button per row to open the match view
- `recurring-payment-detection`: No spec-level changes (implementation only — match view may link to existing patterns)

## Impact

- **Frontend**: New page/panel component under `/banking`, new route or slide-over from transaction list
- **Backend**: May need a new query to fetch all matches for a given transaction (reverse lookup), and a balance/difference calculation field
- **Existing mutations**: Reused as-is (`createPaymentMatch`, `createPaymentMatchForRecord`, `deletePaymentMatch`)
- **Model**: No schema changes — `InvoicePaymentMatch` already supports multiple matches per transaction and per invoice
