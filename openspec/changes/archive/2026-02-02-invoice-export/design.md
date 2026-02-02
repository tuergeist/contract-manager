## Context

The contract manager tracks contracts with billing schedules, but has no invoice export capability. Users need to generate monthly invoices for accounting systems or to send to customers. The existing `Contract.get_billing_schedule()` method already calculates billing events - this feature exposes that data through export functionality.

**Current state:**
- Billing schedule calculation exists in `Contract.get_billing_schedule()`
- No invoice entity or export endpoints exist
- Frontend has no invoice-related pages
- openpyxl is already a dependency (used for contract import)

## Goals / Non-Goals

**Goals:**
- Enable users to export all invoices due in a selected month
- Support PDF export (individual or combined) and Excel export
- Provide preview before export to verify invoice data
- Leverage existing billing schedule logic

**Non-Goals:**
- Persisting invoices to database (this is export-only, not invoice management)
- Integration with external accounting systems (future feature)
- Invoice numbering or sequential tracking (out of scope)
- Email delivery of invoices (future feature)

## Decisions

### 1. Invoice as transient data, not persisted

**Decision:** Calculate invoices on-demand from billing schedules rather than storing them as database entities.

**Rationale:**
- Invoices are derived data from contracts - storing them creates sync issues
- On-demand calculation ensures invoices always reflect current contract state
- Simpler implementation without invoice CRUD operations

**Alternative considered:** Create Invoice model with status tracking - rejected as over-engineering for export-only use case.

### 2. PDF generation with WeasyPrint

**Decision:** Use WeasyPrint for PDF generation from HTML templates.

**Rationale:**
- Renders HTML/CSS to PDF - reuse Django template skills
- Better typography and layout control than reportlab
- Already used in many Django projects, well-documented

**Alternative considered:** reportlab - more low-level, harder to maintain templates.

### 3. GraphQL query for invoice data, REST endpoint for file download

**Decision:**
- GraphQL `invoicesForMonth(year, month)` query returns invoice data for preview
- REST endpoint `/api/invoices/export/` handles file downloads (PDF/Excel)

**Rationale:**
- GraphQL is great for structured data queries (preview)
- File downloads work better with REST (streaming, content-disposition headers)
- Consistent with how other apps handle file exports

### 4. Single Excel file with multiple sheets

**Decision:** Excel export produces one file with sheets: Summary, Invoices, Line Items.

**Rationale:**
- Single file is easier to handle than multiple files
- Multiple sheets allow different views of the same data
- Matches typical accounting import expectations

### 5. Frontend route: `/invoices/export`

**Decision:** New top-level route rather than nested under contracts.

**Rationale:**
- Invoice export is a distinct workflow, not contract-specific
- Clean URL structure
- Easy to extend later (e.g., `/invoices` for invoice history)

## Risks / Trade-offs

**[Performance] Large month with many contracts** → Paginate preview, stream file downloads, add loading indicators. Consider caching billing schedule calculations.

**[Data accuracy] Billing schedule edge cases** → Rely on existing `get_billing_schedule()` which handles prorating, one-offs, and alignment. Add integration tests for export scenarios.

**[PDF rendering] Complex layouts or non-Latin text** → WeasyPrint handles Unicode well. Keep invoice template simple. Test with German characters.

**[Browser compatibility] File downloads** → Use standard content-disposition headers. Test in major browsers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  InvoiceExportPage                                   │    │
│  │  - MonthYearPicker                                   │    │
│  │  - InvoicePreviewTable                               │    │
│  │  - ExportButtons (PDF/Excel)                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│  ┌──────────────────┐    ┌─────────────────────────────┐    │
│  │ GraphQL Schema   │    │ REST Export View            │    │
│  │ - invoicesFor    │    │ - GET /api/invoices/export/ │    │
│  │   Month query    │    │   ?year=&month=&format=     │    │
│  └──────────────────┘    └─────────────────────────────┘    │
│           │                          │                       │
│           ▼                          ▼                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  InvoiceService                                      │    │
│  │  - get_invoices_for_month()                          │    │
│  │  - generate_pdf()                                    │    │
│  │  - generate_excel()                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│                              ▼                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Contract.get_billing_schedule() (existing)          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```
