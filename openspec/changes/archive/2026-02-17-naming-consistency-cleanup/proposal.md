## Why

The invoices feature evolved from "imported invoices only" to a unified system handling both imported and generated invoices. The codebase still carries the original "imported" naming in many places — GraphQL queries, mutations, types, component filenames, and frontend interfaces — creating confusion about what the code actually does. Cleaning this up makes the codebase easier to navigate and reduces friction when onboarding or making changes.

## What Changes

- **BREAKING** Rename GraphQL queries `importedInvoices` → `invoices`, `importedInvoice` → `invoice`
- **BREAKING** Rename GraphQL mutations `updateImportedInvoice` → `updateInvoice`, `deleteImportedInvoice` → `deleteInvoice`, `confirmImportedInvoice` → `confirmInvoice`
- Rename backend GraphQL types: `ImportedInvoiceType` → `InvoiceType`, `ImportedInvoiceResult` → `InvoiceResult`
- Rename frontend file `ImportedInvoiceList.tsx` → `InvoiceList.tsx` and its component export
- Rename frontend TypeScript interface `ImportedInvoice` → `Invoice`
- Align `ImportBatch` interface name with backend `InvoiceImportBatchType` → `InvoiceImportBatch`
- Standardize mutation naming: all invoice mutations should follow `verbInvoice` pattern (no "imported" prefix)

## Capabilities

### New Capabilities

_None — this is a rename/refactor only._

### Modified Capabilities

- `invoice-import`: Query and mutation names change (removing "imported" prefix), type names updated. No behavioral changes.

## Impact

- **GraphQL API**: Breaking changes to query/mutation names. All frontend queries must be updated in sync.
- **Backend**: `apps/invoices/schema.py` — type, query, and mutation renames. Model stays as `ImportedInvoice` (Django model rename would require migration and is out of scope).
- **Frontend**: `features/invoices/ImportedInvoiceList.tsx` renamed, all GraphQL query references updated in `ContractDetail.tsx`, `CustomerDetail.tsx`, `BankingPage.tsx`.
- **No database changes**: Django model `ImportedInvoice` and its table name remain unchanged to avoid unnecessary migrations.
