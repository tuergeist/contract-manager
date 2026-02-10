## MODIFIED Requirements

### Requirement: Invoice includes complete billing details

Each generated invoice SHALL include all information needed for customer billing and accounting, including tax calculations and an assigned invoice number.

#### Scenario: Invoice contains required fields
- **WHEN** an invoice is generated
- **THEN** it SHALL include: customer name, customer address, contract name, billing date, line items with product/description/quantity/unit price/net amount, tax rate, tax amount per line item, gross total, invoice number, and billing period covered

#### Scenario: Invoice respects item-level billing dates
- **WHEN** a contract item has a custom billing_start_date or billing_end_date
- **THEN** the item is only included in invoices within its billing period
- **AND** items outside their billing period are excluded

#### Scenario: Invoice handles prorated items
- **WHEN** a contract item has align_to_contract_at set
- **THEN** the first billing period is prorated
- **AND** the prorated amount and factor are included in the line item

#### Scenario: Invoice includes tax breakdown
- **WHEN** an invoice is generated
- **THEN** each line item includes net amount
- **AND** the invoice shows total net, tax rate, total tax amount, and gross total

## ADDED Requirements

### Requirement: User can generate and persist invoices

The system SHALL allow users to generate invoices from calculated billing data, assign sequential numbers, and persist them as records.

#### Scenario: Generate invoices for a month
- **WHEN** user reviews calculated invoices for a month on the export page
- **AND** clicks "Generate & Finalize"
- **THEN** system assigns sequential invoice numbers to each invoice
- **AND** persists them as InvoiceRecord entries with status "finalized"
- **AND** stores a snapshot of line items at generation time

#### Scenario: Preview before generating
- **WHEN** user selects a month on the export page
- **THEN** system shows calculated (unsaved) invoices for review
- **AND** user can review totals and line items before generating

#### Scenario: Generated invoices are immutable
- **WHEN** an invoice has been finalized
- **THEN** its data (line items, amounts, invoice number) SHALL NOT be editable
- **AND** to correct an error, the invoice must be cancelled and a new one generated

#### Scenario: Cancel a finalized invoice
- **WHEN** user cancels a finalized invoice
- **THEN** its status changes to "cancelled"
- **AND** the invoice number is NOT reused
- **AND** the invoice remains visible in history with "cancelled" status

### Requirement: Generated invoices include company legal data

Each persisted invoice SHALL include the tenant's company legal data as it was at generation time.

#### Scenario: Legal data snapshot at generation
- **WHEN** invoices are generated
- **THEN** system captures a snapshot of the company's legal data (name, address, tax IDs, register info)
- **AND** stores it with the invoice record
- **AND** later changes to company data do not affect already-generated invoices

### Requirement: User can view invoice history

The system SHALL display previously generated invoices.

#### Scenario: View past invoices
- **WHEN** user selects a month that has already been generated
- **THEN** system shows the persisted invoice records with their assigned numbers
- **AND** distinguishes them from newly calculated (ungenerated) invoices

#### Scenario: Re-export generated invoices
- **WHEN** user exports a month with already-generated invoices
- **THEN** PDFs use the persisted data and assigned invoice numbers
- **AND** the output is consistent regardless of current contract state

### Requirement: Duplicate generation prevention

The system SHALL prevent generating duplicate invoices for the same contract and billing period.

#### Scenario: Prevent duplicate generation
- **WHEN** user attempts to generate invoices for a month that has already been fully generated
- **THEN** system shows a message that invoices for this period already exist
- **AND** does not create duplicate records

#### Scenario: Generate for new contracts only
- **WHEN** invoices for a month were previously generated
- **AND** a new contract now has billing events in that month
- **THEN** system generates invoices only for the new contract
- **AND** existing invoices remain unchanged
