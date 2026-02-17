## MODIFIED Requirements

### Requirement: User can access invoice export page
The system SHALL provide access to the invoice export page via a button on the Invoices page. The invoice export page SHALL remain at `/invoices/export` but SHALL NOT have a dedicated sidebar navigation entry.

#### Scenario: Navigate to invoice export from invoices page
- **WHEN** user views the Invoices page
- **THEN** an "Export" button is displayed in the page header
- **AND** clicking the button navigates to `/invoices/export`

#### Scenario: Export button requires permission
- **WHEN** user without `invoices.export` permission views the Invoices page
- **THEN** the "Export" button is not displayed

#### Scenario: Page requires authentication
- **WHEN** unauthenticated user accesses `/invoices/export`
- **THEN** system redirects to login page

## REMOVED Requirements

### Requirement: Invoice export has dedicated sidebar entry
**Reason**: Invoice export is now accessed from the Invoices page header button instead of a separate sidebar entry.
**Migration**: Users navigate to Invoices page and click "Export" button.
