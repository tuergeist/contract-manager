## Requirements

### Requirement: User can preview a rendered invoice as HTML

The system SHALL provide an HTML preview of each invoice on the export page, showing the full rendered invoice layout with all data except the invoice number.

#### Scenario: Preview button on each invoice row
- **WHEN** the invoice preview table is displayed on `/invoices/export`
- **THEN** each invoice row SHALL display a preview icon/button
- **AND** the button SHALL be clickable without toggling the row expansion

#### Scenario: Open invoice preview dialog
- **WHEN** user clicks the preview button on an invoice row
- **THEN** a dialog opens displaying the rendered invoice as HTML
- **AND** the dialog is large enough to show A4-format content readably

#### Scenario: Preview shows all invoice data except invoice number
- **WHEN** the preview dialog is open
- **THEN** the rendered invoice SHALL include: company header with logo, customer billing address, billing date, billing period, line items table with position/description/quantity/unit price/amount, subtotal, tax, gross total, PO number (if present), order confirmation number (if present), invoice text (if present), and legal footer
- **AND** the invoice number SHALL NOT be displayed (it is assigned only upon generation)

#### Scenario: Preview uses per-customer language
- **WHEN** a customer has an `invoice_language` configured
- **THEN** the preview SHALL render labels and formatting in that customer's language
- **WHEN** a customer has no `invoice_language` set
- **THEN** the preview SHALL use the company's default language

#### Scenario: Preview matches PDF template styling
- **WHEN** the tenant has customized invoice template settings (accent color, header text, footer text, logo)
- **THEN** the preview SHALL reflect those customizations, matching the PDF output

#### Scenario: Preview for generated invoice shows invoice number
- **WHEN** the invoice has already been generated (has a finalized InvoiceRecord)
- **THEN** the preview SHALL include the assigned invoice number

#### Scenario: Loading state while preview loads
- **WHEN** user clicks the preview button
- **THEN** the dialog SHALL show a loading indicator until the HTML content is ready

#### Scenario: Preview dialog can be closed
- **WHEN** the preview dialog is open
- **THEN** the user can close it by clicking a close button or pressing Escape
- **AND** the underlying export page state is preserved

### Requirement: REST endpoint returns rendered invoice HTML

The system SHALL provide a REST endpoint that returns a single invoice rendered as HTML.

#### Scenario: Request preview HTML for a specific contract
- **WHEN** client requests `GET /api/invoices/preview-html/?year=2026&month=3&contract_id=42`
- **THEN** system returns the rendered invoice HTML with content-type `text/html`
- **AND** the response is a complete HTML document suitable for iframe rendering

#### Scenario: Invoice number included for generated invoices
- **WHEN** the requested contract has a finalized InvoiceRecord for the given month
- **THEN** the rendered HTML SHALL include the invoice number

#### Scenario: Invoice number omitted for ungenerated invoices
- **WHEN** the requested contract has no finalized InvoiceRecord for the given month
- **THEN** the rendered HTML SHALL omit the invoice number

#### Scenario: Authentication required
- **WHEN** an unauthenticated user requests the preview endpoint
- **THEN** system returns HTTP 401

#### Scenario: Permission required
- **WHEN** user without `invoices.export` permission requests the preview endpoint
- **THEN** system returns HTTP 403

#### Scenario: Contract not found for month
- **WHEN** the requested contract has no invoice data for the given month
- **THEN** system returns HTTP 404 with an error message

#### Scenario: Tax calculation matches export
- **WHEN** the preview is rendered
- **THEN** the tax calculation (domestic vs reverse charge) SHALL match the logic used in PDF export
