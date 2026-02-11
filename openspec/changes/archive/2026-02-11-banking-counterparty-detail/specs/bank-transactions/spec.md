## MODIFIED Requirements

### Requirement: User can view transactions in a paginated table
The system SHALL display bank transactions in a table with columns: date, counterparty name, booking text, amount, and bank account name. The table SHALL be paginated with 50 rows per page. The counterparty name column SHALL be rendered as a clickable link that navigates to the counterparty detail view at `/banking/counterparty/:name`.

#### Scenario: View transaction table
- **WHEN** user navigates to the banking page and selects "all accounts"
- **THEN** the system displays transactions from all accounts, sorted by entry date descending (newest first)

#### Scenario: Pagination
- **WHEN** there are 200 transactions and user is on page 1
- **THEN** the system shows transactions 1-50 and indicates 4 pages total

#### Scenario: Click counterparty name
- **WHEN** user clicks on "BG Verkehr" in the counterparty column
- **THEN** the browser navigates to `/banking/counterparty/BG%20Verkehr`
