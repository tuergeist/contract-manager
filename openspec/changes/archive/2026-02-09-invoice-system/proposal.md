## Why

The existing invoice system generates invoices on-demand from contract billing schedules with a hardcoded HTML template, no invoice numbering, and incomplete legal metadata. To use these invoices in real business operations, they must comply with German HGB/UStG requirements for GmbH invoices — including sequential numbering, tax information, and mandatory company details. Users also need the ability to customize the invoice layout based on their existing invoice designs.

## What Changes

- **Invoice template management**: Users can upload one or more existing invoice PDFs as visual reference, then configure an editable invoice template (logo, colors, header/footer text, field placement) that the system uses for PDF generation
- **Invoice number scheme**: Configurable number pattern supporting static text, date components, and an auto-incrementing counter (e.g., `RE-2026-0001`, `INV/{YYYY}/{NNN}`). Each generated invoice receives a unique, sequential number
- **Persistent invoice records**: Invoices transition from purely on-demand calculation to persisted records with assigned numbers, generation timestamps, and status tracking
- **German legal compliance (HGB/UStG §14)**: Tenant-level configuration for all legally required invoice data:
  - Company name with legal form (e.g., "Firma GmbH")
  - Full company address
  - Tax number (Steuernummer) and/or VAT ID (USt-IdNr.)
  - Commercial register entry (Amtsgericht + HRB number)
  - Managing directors (Geschäftsführer)
  - Bank details (IBAN, BIC, bank name)
  - Delivery/service date on each invoice
  - Net amount, tax rate, tax amount, gross amount per line item
  - Optional: Stammkapital (share capital)
- **Updated PDF template**: The generated invoice PDF includes all legally required fields, uses the configured template styling, and prints the assigned invoice number

## Capabilities

### New Capabilities
- `invoice-templates`: Upload reference invoices (PDF), configure editable invoice template (logo, branding, layout, header/footer), preview template with sample data
- `invoice-numbering`: Define number scheme patterns with placeholders ({YYYY}, {MM}, {NNN}), auto-incrementing counter, uniqueness enforcement, reset rules (yearly/never)
- `invoice-legal-compliance`: Tenant-level settings for all German HGB/UStG §14 mandatory fields (company data, tax IDs, register info, managing directors, bank details), validation that invoices include all required data before export

### Modified Capabilities
- `invoice-generation`: Invoices are now persisted with assigned numbers and legal data; generation creates database records instead of purely ephemeral calculations
- `invoice-export`: PDF export uses the configured template and includes all legal fields; invoice number appears on exported documents

## Impact

- **Backend**: New models (InvoiceRecord, InvoiceTemplate, InvoiceNumberScheme, CompanyLegalData), new migrations, file upload handling for reference PDFs and logos, updated PDF generation to use template + legal data
- **Frontend**: New settings pages for template configuration, number scheme setup, and legal data entry; updated invoice export page to show invoice numbers; template preview component
- **Database**: New tables for persisted invoices and configuration; migration from stateless to stateful invoice tracking
- **Dependencies**: May need additional PDF/image processing library for logo handling
- **API**: New GraphQL mutations for template/numbering/legal data CRUD; updated invoice queries to return persisted records with numbers
