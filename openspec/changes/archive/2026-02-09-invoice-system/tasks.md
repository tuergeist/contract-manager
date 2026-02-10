## 1. Backend Models & Migrations

- [x] 1.1 Create `CompanyLegalData` model with OneToOne to Tenant (company_name, street, zip_code, city, country, tax_number, vat_id, commercial_register_court, commercial_register_number, managing_directors JSONField, bank_name, iban, bic, phone, email, website, share_capital, default_tax_rate)
- [x] 1.2 Create `InvoiceNumberScheme` model (tenant FK, pattern, next_counter, reset_period, last_reset_year, last_reset_month)
- [x] 1.3 Create `InvoiceTemplate` model (tenant FK, logo FileField, accent_color, header_text, footer_text)
- [x] 1.4 Create `InvoiceTemplateReference` model for uploaded reference PDFs (template FK, file FileField, filename, uploaded_at, file_size)
- [x] 1.5 Create `InvoiceRecord` model (tenant FK, contract FK, customer FK, invoice_number unique per tenant, billing_date, period_start, period_end, total_net, tax_rate, tax_amount, total_gross, line_items_snapshot JSONField, company_data_snapshot JSONField, status choices draft/finalized/cancelled, generated_at)
- [x] 1.6 Generate and run migrations for all new models
- [x] 1.7 Add validation logic: CompanyLegalData clean() requires at least one of tax_number/vat_id, requires register court+number, requires at least one managing director

## 2. Backend Invoice Numbering Service

- [x] 2.1 Create `InvoiceNumberService` with `get_next_number(tenant, billing_date)` method using select_for_update() + F() expression for atomic counter increment
- [x] 2.2 Implement pattern placeholder resolution ({YYYY}, {YY}, {MM}, {NNN}/{NNNN}/{NNNNN}) with zero-padding
- [x] 2.3 Implement counter reset logic (yearly/monthly/never) checking last_reset_year/month against billing_date
- [x] 2.4 Add default scheme creation (pattern `{YYYY}-{NNNN}`, reset yearly, counter 1) when none exists
- [x] 2.5 Write tests for numbering service: sequential generation, counter reset, concurrent safety, pattern formatting

## 3. Backend Invoice Generation Updates

- [x] 3.1 Add tax calculation to `InvoiceService`: compute net, tax_amount, gross per line item and totals using tenant's default_tax_rate
- [x] 3.2 Create `generate_and_persist(year, month)` method that calls existing `get_invoices_for_month()`, assigns numbers via InvoiceNumberService, and creates InvoiceRecord entries in a single transaction
- [x] 3.3 Add company legal data snapshot capture at generation time (store as JSON on InvoiceRecord)
- [x] 3.4 Add duplicate prevention: skip contracts that already have a finalized InvoiceRecord for the same billing period
- [x] 3.5 Add cancel invoice method: sets status to cancelled, does NOT reuse the number
- [x] 3.6 Add query method for retrieving persisted invoices by month (with status filtering)
- [x] 3.7 Write tests for invoice generation: persist flow, duplicate prevention, cancellation, tax calculations, legal data snapshot

## 4. Backend GraphQL Schema Updates

- [x] 4.1 Add CompanyLegalData GraphQL types (input + output) and mutations (save_company_legal_data, get_company_legal_data)
- [x] 4.2 Add InvoiceNumberScheme GraphQL types and mutations (save_number_scheme, get_number_scheme, preview_next_number)
- [x] 4.3 Add InvoiceTemplate GraphQL types and mutations (save_template_settings, get_template_settings, upload_logo, delete_logo)
- [x] 4.4 Add InvoiceTemplateReference mutations (upload_reference_pdf, delete_reference_pdf, list_reference_pdfs)
- [x] 4.5 Add InvoiceRecord GraphQL type and queries (invoices_for_month updated to return persisted records with numbers, invoice_history)
- [x] 4.6 Add generate_invoices mutation (calls generate_and_persist, returns created records)
- [x] 4.7 Add cancel_invoice mutation
- [x] 4.8 Add validation query: check_legal_data_complete (returns boolean + list of missing fields)
- [x] 4.9 Add permission checks: settings.write for configuration mutations, invoices.write for generate/cancel

## 5. Backend PDF Template Update

- [x] 5.1 Update invoice.html template: add invoice number display in header/details section
- [x] 5.2 Add tax breakdown section: net subtotal, tax rate + tax amount line, gross total
- [x] 5.3 Add company legal data block in header (company name, address, tax/VAT ID)
- [x] 5.4 Add GmbH legal footer: register court + number, managing directors, bank details, share capital
- [x] 5.5 Add template customization: logo image, accent color CSS variable, header text, footer text from InvoiceTemplate settings
- [x] 5.6 Add delivery/service period (Leistungszeitraum) display in invoice details
- [x] 5.7 Update `generate_pdf()` to pass template settings and legal data to the Django template context
- [x] 5.8 Add fallback rendering when no logo or template settings are configured
- [x] 5.9 Write tests for updated PDF generation: verify legal fields present, tax breakdown, invoice number, template customization

## 6. Backend File Upload Handling

- [x] 6.1 Create upload_to callables for logo files and reference PDFs (tenant-scoped paths)
- [x] 6.2 Add file validation: logo accepts PNG/JPG/SVG max 5MB, reference PDFs accept PDF max 20MB
- [x] 6.3 Add REST endpoint or GraphQL file upload for logo and reference PDFs (using multipart upload pattern from existing attachment uploads)
- [x] 6.4 Write tests for file upload: valid types accepted, invalid types rejected, size limits enforced

## 7. Frontend: Company Legal Data Settings Page

- [x] 7.1 Create CompanyDataSettings component at `/settings/company-data` with form fields for all legal data
- [x] 7.2 Add form sections: Company Identification, Tax Information, Commercial Register, Managing Directors, Bank Details, Contact Information, Share Capital
- [x] 7.3 Add client-side validation: required fields, tax ID cross-validation, IBAN format
- [x] 7.4 Add GraphQL queries and mutations for loading/saving company legal data
- [x] 7.5 Add success/error toast notifications on save
- [x] 7.6 Add German and English translations for all form labels and messages

## 8. Frontend: Invoice Number Scheme Settings Page

- [x] 8.1 Create NumberSchemeSettings component at `/settings/invoice-numbering`
- [x] 8.2 Add pattern input field with placeholder documentation/help text
- [x] 8.3 Add live preview showing example of next invoice number
- [x] 8.4 Add reset period selector (yearly/monthly/never)
- [x] 8.5 Add starting counter input with validation (min 1)
- [x] 8.6 Add GraphQL queries and mutations for loading/saving number scheme
- [x] 8.7 Add German and English translations

## 9. Frontend: Invoice Template Settings Page

- [x] 9.1 Create TemplateSettings component at `/settings/invoice-template`
- [x] 9.2 Add logo upload area with image preview and delete button
- [x] 9.3 Add accent color picker (hex input + color swatch)
- [x] 9.4 Add header text and footer text textarea fields
- [x] 9.5 Add reference PDF upload area with list of uploaded files (download/delete per file)
- [x] 9.6 Add template preview panel showing a sample invoice with current settings
- [x] 9.7 Add GraphQL queries and mutations for template settings and file uploads
- [x] 9.8 Add German and English translations

## 10. Frontend: Invoice Export Page Updates

- [x] 10.1 Update invoice preview table to show invoice number column (or "—" for ungenerated)
- [x] 10.2 Add net amount, tax amount, and gross total columns to preview table
- [x] 10.3 Add status badge column (Finalized/Cancelled/Not generated) with color coding
- [x] 10.4 Add "Generate & Finalize" button with count of ungenerated invoices
- [x] 10.5 Add confirmation dialog before generation ("Generate X invoices?")
- [x] 10.6 Add generation success feedback: refresh table, show success toast with count
- [x] 10.7 Add legal data completeness check: show error with link to settings if incomplete
- [x] 10.8 Update totals summary to show net, tax, and gross amounts
- [x] 10.9 Add German and English translations for new UI elements

## 11. Frontend: Navigation & Routing

- [x] 11.1 Add settings sub-navigation links for Company Data, Invoice Numbering, Invoice Template
- [x] 11.2 Add routes for `/settings/company-data`, `/settings/invoice-numbering`, `/settings/invoice-template`
- [x] 11.3 Ensure settings pages are permission-gated (settings.write)

## 12. Integration Testing

- [x] 12.1 Write E2E test: configure company legal data → configure number scheme → generate invoices → verify PDF contains legal fields and invoice number
- [x] 12.2 Write E2E test: upload reference PDF → configure template → preview shows customized styling
- [x] 12.3 Write E2E test: generate invoices → re-visit month → see persisted records with numbers → export PDF
