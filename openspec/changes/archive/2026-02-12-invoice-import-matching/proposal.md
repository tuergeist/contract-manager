## Why

We issue invoices to customers but have no central system to track them and their payment status. Currently there's no way to import existing outgoing invoices or match them against incoming bank transactions (payments) to verify they've been paid. This creates manual reconciliation work and makes it hard to track outstanding receivables.

## What Changes

- Add ability to upload/import our outgoing invoice PDFs (we are the Kreditor)
- Run AI extraction on uploaded invoices to extract: invoice number, total amount, invoice date, and customer name
- Match extracted customer to existing customers in the system (fuzzy matching)
- Create invoice records in the database (metadata only, linked to PDF)
- Add invoice-to-transaction matching for incoming payments with flexible strategies:
  - Invoice number matching in booking text (with fuzziness for typos/formatting differences)
  - Amount + customer matching (counterparty matches customer)
  - Manual matching as fallback
- Display payment status on invoices and matched invoice info on transactions

## Capabilities

### New Capabilities
- `invoice-import`: Upload outgoing invoice PDFs, store in object storage, create invoice records with extracted metadata
- `invoice-extraction`: AI-powered extraction of invoice number, total amount, date, and customer from PDF
- `invoice-payment-matching`: Match incoming bank transactions (credits) to invoices using configurable strategies (invoice number fuzzy match in booking text, amount+customer match, manual)

### Modified Capabilities
- `bank-transactions`: Add invoice reference field and payment match status to credit transactions; display matched invoice info in transaction list

## Impact

- **Backend**: New Invoice model, extraction service (using existing AI infrastructure), payment matching service with pluggable strategies
- **Frontend**: Invoice list page with payment status, upload UI, extraction review UI, match status indicators on transactions
- **Database**: New invoices table, junction table for transaction-invoice payment matches
- **Dependencies**: Reuses existing PDF extraction AI tools and object storage
