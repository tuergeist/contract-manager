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

Each generated invoice SHALL include all information needed for customer billing and accounting.

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
