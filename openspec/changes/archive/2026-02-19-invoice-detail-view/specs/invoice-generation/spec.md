## ADDED Requirements

### Requirement: Single invoice record query by ID

The GraphQL API SHALL provide an `invoice_record(id: Int!)` query that returns a single invoice record with all related data including payment matches.

#### Scenario: Fetch existing invoice record
- **WHEN** user queries `invoice_record(id: 123)` and a record with that ID exists in their tenant
- **THEN** the system SHALL return the full InvoiceRecordType including payment matches, email fields, and pdf_url

#### Scenario: Invoice record not found
- **WHEN** user queries `invoice_record(id: 999)` and no record exists with that ID in their tenant
- **THEN** the system SHALL return null

#### Scenario: Invoice record belongs to different tenant
- **WHEN** user queries `invoice_record(id: 123)` and the record belongs to a different tenant
- **THEN** the system SHALL return null
- **AND** no data from the other tenant SHALL be exposed
