## ADDED Requirements

### Requirement: System suggests invoice matches for linked counterparties
The system SHALL display suggested invoice matches when a user opens the transaction match sheet for a transaction whose counterparty is linked to a customer. Suggestions are based on the customer's open invoices, ranked by amount proximity.

#### Scenario: Transaction with linked counterparty shows suggestions
- **WHEN** user opens the match sheet for a transaction of €1,200.00 whose counterparty is linked to customer "Acme GmbH"
- **THEN** the system displays a "Suggested matches" section showing open invoices from Acme GmbH, sorted by closest amount to €1,200.00

#### Scenario: Exact amount match highlighted
- **WHEN** the suggestions include an invoice with the exact same amount as the transaction
- **THEN** that invoice is visually highlighted (e.g., green badge) to indicate an exact match

#### Scenario: Click suggestion to match
- **WHEN** user clicks on a suggested invoice
- **THEN** the system creates the match (same as manual matching) and refreshes both the suggestions list and match details

#### Scenario: All suggestions already matched
- **WHEN** all open invoices from the linked customer are already matched to this transaction
- **THEN** the system displays an empty state message indicating all invoices are matched

#### Scenario: Unlinked counterparty hides suggestions
- **WHEN** user opens the match sheet for a transaction whose counterparty has no linked customer
- **THEN** the suggestions section is not displayed

### Requirement: Suggested matches filter by eligible invoices
The system SHALL only suggest invoices that are eligible for matching: confirmed or sent (not voided or paid), with an invoice date on or before the transaction entry date, and not already matched to this transaction. Results SHALL be capped at 20.

#### Scenario: Paid invoices excluded
- **WHEN** a customer has 5 invoices, 2 of which are paid
- **THEN** only the 3 unpaid invoices appear in suggestions

#### Scenario: Future-dated invoices excluded
- **WHEN** a transaction has entry date 2025-03-15 and the customer has an invoice dated 2025-04-01
- **THEN** that invoice does not appear in suggestions

#### Scenario: Already-matched invoices excluded
- **WHEN** an invoice is already matched to this transaction
- **THEN** it does not appear in the suggestions list

#### Scenario: Mixed invoice types
- **WHEN** a customer has both imported invoices and system-generated invoices
- **THEN** both types appear in suggestions, ranked by amount proximity

### Requirement: Transaction match details include customer link
The system SHALL expose the customer ID on transaction match details so the frontend can determine whether to fetch suggestions.

#### Scenario: Match details for linked counterparty
- **WHEN** frontend queries match details for a transaction with a linked counterparty
- **THEN** the response includes the customer ID

#### Scenario: Match details for unlinked counterparty
- **WHEN** frontend queries match details for a transaction with no linked counterparty
- **THEN** the customer ID field is null
