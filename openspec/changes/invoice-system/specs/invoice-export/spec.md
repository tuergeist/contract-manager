## MODIFIED Requirements

### Requirement: User can export invoices as PDF

The system SHALL allow users to export invoices as PDF files using the configured template and including all legal fields.

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

#### Scenario: PDF contains complete invoice information with legal fields
- **WHEN** a PDF invoice is generated
- **THEN** it SHALL include: configured company logo, company name and address, tax number or VAT ID, customer billing address, invoice number, invoice date, delivery/service period, line items table with net amounts, tax rate and tax amount, gross total, and GmbH legal footer (register, directors, bank details)

#### Scenario: PDF uses configured template
- **WHEN** a PDF invoice is generated
- **AND** template settings have been configured (logo, accent color, header/footer text)
- **THEN** the PDF uses the configured styling

#### Scenario: PDF uses default template
- **WHEN** a PDF invoice is generated
- **AND** no template settings have been configured
- **THEN** the PDF uses the default template styling

### Requirement: User can preview invoices before export

The system SHALL display a preview table of all invoices before exporting, including invoice numbers for generated invoices.

#### Scenario: Preview shows invoice summary with numbers
- **WHEN** invoices are loaded for selected month
- **THEN** preview table shows: invoice number (if generated), customer name, contract name, billing date, total net amount, tax amount, total gross amount, number of line items
- **AND** invoices are sorted by customer name

#### Scenario: Preview distinguishes generated vs. calculated invoices
- **WHEN** preview table is displayed
- **AND** some invoices have been previously generated
- **THEN** generated invoices show their assigned invoice number
- **AND** ungenerated invoices show a placeholder (e.g., "—" or "Not yet generated")

#### Scenario: Preview shows totals
- **WHEN** preview table is displayed
- **THEN** system shows total number of invoices, sum of net amounts, sum of tax amounts, and sum of gross amounts

## ADDED Requirements

### Requirement: User can generate and finalize invoices from export page

The system SHALL provide a "Generate & Finalize" action on the invoice export page.

#### Scenario: Generate button available
- **WHEN** there are ungenerated invoices for the selected month
- **THEN** system shows a "Generate & Finalize" button
- **AND** the button indicates how many invoices will be generated

#### Scenario: Generate button disabled when all generated
- **WHEN** all invoices for the selected month have already been generated
- **THEN** the "Generate & Finalize" button is disabled or hidden
- **AND** a message indicates all invoices are already generated

#### Scenario: Generation confirmation
- **WHEN** user clicks "Generate & Finalize"
- **THEN** system shows a confirmation dialog with the number of invoices to be generated
- **AND** user must confirm before invoices are finalized

#### Scenario: Generation success
- **WHEN** user confirms generation
- **THEN** system generates and persists all ungenerated invoices
- **AND** assigns sequential invoice numbers
- **AND** refreshes the preview table to show the assigned numbers
- **AND** shows a success message with the number of invoices generated

### Requirement: Export page shows invoice status indicators

The system SHALL visually indicate the status of each invoice in the preview table.

#### Scenario: Finalized invoice indicator
- **WHEN** an invoice has status "finalized"
- **THEN** it shows a visual indicator (e.g., green badge) with status "Finalized"

#### Scenario: Cancelled invoice indicator
- **WHEN** an invoice has status "cancelled"
- **THEN** it shows a visual indicator (e.g., red badge) with status "Cancelled"
- **AND** cancelled invoices are visually distinct (e.g., strikethrough or muted)

#### Scenario: Ungenerated invoice indicator
- **WHEN** an invoice has not been generated yet
- **THEN** it shows a visual indicator (e.g., gray badge) with status "Draft" or "Not generated"
