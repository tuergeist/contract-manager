## ADDED Requirements

### Requirement: Transaction displays matched invoice info
The system SHALL display matched invoice information on credit transactions that have payment matches.

#### Scenario: Transaction with invoice match
- **WHEN** viewing a credit transaction that is matched to invoice "RE-2025-001234"
- **THEN** system displays invoice number, customer name, and match type (auto/manual)

#### Scenario: Transaction without invoice match
- **WHEN** viewing a credit transaction with no invoice match
- **THEN** system shows no invoice info and optionally displays "Match to Invoice" action

### Requirement: User can match transaction to invoice from transaction view
The system SHALL allow users to link a transaction to an invoice directly from the transaction list or detail view.

#### Scenario: Match from transaction list
- **WHEN** user clicks "Match to Invoice" on a credit transaction
- **THEN** system shows list of unmatched invoices with matching suggestions highlighted

#### Scenario: View matched invoice from transaction
- **WHEN** user clicks on the matched invoice link on a transaction
- **THEN** system navigates to the invoice detail view

### Requirement: Transaction list shows invoice match indicator
The system SHALL display a visual indicator on credit transactions that have been matched to invoices.

#### Scenario: Matched transaction indicator
- **WHEN** viewing transaction list with some matched and some unmatched credits
- **THEN** matched transactions show a checkmark or "Matched" badge

#### Scenario: Filter by match status
- **WHEN** user selects "Unmatched Credits" filter
- **THEN** system shows only credit transactions without invoice matches

### Requirement: Counterparty can be linked to customer
The system SHALL allow linking a Counterparty to a Customer record to enable amount+customer payment matching.

#### Scenario: Link counterparty to customer
- **WHEN** user views counterparty "ACME CORP" and clicks "Link to Customer"
- **THEN** system shows customer search and allows selecting "Acme GmbH" to create the link

#### Scenario: View linked customer from counterparty
- **WHEN** counterparty is linked to a customer
- **THEN** counterparty detail shows the linked customer name with link to customer page

#### Scenario: Unlink counterparty from customer
- **WHEN** user clicks "Unlink Customer" on a linked counterparty
- **THEN** system removes the customer FK from counterparty
