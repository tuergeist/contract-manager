## MODIFIED Requirements

### Requirement: User can preview invoices before export

The system SHALL display a preview table of all invoices before exporting. Each invoice row SHALL include a button to open an HTML preview of the rendered invoice.

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

#### Scenario: Preview button opens rendered invoice
- **WHEN** user clicks the preview icon on an invoice row
- **THEN** a dialog opens showing the full rendered HTML invoice
- **AND** the row click (expand/collapse) is not triggered
