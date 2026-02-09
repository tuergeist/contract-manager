## Context

The contract manager already has a stateless invoice system: `InvoiceService` calculates invoices on-demand from contract billing schedules, renders them via a hardcoded HTML/WeasyPrint template, and exports as PDF/Excel. There are no persisted invoice records, no invoice numbers, and no German legal fields (tax, register data, bank details). The current template shows only company name, customer address, line items, and a total.

The Tenant model has a `settings` JSONField and a `currency` field, but no company legal data. File uploads exist for contract and customer attachments using Django's `FileField` with `upload_to` callables and `MEDIA_ROOT`.

## Goals / Non-Goals

**Goals:**
- Allow users to upload reference invoice PDFs that serve as visual inspiration for template configuration
- Provide a configurable invoice template system (logo, colors, header/footer text, legal blocks)
- Implement sequential invoice numbering with configurable patterns
- Store all German HGB/UStG §14 mandatory company data at the tenant level
- Persist generated invoices as database records with assigned numbers
- Update the PDF template to include all legally required information

**Non-Goals:**
- Full WYSIWYG drag-and-drop invoice template editor (too complex; we use a structured settings approach instead)
- OCR or automatic extraction of layout/fields from uploaded PDF references
- Tax calculation engine (tax rates are configured, not auto-calculated from product categories)
- E-invoicing formats (ZUGFeRD/XRechnung) — future enhancement
- Credit notes or invoice corrections — future enhancement
- Payment tracking or dunning — out of scope

## Decisions

### 1. Template approach: Structured settings vs. WYSIWYG editor

**Decision**: Structured settings stored as a JSON configuration on a new `InvoiceTemplate` model. The Django HTML template uses these settings (logo URL, accent color, header text, footer text, legal block content) to render the PDF.

**Why not WYSIWYG**: A drag-and-drop editor is a massive frontend undertaking (canvas, element positioning, snap-to-grid). The value proposition is low — invoices have a standard structure defined by legal requirements. A settings-based approach covers 95% of customization needs.

**Why not multiple Django templates**: Maintaining separate HTML templates per tenant creates deployment/maintenance burden. A single parameterized template with CSS custom properties for theming is simpler and still flexible.

**Alternatives considered**:
- Jinja2 templates editable by users → security risk (template injection), poor UX
- Third-party invoice template services → external dependency, data leaves the system

### 2. Reference PDF uploads: Storage only, no parsing

**Decision**: Uploaded reference PDFs are stored as file attachments on the `InvoiceTemplate` model. They are displayed in the settings UI as downloadable/viewable references so users can see their existing invoice while configuring the template. No OCR or layout extraction.

**Why**: PDF parsing/OCR is unreliable, adds heavy dependencies (Tesseract, etc.), and the result would still need manual review. Showing the PDF side-by-side with a live preview achieves the same goal with far less complexity.

### 3. Invoice numbering: Pattern-based with DB-level counter

**Decision**: New `InvoiceNumberScheme` model per tenant with:
- `pattern` string with placeholders: `{YYYY}`, `{YY}`, `{MM}`, `{NNN}` (or `{NNNN}`, `{NNNNN}` for digit width)
- `next_counter` integer field, atomically incremented via `F()` expression + `select_for_update()`
- `reset_period`: `"yearly"` | `"monthly"` | `"never"`
- `last_reset_year` / `last_reset_month` to track when counter was last reset

**Pattern examples**:
- `RE-{YYYY}-{NNNN}` → `RE-2026-0001`, `RE-2026-0002`
- `INV/{YY}/{MM}/{NNN}` → `INV/26/02/001`
- `{YYYY}{MM}{NNNNN}` → `20260200001`

**Counter safety**: Use `select_for_update()` + `F('next_counter') + 1` to prevent race conditions. The counter increment and invoice record creation happen in the same transaction.

**Alternatives considered**:
- UUID-based IDs → not legally compliant (must be sequential, gap-free per German tax law)
- Application-level counter with Redis → adds infrastructure dependency, harder to guarantee gap-free

### 4. Legal data storage: Dedicated model vs. Tenant JSONField

**Decision**: New `CompanyLegalData` model with a OneToOne to Tenant, with explicit fields for each legally required datum.

**Why not JSONField on Tenant**: Explicit fields enable database-level validation, clear schema, and easier querying. The `settings` JSONField on Tenant is already used for UI preferences — mixing in legally required data with different validation needs creates confusion.

**Required fields** (per UStG §14 Abs. 4 + HGB §35a GmbH):
- `company_name` — Full legal name including legal form
- `street`, `zip_code`, `city`, `country` — Full address
- `tax_number` — Steuernummer (optional if VAT ID is provided)
- `vat_id` — USt-IdNr. (optional if tax number is provided, but at least one required)
- `commercial_register_court` — e.g., "Amtsgericht München"
- `commercial_register_number` — e.g., "HRB 12345"
- `managing_directors` — Comma-separated or JSONField list
- `bank_name`, `iban`, `bic` — Bank details (not strictly §14, but standard practice)
- `phone`, `email`, `website` — Contact (optional, common on invoices)
- `share_capital` — Stammkapital (optional, required if not fully paid in)

### 5. Invoice persistence: New InvoiceRecord model

**Decision**: New `InvoiceRecord` model that persists a generated invoice:
- Links to contract, customer, tenant
- Stores the assigned `invoice_number` (unique per tenant)
- Stores `billing_date`, `period_start`, `period_end`
- Stores `total_net`, `tax_rate`, `tax_amount`, `total_gross`
- Stores `line_items_snapshot` as JSONField (frozen copy of line items at generation time)
- Stores `status`: `draft` | `finalized` | `cancelled`
- Stores `generated_at` timestamp

**Why snapshot line items**: Contract items can change after an invoice is generated. The invoice must reflect what was billed at that point in time, not current contract state.

**Why not replace on-demand calculation**: The existing `InvoiceService.get_invoices_for_month()` remains as the calculation engine. A new "generate invoices" action calls it, assigns numbers, and persists the results. The preview/export page can still show calculated (unsaved) invoices for review before generation.

### 6. Tax handling: Simple rate configuration

**Decision**: Add `default_tax_rate` (Decimal, default 19.00) on `CompanyLegalData`. Each invoice line item calculates: `net = amount`, `tax = amount * rate / 100`, `gross = net + tax`. The rate can be overridden per invoice if needed (e.g., 7% reduced rate).

**Why not per-product tax rates**: Adds significant complexity. Most B2B software/service contracts use the standard 19% rate. Per-product rates can be added later if needed.

### 7. Frontend architecture: Settings sub-pages

**Decision**: Add three new sub-sections under the existing `/settings` route:
- `/settings/invoice-template` — Logo upload, color picker, header/footer text, reference PDF uploads, live preview
- `/settings/invoice-numbering` — Pattern input with placeholder help, counter display, reset rules
- `/settings/company-data` — Form for all legal fields with validation

The existing invoice export page (`/invoices/export`) gets updated to show invoice numbers and a "Generate & Finalize" action.

## Risks / Trade-offs

**[Gap-free numbering under concurrent generation]** → Use database-level `select_for_update()` with transaction isolation. If a transaction fails after incrementing the counter, the number is "burned" — this is acceptable per German tax law (gaps must be explainable, and a technical failure is a valid explanation). Mitigation: generate in a single transaction.

**[WeasyPrint dependency for PDF]** → Already in use. The updated template will be more complex (logo images, legal footer), which may affect rendering. Mitigation: test with various logo sizes/formats, add fallback for missing logo.

**[Migration from stateless to stateful invoices]** → Existing on-demand invoices have no history. After deployment, only newly generated invoices will have numbers/records. Mitigation: document clearly that the system starts numbering from the configured starting counter. No backfill of historical invoices.

**[File upload size for logos/reference PDFs]** → Large files could impact storage and PDF rendering performance. Mitigation: validate file size (max 5MB for logos, 20MB for reference PDFs), validate file types, resize logos on upload.

**[Legal compliance completeness]** → German invoice requirements evolve. The implementation covers UStG §14 Abs. 4 and HGB §35a GmbH as of 2026. Mitigation: use explicit model fields so adding new requirements is a simple migration.

## Open Questions

- Should the system support multiple tax rates per invoice (e.g., mixing 19% and 7% line items)? Current design uses a single rate. This could be added later as a per-line-item override.
- Should finalized invoices be immutable (no editing, only cancellation + new invoice)? Recommended yes for legal compliance, but needs user confirmation.
- What should the starting invoice number be? Users may have existing invoice sequences from another system and need to set the counter to continue from their last number.
