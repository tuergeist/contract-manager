## ADDED Requirements

### Requirement: User can access invoice export page

The system SHALL provide an invoice export page accessible from the main navigation.

#### Scenario: Navigate to invoice export
- **WHEN** user clicks "Invoice Export" in navigation
- **THEN** system displays the invoice export page at `/invoices/export`
- **AND** page shows a month/year picker defaulting to current month

#### Scenario: Page requires authentication
- **WHEN** unauthenticated user accesses `/invoices/export`
- **THEN** system redirects to login page

### Requirement: User can select target month for invoice generation

The system SHALL allow users to select a specific month and year for invoice generation.

#### Scenario: Select month and year
- **WHEN** user selects "March 2026" from the month picker
- **THEN** system loads invoices due in March 2026
- **AND** displays them in a preview table with at least contract name, customer name, total invoice amount

#### Scenario: Default to current month
- **WHEN** user first loads the invoice export page
- **THEN** month picker defaults to current month and year
- **AND** invoices for current month are automatically loaded

### Requirement: User can preview invoices before export

The system SHALL display a preview table of all invoices before exporting.

#### Scenario: Preview shows invoice summary
- **WHEN** invoices are loaded for selected month
- **THEN** preview table shows: customer name, contract name, billing date, total amount, number of line items
- **AND** invoices are sorted by customer name

#### Scenario: Preview shows totals
- **WHEN** preview table is displayed
- **THEN** system shows total number of invoices and sum of all invoice amounts

#### Scenario: Expand invoice to see line items
- **WHEN** user clicks on an invoice row in preview
- **THEN** system expands to show all line items with product, quantity, unit price, and amount

#### Scenario: Empty state when no invoices
- **WHEN** selected month has no invoices
- **THEN** system displays "No invoices for this month" message
- **AND** export buttons are disabled

### Requirement: User can export invoices as PDF

The system SHALL allow users to export invoices as PDF files.

#### Scenario: Export single combined PDF
- **WHEN** user clicks "Export PDF" button
- **THEN** system generates a single PDF containing all invoices
- **AND** each invoice starts on a new page
- **AND** file downloads with name format `invoices-YYYY-MM.pdf`

#### Scenario: Export individual PDFs as ZIP
- **WHEN** user clicks "Export Individual PDFs"
- **THEN** system generates one PDF per invoice
- **AND** PDFs are packaged in a ZIP file
- **AND** each PDF is named `invoice-{customer}-{contract}-YYYY-MM.pdf`
- **AND** ZIP file downloads with name format `invoices-YYYY-MM.zip`

#### Scenario: PDF contains complete invoice information
- **WHEN** a PDF invoice is generated
- **THEN** it SHALL include: company header, customer billing address, invoice date, billing period, line items table, subtotal, and total amount

### Requirement: User can export invoices as Excel

The system SHALL allow users to export all invoices as an Excel spreadsheet.

#### Scenario: Export Excel file
- **WHEN** user clicks "Export Excel" button
- **THEN** system generates an Excel file with multiple sheets
- **AND** file downloads with name format `invoices-YYYY-MM.xlsx`

#### Scenario: Excel contains Summary sheet
- **WHEN** Excel file is generated
- **THEN** "Summary" sheet contains: total invoices count, total amount, breakdown by customer

#### Scenario: Excel contains Invoices sheet
- **WHEN** Excel file is generated
- **THEN** "Invoices" sheet contains one row per invoice: customer, contract, date, total

#### Scenario: Excel contains Line Items sheet
- **WHEN** Excel file is generated
- **THEN** "Line Items" sheet contains one row per line item: customer, contract, product, quantity, unit price, amount
- **AND** rows are grouped by invoice

### Requirement: Export shows loading state

The system SHALL provide feedback during export generation.

#### Scenario: Loading indicator during export
- **WHEN** user initiates an export
- **THEN** system shows loading spinner on the export button
- **AND** button is disabled until export completes

#### Scenario: Error handling for failed export
- **WHEN** export generation fails
- **THEN** system displays error message to user
- **AND** user can retry the export

### Requirement: Invoice export supports localization

The system SHALL display the invoice export page in German and English.

#### Scenario: German translations
- **WHEN** user language is German
- **THEN** all labels, buttons, and messages display in German

#### Scenario: English translations
- **WHEN** user language is English
- **THEN** all labels, buttons, and messages display in English

#### Scenario: PDF content matches user language
- **WHEN** user exports PDF with German language setting
- **THEN** PDF labels and headers are in German
