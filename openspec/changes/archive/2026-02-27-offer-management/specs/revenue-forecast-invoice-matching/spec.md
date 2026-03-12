## MODIFIED Requirements

### Requirement: Forecast rows include offer creation action

Each billing event row in the revenue forecast tab SHALL include a "Create Offer" action.

#### Scenario: Create offer button on forecast row
- **WHEN** user views the revenue forecast tab for any contract (draft or active)
- **THEN** each billing event row SHALL display a "Create Offer" button/icon

#### Scenario: Create offer navigates to offer detail
- **WHEN** user clicks "Create Offer" on a forecast row
- **THEN** the system SHALL call the `createOffer` mutation with the contract ID and billing date
- **AND** on success, navigate to the newly created offer's detail page (`/offers/:id`)

#### Scenario: Existing offer linked
- **WHEN** an offer already exists for a contract + billing date combination
- **THEN** the forecast row SHALL show a link to the existing offer instead of a "Create Offer" button
