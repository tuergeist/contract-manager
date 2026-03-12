## ADDED Requirements

### Requirement: Contract has a deal won date field
The Contract model SHALL have an optional `deal_won_date` DateField to record when the deal was won.

#### Scenario: Field is nullable
- **WHEN** a contract is created manually (without HubSpot)
- **THEN** `deal_won_date` SHALL be null

#### Scenario: Field stores a date
- **WHEN** a contract is imported from HubSpot with closedate 2026-03-15
- **THEN** `deal_won_date` SHALL be set to 2026-03-15

#### Scenario: Field is editable
- **WHEN** a user edits a contract
- **THEN** `deal_won_date` SHALL be editable as an optional date field

### Requirement: HubSpot sync populates deal won date
When importing a closedwon deal from HubSpot, the system SHALL set `deal_won_date` from the deal's `closedate` property.

#### Scenario: New deal import sets deal_won_date
- **WHEN** a HubSpot deal with closedate=2026-06-01 is imported
- **THEN** the created contract SHALL have `deal_won_date` = 2026-06-01

#### Scenario: Missing closedate defaults to today
- **WHEN** a HubSpot deal has no closedate property
- **THEN** `deal_won_date` SHALL be set to the current date

### Requirement: Backfill deal won date for existing HubSpot contracts
A data migration SHALL set `deal_won_date = start_date` for all existing contracts that have a `hubspot_deal_id` but no `deal_won_date`.

#### Scenario: Existing HubSpot contract gets backfilled
- **WHEN** the migration runs on a contract with hubspot_deal_id="12345" and start_date=2025-09-01
- **THEN** `deal_won_date` SHALL be set to 2025-09-01

#### Scenario: Non-HubSpot contracts are not backfilled
- **WHEN** the migration runs on a contract with hubspot_deal_id=null
- **THEN** `deal_won_date` SHALL remain null

#### Scenario: Already-set deal_won_date is not overwritten
- **WHEN** the migration runs on a contract that already has deal_won_date set
- **THEN** `deal_won_date` SHALL not be changed

### Requirement: Contract exposes is_new_business flag
The system SHALL expose an `is_new_business` boolean derived from the presence of `hubspot_deal_id`.

#### Scenario: HubSpot-imported contract is new business
- **WHEN** a contract has hubspot_deal_id="12345"
- **THEN** `is_new_business` SHALL be true

#### Scenario: Manually created contract is existing business
- **WHEN** a contract has hubspot_deal_id=null
- **THEN** `is_new_business` SHALL be false

#### Scenario: GraphQL exposes the field
- **WHEN** querying a contract via GraphQL
- **THEN** the `isNewBusiness` field SHALL be available on ContractType

### Requirement: GraphQL exposes deal_won_date
The ContractType SHALL expose `dealWonDate` as a readable and writable field.

#### Scenario: Query returns deal won date
- **WHEN** querying a contract with deal_won_date=2026-03-15
- **THEN** the GraphQL response SHALL include `dealWonDate: "2026-03-15"`

#### Scenario: Mutation can set deal won date
- **WHEN** updating a contract with dealWonDate="2026-04-01"
- **THEN** the contract's deal_won_date SHALL be updated to 2026-04-01
