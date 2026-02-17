## 1. Backend GraphQL Type Renames

- [x] 1.1 Rename `ImportedInvoiceType` → `InvoiceType` in `backend/apps/invoices/schema.py`
- [x] 1.2 Rename `ImportedInvoiceConnection` → `InvoiceConnection`
- [x] 1.3 Rename `ImportedInvoiceResult` → `InvoiceResult`
- [x] 1.4 Rename `UpdateImportedInvoiceInput` → `UpdateInvoiceInput`
- [x] 1.5 Update all internal references to renamed types (return types, field types, helper function signatures)

## 2. Backend GraphQL Query Renames

- [x] 2.1 Rename query method `imported_invoices()` → `invoices()` (GraphQL field: `importedInvoices` → `invoices`)
- [x] 2.2 Rename query method `imported_invoice()` → `invoice()` (GraphQL field: `importedInvoice` → `invoice`)

## 3. Backend GraphQL Mutation Renames

- [x] 3.1 Rename mutation `update_imported_invoice()` → `update_invoice()`
- [x] 3.2 Rename mutation `delete_imported_invoice()` → `delete_invoice()`
- [x] 3.3 Rename mutation `confirm_imported_invoice()` → `confirm_invoice()`

## 4. Frontend File and Component Renames

- [x] 4.1 Rename `ImportedInvoiceList.tsx` → `InvoiceList.tsx`
- [x] 4.2 Rename component export `ImportedInvoiceList` → `InvoiceList`
- [x] 4.3 Rename interface `ImportedInvoice` → `Invoice`
- [x] 4.4 Rename interface `ImportBatch` → `InvoiceImportBatch`
- [x] 4.5 Update import in `App.tsx` to reference `InvoiceList`

## 5. Frontend GraphQL Query Updates

- [x] 5.1 Update all `importedInvoices` → `invoices` in GQL query strings in `InvoiceList.tsx`
- [x] 5.2 Update all `importedInvoice` → `invoice` in GQL query strings in `InvoiceList.tsx`
- [x] 5.3 Update `importedInvoices` query references in `ContractDetail.tsx`
- [x] 5.4 Update `importedInvoices` query references in `CustomerDetail.tsx`
- [x] 5.5 Update GQL mutation names (`updateImportedInvoice` → `updateInvoice`, etc.) in `InvoiceList.tsx`

## 6. Verification

- [x] 6.1 Global search for remaining `importedInvoice` references (case-insensitive) — fix any stragglers
- [x] 6.2 Run `npx tsc --noEmit` to verify frontend compiles
- [x] 6.3 Run `make test-back` to verify backend tests pass
