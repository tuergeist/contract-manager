## ADDED Requirements

### Requirement: Customer has an optional VAT ID field

The Customer model SHALL have an optional `vat_id` field (max 50 characters) for storing the customer's VAT registration number (e.g., "DE123456789").

#### Scenario: Customer created without VAT ID
- **WHEN** a customer is created without providing a VAT ID
- **THEN** the `vat_id` field SHALL default to an empty string
- **AND** the customer is created successfully

#### Scenario: Customer created with VAT ID
- **WHEN** a customer is created with `vat_id: "DE123456789"`
- **THEN** the `vat_id` field SHALL store the value as-is
- **AND** no format validation is applied

#### Scenario: Customer VAT ID updated
- **WHEN** a user updates a customer's VAT ID via GraphQL mutation
- **THEN** the new value SHALL be persisted
- **AND** existing invoices are not affected

### Requirement: VAT ID is exposed in GraphQL API

The GraphQL CustomerType SHALL expose `vat_id` as a readable field, and create/update mutations SHALL accept it as an optional input.

#### Scenario: Query customer with VAT ID
- **WHEN** a user queries a customer via GraphQL
- **THEN** the response SHALL include the `vat_id` field

#### Scenario: Update customer VAT ID via mutation
- **WHEN** a user calls the update customer mutation with `vatId: "ATU12345678"`
- **THEN** the customer's `vat_id` SHALL be updated to "ATU12345678"

### Requirement: VAT ID synced from HubSpot

When syncing customers from HubSpot, the system SHALL map the HubSpot `vatid` company property to the Customer `vat_id` field.

#### Scenario: HubSpot customer has VAT ID
- **WHEN** a customer is synced from HubSpot
- **AND** the HubSpot company has property `vatid` set to "DE999888777"
- **THEN** the Customer `vat_id` SHALL be set to "DE999888777"

#### Scenario: HubSpot customer has no VAT ID
- **WHEN** a customer is synced from HubSpot
- **AND** the HubSpot company has no `vatid` property
- **THEN** the Customer `vat_id` SHALL remain unchanged (not cleared)

### Requirement: VAT ID editable in frontend customer detail

The customer detail page SHALL display the VAT ID field and allow editing it inline.

#### Scenario: VAT ID displayed on customer detail
- **WHEN** a user views a customer detail page
- **THEN** the VAT ID field SHALL be visible in the customer information section
- **AND** it SHALL show the current value or be empty if not set

#### Scenario: VAT ID edited inline
- **WHEN** a user edits the VAT ID field on the customer detail page
- **AND** saves the change
- **THEN** the updated VAT ID SHALL be persisted via the update customer mutation
