## ADDED Requirements

### Requirement: Offer list page displays all offers

The system SHALL provide an offer list page at `/offers` displaying all offers for the current tenant.

#### Scenario: List displays offer summary
- **WHEN** user navigates to `/offers`
- **THEN** the page SHALL display a table with columns: offer number, customer, contract, offer date, valid until, total gross, status
- **AND** offers SHALL be sorted by offer date descending by default

#### Scenario: Search and filter
- **WHEN** user enters text in the search field
- **THEN** the list SHALL filter by offer number, customer name, or contract name
- **WHEN** user selects a status filter
- **THEN** only offers with that status SHALL be shown

#### Scenario: Pagination
- **WHEN** there are more offers than the page size
- **THEN** the list SHALL paginate with page controls

#### Scenario: Expired indicator
- **WHEN** an offer's `valid_until` is in the past and status is `draft` or `sent`
- **THEN** the row SHALL display a visual expired indicator (e.g., red badge or text color)

#### Scenario: Click navigates to detail
- **WHEN** user clicks an offer row
- **THEN** the page SHALL navigate to `/offers/:id`

### Requirement: Offer detail page displays full offer data

The system SHALL provide an offer detail page at `/offers/:id`.

#### Scenario: Detail shows metadata
- **WHEN** user navigates to `/offers/123`
- **THEN** the page SHALL display: offer number, offer date, valid until, status, customer (linked), contract (linked), billing period, notes

#### Scenario: Detail shows line items
- **WHEN** user views an offer detail
- **THEN** the page SHALL display the line items from `line_items_snapshot` in a table matching the PDF layout

#### Scenario: Detail shows PDF preview
- **WHEN** the offer has a `pdf_file`
- **THEN** the page SHALL embed the PDF for inline viewing
- **AND** provide a "Download PDF" button

#### Scenario: Status change actions
- **WHEN** user views a draft offer
- **THEN** "Send" and "Cancel" buttons SHALL be available
- **WHEN** user views a sent offer
- **THEN** "Mark Accepted", "Mark Rejected", and "Cancel" buttons SHALL be available

#### Scenario: Delete draft offer
- **WHEN** user views a draft offer
- **THEN** a "Delete" button SHALL be available with confirmation dialog

#### Scenario: Offer not found
- **WHEN** user navigates to `/offers/999` and no offer exists
- **THEN** the page SHALL display an error message

### Requirement: Navigation includes offers

The system SHALL add an "Offers" entry to the main navigation.

#### Scenario: Nav entry visible
- **WHEN** user has permissions to view offers
- **THEN** the main navigation SHALL include an "Offers" / "Angebote" link to `/offers`
