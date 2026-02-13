## ADDED Requirements

### Requirement: System calculates invoices due in a given month

The system SHALL calculate all invoices due for a specified month by aggregating billing events from all active contracts within the tenant.

#### Scenario: Invoices calculated for month with active contracts
- **WHEN** user requests invoices for January 2026
- **THEN** system returns all billing events scheduled for January 2026 across all active contracts
- **AND** each invoice includes contract ID, customer info, billing date, and line items

#### Scenario: Invoices filtered by contract status
- **WHEN** user requests invoices for a month
- **THEN** system only includes invoices from contracts with status "active"
- **AND** draft, paused, cancelled, and ended contracts are excluded

#### Scenario: No invoices in requested month
- **WHEN** user requests invoices for a month with no billing events
- **THEN** system returns an empty list
- **AND** no error is raised

### Requirement: Invoice includes complete billing details

Each generated invoice SHALL include all information needed for customer billing and accounting, including contract metadata such as invoice text, PO number, and order confirmation number.

#### Scenario: Invoice contains required fields
- **WHEN** an invoice is generated
- **THEN** it SHALL include: customer name, customer address, contract name, billing date, line items with product/description/quantity/unit price/total, invoice total, and billing period covered

#### Scenario: Invoice respects item-level billing dates
- **WHEN** a contract item has a custom billing_start_date or billing_end_date
- **THEN** the item is only included in invoices within its billing period
- **AND** items outside their billing period are excluded

#### Scenario: Invoice handles prorated items
- **WHEN** a contract item has align_to_contract_at set
- **THEN** the first billing period is prorated
- **AND** the prorated amount and factor are included in the line item

#### Scenario: Invoice PDF shows PO number when present
- **WHEN** the contract has a PO number set
- **THEN** the invoice PDF metadata section SHALL display the PO number with label "Bestellnummer" (DE) or "PO Number" (EN)

#### Scenario: Invoice PDF shows order confirmation number when present
- **WHEN** the contract has an order confirmation number set
- **THEN** the invoice PDF metadata section SHALL display it with label "Auftragsbestätigung" (DE) or "Order Confirmation" (EN)

#### Scenario: Invoice PDF shows invoice text when present
- **WHEN** the contract has invoice_text set
- **THEN** the invoice PDF SHALL render the text below the totals section, before the footer

#### Scenario: Invoice PDF omits empty metadata fields
- **WHEN** the contract has no PO number, no order confirmation number, or no invoice text
- **THEN** the corresponding sections SHALL not appear on the PDF

#### Scenario: Invoice preview includes metadata fields
- **WHEN** a preview PDF is generated
- **THEN** it SHALL include sample PO number, order confirmation number, and invoice text to demonstrate the layout

### Requirement: Invoice generation is tenant-scoped

The system SHALL only return invoices for contracts belonging to the current user's tenant.

#### Scenario: Multi-tenant isolation
- **WHEN** user from Tenant A requests invoices
- **THEN** only contracts from Tenant A are included
- **AND** contracts from other tenants are never visible

### Requirement: One-off items billed only once

One-off contract items SHALL appear in exactly one invoice at their billing start date.

#### Scenario: One-off item included once
- **WHEN** a contract has a one-off item with billing_start_date in January 2026
- **THEN** the item appears in January 2026 invoice only
- **AND** does not appear in subsequent months

#### Scenario: One-off item with past billing date
- **WHEN** user requests invoices for February 2026
- **AND** a one-off item has billing_start_date in January 2026
- **THEN** the one-off item is not included in February invoice
