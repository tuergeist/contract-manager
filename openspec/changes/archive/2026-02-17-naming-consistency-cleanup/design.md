## Context

The invoices feature started as "imported invoices" — PDF uploads with metadata extraction. It has since grown to include generated invoices, CSV imports, and batch uploads. The "imported" prefix remains in GraphQL types, queries, mutations, and frontend code, making the naming misleading.

This is a purely internal refactor. There is no external API contract — the GraphQL API is consumed only by our own React frontend.

## Goals / Non-Goals

**Goals:**
- Remove "imported" prefix from all GraphQL query/mutation names and types
- Rename the frontend component file and TypeScript interfaces to match
- Keep all behavior identical — pure rename, no logic changes

**Non-Goals:**
- Renaming the Django model `ImportedInvoice` or its database table (would require a migration with data, not worth it)
- Renaming the backend helper function `_convert_imported_invoice` (internal, not exposed)
- Renaming the `InvoiceImportBatch` model or type (this name is accurate — it represents an import batch)
- Changing the `invoice-import` spec name (the spec describes the import capability, name is still correct)
- Renaming migration files (immutable once applied)

## Decisions

### 1. Rename GraphQL types and keep Django models unchanged

The GraphQL layer is the public interface; the Django model is internal. Strawberry types are manually constructed (not auto-generated from models), so the type name is independent of the model name.

**Renames:**
| Current | New |
|---------|-----|
| `ImportedInvoiceType` | `InvoiceType` |
| `ImportedInvoiceConnection` | `InvoiceConnection` |
| `ImportedInvoiceResult` | `InvoiceResult` |
| `UpdateImportedInvoiceInput` | `UpdateInvoiceInput` |

### 2. Rename GraphQL query and mutation methods

Strawberry derives the GraphQL field name from the Python method name. Renaming the method renames the API field.

**Queries:**
| Current method | New method | GraphQL field |
|---------------|-----------|---------------|
| `imported_invoices()` | `invoices()` | `invoices` |
| `imported_invoice()` | `invoice()` | `invoice` |

**Mutations:**
| Current method | New method | GraphQL field |
|---------------|-----------|---------------|
| `update_imported_invoice()` | `update_invoice()` | `updateInvoice` |
| `delete_imported_invoice()` | `delete_invoice()` | `deleteInvoice` |
| `confirm_imported_invoice()` | `confirm_invoice()` | `confirmInvoice` |

Methods that already lack the "imported" prefix stay as-is: `upload_invoice`, `extract_invoice`, `re_extract_invoice`, `upload_invoices`, `upload_invoice_csv`.

### 3. Rename frontend file and interfaces

| Current | New |
|---------|-----|
| `ImportedInvoiceList.tsx` | `InvoiceList.tsx` |
| `interface ImportedInvoice` | `interface Invoice` |
| `interface ImportBatch` | `interface InvoiceImportBatch` |
| Component export `ImportedInvoiceList` | `InvoiceList` |

Update the import in `App.tsx` and any other files referencing the old names.

### 4. Update all frontend GraphQL query strings

Every `gql` template literal that references `importedInvoices` or `importedInvoice` must be updated. These appear in:
- `ImportedInvoiceList.tsx` (→ `InvoiceList.tsx`)
- `ContractDetail.tsx`
- `CustomerDetail.tsx`

### 5. Single atomic commit

All backend and frontend changes ship together in one commit since the API and consumer must stay in sync.

## Risks / Trade-offs

- **Risk: Missed reference** — A stale `importedInvoice` string somewhere causes a runtime GraphQL error.
  → Mitigation: Global search for `importedInvoice` (case-insensitive) after all renames. TypeScript compilation will catch frontend issues. Backend tests will catch query/mutation issues.

- **Risk: Apollo cache invalidation** — Renaming GraphQL types could affect Apollo's `__typename`-based caching.
  → Mitigation: The Strawberry types use explicit class names. Apollo will treat the new type names as new types, which is fine — no persistent cache across deployments.

- **Trade-off: Model name diverges from type name** — `ImportedInvoice` (Django) vs `InvoiceType` (GraphQL). This is acceptable since the GraphQL type is already manually constructed and the model name is internal.
