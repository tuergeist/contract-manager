## MODIFIED Requirements

### Requirement: Invoice detail page displays invoice metadata

The system SHALL provide a detail page at `/invoices/:id` that detects the invoice type (generated or imported) and renders the appropriate detail view. For generated invoices (`InvoiceRecord`), the page SHALL display the full metadata including invoice number, billing date, invoice date, period, amounts (net, tax, gross), tax rate, status, and generation timestamp. The `type` query parameter (`generated` or `imported`) MAY be used to specify the invoice type; if omitted, the page SHALL try the generated invoice query first, then fall back to imported.

#### Scenario: User navigates to generated invoice detail
- **WHEN** user navigates to `/invoices/123`
- **THEN** the page SHALL load the generated invoice record with id 123
- **AND** show invoice number, billing date, invoice date, period start/end, total net, tax rate, tax amount, total gross, status, and generated-at timestamp

#### Scenario: User navigates to imported invoice detail
- **WHEN** user navigates to `/invoices/456?type=imported`
- **THEN** the page SHALL load the imported invoice with id 456 and render the imported invoice detail view

#### Scenario: Auto-detection fallback
- **WHEN** user navigates to `/invoices/456` without a `type` parameter and no generated invoice with id 456 exists
- **THEN** the page SHALL attempt to load an imported invoice with id 456

#### Scenario: Invoice not found
- **WHEN** user navigates to `/invoices/999` and no record exists with that id in either type
- **THEN** the page SHALL display an error message indicating the invoice was not found

### Requirement: Existing pages link to invoice detail

Invoice numbers on the invoice list, export page, and contract detail invoices tab SHALL be clickable links navigating to the invoice detail page. Both generated and imported invoices in the list SHALL link to the detail page.

#### Scenario: Invoice number links on export page
- **WHEN** user views the invoice export page with generated records
- **THEN** each invoice number SHALL be a link to `/invoices/:id`

#### Scenario: Invoice number links on contract detail
- **WHEN** user views the invoices tab on a contract detail page
- **THEN** each generated invoice number SHALL be a link to `/invoices/:id`

#### Scenario: Imported invoice links on invoice list
- **WHEN** user views the invoice list showing imported invoices
- **THEN** each imported invoice number SHALL be a link to `/invoices/:id?type=imported`

#### Scenario: Generated invoice links on invoice list
- **WHEN** user views the invoice list showing generated invoices
- **THEN** each generated invoice number SHALL be a link to `/invoices/:id`
