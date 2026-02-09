## Why

The tool currently only tracks the revenue/debitor side (customer contracts, invoices). There is no visibility into the cost/creditor side — what suppliers are paid, when, and how much accumulates over a year. The company's bank exports (MT940/MTA format) contain all this data but there is no way to import, store, search, or analyze it. Having bank transaction data inside the tool enables cost tracking, supplier analysis, and eventually matching costs to contracts.

## What Changes

- **New: Bank Accounts section** — a dedicated area in the app where users can manage bank accounts and upload MT940/MTA statement files
- **New: MT940 parser** — backend service to parse MT940 (SWIFT) bank statement files, extracting transactions with date, amount, counterparty (name, IBAN, BIC), booking text, reference, and value date
- **New: Transaction storage with deduplication** — imported transactions are persisted; overlapping/duplicate entries (same account + date + amount + reference) are silently ignored on re-import
- **New: Transaction list view** — searchable, filterable, sortable table of all bank transactions across all accounts. Filters: bank account, date range, amount range, counterparty name, booking text, debit/credit direction

## Capabilities

### New Capabilities
- `bank-accounts`: Managing bank accounts (CRUD) and uploading MT940 files per account
- `bank-transactions`: Storing, deduplicating, searching, and filtering imported bank transactions

### Modified Capabilities
_(none)_

## Impact

- **Backend**: New Django app (`banking` or extend `invoices`), new models (BankAccount, BankTransaction), MT940 parsing service, new GraphQL queries/mutations
- **Frontend**: New sidebar entry, new pages for bank accounts and transaction list
- **Dependencies**: MT940 parser library (e.g. `mt-940` Python package) or custom parser
- **Database**: New tables for accounts and transactions (potentially large volume — need indexing on date, amount, counterparty)
