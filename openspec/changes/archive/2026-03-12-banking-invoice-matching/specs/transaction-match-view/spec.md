## ADDED Requirements

### Requirement: Match view shows suggested invoice candidates
The system SHALL display a "Suggested matches" section in the TransactionMatchSheet when the transaction's counterparty is linked to a customer. This section SHALL appear above the manual search panel and auto-load candidates when the sheet opens.

#### Scenario: Counterparty linked — suggestions shown
- **WHEN** user opens the match view for a transaction whose counterparty is linked to customer "Acme Corp"
- **THEN** a "Suggested matches" section appears showing Acme Corp's unpaid invoices ranked by amount proximity

#### Scenario: Counterparty not linked — no suggestions section
- **WHEN** user opens the match view for a transaction whose counterparty has no linked customer
- **THEN** the "Suggested matches" section is not displayed and the manual search panel is shown directly

#### Scenario: All suggestions already matched
- **WHEN** user opens the match view and all candidate invoices are already matched to this transaction
- **THEN** the "Suggested matches" section shows an empty state hint (e.g. "All invoices from this customer are matched")

### Requirement: User can add a match from suggestions with one click
The system SHALL allow adding a match by clicking on a suggested invoice candidate. The behavior SHALL be identical to adding a match from manual search results.

#### Scenario: Click suggestion to match
- **WHEN** user clicks on a suggested invoice candidate
- **THEN** the system creates a payment match, the invoice moves to the matched invoices list, the suggestion disappears from the candidates list, and the running balance updates

#### Scenario: Suggestion list updates after match
- **WHEN** user matches a suggested candidate
- **THEN** the candidate is removed from the suggestions list and the matched invoices list refreshes

### Requirement: Suggestions show amount difference indicator
Each suggestion row SHALL display the amount difference between the invoice and the transaction to help users identify the right match at a glance.

#### Scenario: Exact match highlighted
- **WHEN** a suggested invoice amount exactly matches the transaction amount
- **THEN** the row shows a visual indicator (e.g. green highlight or "exact match" badge)

#### Scenario: Close match shown with difference
- **WHEN** a suggested invoice amount is 4.800,00 EUR and the transaction is 5.000,00 EUR
- **THEN** the row shows the difference "-200,00 EUR" to help the user assess the match

### Requirement: Manual search remains available as fallback
The manual invoice search panel SHALL remain available below the suggestions section. Users SHALL be able to use manual search regardless of whether suggestions are shown.

#### Scenario: Manual search alongside suggestions
- **WHEN** the match view shows suggestions for a linked counterparty
- **THEN** the manual search panel is still visible and functional below the suggestions

#### Scenario: Manual search without suggestions
- **WHEN** the counterparty has no linked customer
- **THEN** the manual search panel is the primary way to find invoices (same behavior as before)
