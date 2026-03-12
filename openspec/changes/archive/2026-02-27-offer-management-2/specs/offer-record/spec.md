## ADDED Requirements

### Requirement: OfferRecord persists offer data with frozen snapshots

The system SHALL store offers as `OfferRecord` instances with frozen line items, company data, and customer data captured at creation time.

#### Scenario: Offer created from billing event
- **WHEN** an offer is created from a billing schedule event
- **THEN** the system SHALL create an OfferRecord with:
  - `offer_number` assigned from OfferNumberScheme
  - `contract` and `customer` FK links
  - `offer_date` set to today
  - `valid_until` set to 30 days from today (default)
  - `billing_date`, `period_start`, `period_end` from the billing event
  - `total_net`, `tax_rate`, `tax_amount`, `total_gross` calculated
  - `line_items_snapshot` frozen from billing event items
  - `company_data_snapshot` frozen from tenant's CompanyLegalData
  - `status` set to `draft`

#### Scenario: Offer snapshots are immutable
- **WHEN** the contract's prices or company data change after offer creation
- **THEN** the offer's `line_items_snapshot` and `company_data_snapshot` SHALL remain unchanged

### Requirement: Offer status lifecycle

The system SHALL enforce the following status transitions for offers.

#### Scenario: Valid status transitions
- **GIVEN** an offer in `draft` status
- **THEN** it MAY transition to `sent` or `cancelled`
- **GIVEN** an offer in `sent` status
- **THEN** it MAY transition to `accepted`, `rejected`, or `cancelled`

#### Scenario: Expired offers
- **WHEN** an offer's `valid_until` date is in the past and status is `draft` or `sent`
- **THEN** the offer list SHALL display it with an expired visual indicator
- **AND** the offer MAY still be manually transitioned to `accepted` or `cancelled`

### Requirement: OfferNumberScheme provides configurable numbering

The system SHALL provide an `OfferNumberScheme` model with the same structure as `InvoiceNumberScheme`.

#### Scenario: Default numbering pattern
- **WHEN** no OfferNumberScheme exists for a tenant
- **THEN** the system SHALL create one with default pattern `{YYYY}-{NNNN}` and yearly reset

#### Scenario: Configurable pattern
- **WHEN** a user configures the offer number pattern in settings
- **THEN** the system SHALL support the same placeholders as invoice numbering: `{YYYY}`, `{YY}`, `{MM}`, `{NNN}`, `{NNNN}`, `{NNNNN}`

#### Scenario: Unique offer numbers per tenant
- **WHEN** an offer number is assigned
- **THEN** it SHALL be unique within the tenant (enforced by database constraint)

### Requirement: GraphQL API for offers

The system SHALL expose offer CRUD operations via GraphQL.

#### Scenario: Query single offer
- **WHEN** user queries `offer(id: Int!)`
- **THEN** the system SHALL return the full OfferRecordType if it belongs to the user's tenant, or null otherwise

#### Scenario: Query offer list
- **WHEN** user queries `offers` with optional filters (search, status, dateFrom, dateTo)
- **THEN** the system SHALL return a paginated list of offers for the user's tenant

#### Scenario: Update offer status
- **WHEN** user calls `updateOfferStatus(id, status)` with a valid transition
- **THEN** the system SHALL update the offer status
- **AND** log an audit event

#### Scenario: Update offer validity
- **WHEN** user calls `updateOffer(id, validUntil, notes)` on a draft offer
- **THEN** the system SHALL update the editable fields

#### Scenario: Delete draft offer
- **WHEN** user calls `deleteOffer(id)` on a draft offer
- **THEN** the system SHALL delete the offer record
- **WHEN** user calls `deleteOffer(id)` on a non-draft offer
- **THEN** the system SHALL return an error
