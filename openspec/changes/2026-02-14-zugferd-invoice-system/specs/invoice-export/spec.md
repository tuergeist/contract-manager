## MODIFIED Requirements

### Requirement: User can export invoices as ZUGFeRD PDF

The system SHALL allow users to export invoices as ZUGFeRD-compliant PDF/A-3 documents.

#### Scenario: Export individual ZUGFeRD PDFs
- **WHEN** user clicks "Export ZUGFeRD" button on the invoice export page
- **THEN** system generates one ZUGFeRD PDF per invoice
- **AND** packages them in a ZIP file
- **AND** file downloads with name format `invoices-zugferd-YYYY-MM.zip`

#### Scenario: Export single ZUGFeRD PDF for one invoice
- **WHEN** user exports a single invoice record as ZUGFeRD
- **THEN** system generates one PDF/A-3b with embedded `factur-x.xml`
- **AND** file downloads with name format `invoice-{number}.pdf`

#### Scenario: ZUGFeRD export requires finalized invoices
- **WHEN** user attempts ZUGFeRD export for a month with no finalized invoices
- **THEN** system displays message "ZUGFeRD export requires finalized invoices. Please generate invoices first."
- **AND** provides a link to the invoice generation action

#### Scenario: ZUGFeRD export requires company legal data
- **WHEN** user attempts ZUGFeRD export without configured company legal data
- **THEN** system displays error "Company legal data must be configured for ZUGFeRD export"
- **AND** provides a link to `/settings/company-data`

### Requirement: REST export endpoint supports ZUGFeRD format

The existing `/invoices/export/` endpoint SHALL accept ZUGFeRD as a format parameter.

#### Scenario: Export via REST API
- **WHEN** client requests `GET /invoices/export/?year=2026&month=3&format=zugferd`
- **THEN** system returns a ZIP containing individual ZUGFeRD PDFs
- **AND** response content-type is `application/zip`

#### Scenario: Export single ZUGFeRD via REST API
- **WHEN** client requests `GET /invoices/export/?year=2026&month=3&format=zugferd-single&invoice_id=123`
- **THEN** system returns a single ZUGFeRD PDF for that invoice
- **AND** response content-type is `application/pdf`

### Requirement: Tenant can configure ZUGFeRD as default PDF format

The system SHALL allow tenants to set ZUGFeRD as the default output when exporting PDFs.

#### Scenario: Enable ZUGFeRD default
- **WHEN** admin enables "ZUGFeRD als Standard-PDF-Format" in tenant settings
- **THEN** the regular "Export PDF" button produces ZUGFeRD PDFs
- **AND** the combined PDF export remains non-ZUGFeRD (with a note explaining why)

#### Scenario: Default is off
- **WHEN** the ZUGFeRD default setting is not enabled (default state)
- **THEN** the "Export PDF" button produces regular PDFs as before
- **AND** the "Export ZUGFeRD" button is available as a separate option

### Requirement: Invoice export page shows ZUGFeRD option

The frontend invoice export page SHALL display the ZUGFeRD export option.

#### Scenario: ZUGFeRD button appears
- **WHEN** user navigates to the invoice export page
- **THEN** system displays a "ZUGFeRD PDF" export button alongside "PDF", "Individual PDFs", and "Excel"

#### Scenario: Loading state during ZUGFeRD generation
- **WHEN** user clicks "ZUGFeRD PDF" export button
- **THEN** button shows loading spinner
- **AND** button is disabled until generation completes

#### Scenario: German translations
- **WHEN** user language is German
- **THEN** button label is "ZUGFeRD PDF"
- **AND** tooltip explains "Elektronische Rechnung im ZUGFeRD-Format (PDF/A-3 mit XML)"

#### Scenario: English translations
- **WHEN** user language is English
- **THEN** button label is "ZUGFeRD PDF"
- **AND** tooltip explains "Electronic invoice in ZUGFeRD format (PDF/A-3 with XML)"
