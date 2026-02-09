## Context

The tool manages customer contracts (debitor side) but has no visibility into costs (creditor side). German banks export account statements as MT940/MTA files (SWIFT standard). The company wants to import these files into the tool to search, filter, and analyze all bank transactions. This is the foundation for future supplier cost tracking and contract matching.

Currently there is no `banking` app. A new Django app will be created following the same patterns as `invoices` and `contracts` — multi-tenant models, Strawberry GraphQL schema, and a React feature module with Shadcn/ui components.

## Goals / Non-Goals

**Goals:**
- Import MT940 files and persist every transaction with full metadata
- Deduplicate on re-import (same file or overlapping date ranges)
- Provide a fast, searchable, filterable transaction list view
- Support multiple bank accounts per tenant

**Non-Goals:**
- Automatic supplier matching or categorization (future phase)
- Linking transactions to contracts or invoices (future phase)
- Real-time bank API integration (CSV/MT940 file upload only)
- Outgoing payment initiation

## Decisions

### 1. New Django app `banking`

Create `backend/apps/banking/` rather than extending the `invoices` app. Bank transactions are a separate domain — they include both incoming and outgoing payments and are not invoice-specific. Keeps concerns separated.

Alternative considered: Extending `invoices` app. Rejected because bank transactions are broader than invoicing and would bloat that app.

### 2. MT940 parsing with `mt-940` Python package

Use the established `mt-940` PyPI package (MIT license, well-maintained) rather than writing a custom parser. MT940 is a complex format with bank-specific quirks (as seen in the sample file with `?20`–`?63` subfields). The package handles these edge cases.

Alternative considered: Custom regex parser. Rejected — MT940 has too many vendor-specific variations to handle reliably.

### 3. Data model: BankAccount + BankTransaction

**BankAccount** (tenant-scoped):
- `name` — user-given label (e.g. "Geschäftskonto Dresdner")
- `bank_code` — BLZ / routing number (from MT940 `:25:` field, e.g. "85090000")
- `account_number` — account number (from `:25:` field, e.g. "2721891006")
- `iban` — optional, for display
- `bic` — optional, for display

**BankTransaction** (tenant-scoped, FK to BankAccount):
- `entry_date` — booking date (from `:61:` field)
- `value_date` — value/settlement date (from `:61:` field)
- `amount` — decimal, positive for credit, negative for debit
- `currency` — EUR etc. (from `:60F:` field)
- `transaction_type` — SWIFT type code (e.g. NTRF, NDDT)
- `counterparty_name` — extracted from `:86:` field `?32`/`?33`
- `counterparty_iban` — extracted from `:86:` subfields
- `counterparty_bic` — extracted from `:86:` subfields
- `booking_text` — transaction description / Verwendungszweck (assembled from `:86:` `?20`–`?29` subfields)
- `reference` — EREF/KREF/MREF combined
- `raw_data` — full `:86:` field as-is for debugging
- `opening_balance` — from `:60F:` for the statement this belongs to
- `closing_balance` — from `:62F:` for the statement this belongs to
- `import_hash` — SHA256 of (account_id + entry_date + amount + reference) for deduplication

**Indexes:** Composite index on `(tenant_id, account_id, entry_date)`, individual indexes on `amount`, `counterparty_name`, `booking_text` (for search), and unique constraint on `import_hash` per tenant.

### 4. Deduplication strategy

Each transaction gets a deterministic hash computed from `(bank_account_id, entry_date, amount, currency, reference, counterparty_name)`. On import, use `INSERT ... ON CONFLICT (tenant_id, import_hash) DO NOTHING` semantics via Django's `bulk_create(ignore_conflicts=True)`. This silently skips duplicates without error.

Alternative considered: Date-range-based overlap detection. Rejected — too complex and fragile. Hash-based dedup is simple, deterministic, and handles partial re-imports correctly.

### 5. File upload via REST endpoint

MT940 upload via a REST `POST /api/banking/upload/<account_id>/` endpoint (similar to invoice logo upload pattern in `invoices/views.py`). Returns JSON with import stats (total parsed, new, skipped). GraphQL is not ideal for file uploads.

### 6. Frontend: single page with account selector + transaction table

One main page `/banking` with:
- Account selector/manager in a sidebar or header section
- Transaction table below, filtered to selected account (or "all accounts")
- Standard table pattern: search bar, column filters, sortable headers, pagination
- Upload button per account opens file dialog

This avoids needing separate account list and transaction list pages. Keeps the UX simple.

### 7. Permission resource: `banking`

Add `banking.read` and `banking.write` permissions following the existing RBAC pattern. Read for viewing transactions, write for uploading files and managing accounts.

## Risks / Trade-offs

**Large import volumes** → A single MT940 file can contain thousands of transactions across months. `bulk_create` with batching (500 per batch) keeps memory usage reasonable. Pagination on the frontend ensures the table stays responsive.

**MT940 format variations between banks** → Different German banks encode `:86:` subfields slightly differently. The `mt-940` package handles most variations, but edge cases may need custom post-processing. Mitigation: store `raw_data` field so nothing is lost even if parsing is imperfect.

**Hash collisions on deduplication** → Two genuinely different transactions with identical date/amount/reference/counterparty would be treated as duplicates. This is extremely rare for bank transactions. Mitigation: include enough fields in the hash to make collisions practically impossible.

## Open Questions

- Should the upload accept multiple files at once (batch upload), or one file per upload?
- Should there be a "delete imported data" action per file/date range, or is data append-only?
