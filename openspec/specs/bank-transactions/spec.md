## ADDED Requirements

### Requirement: Transaction rows have a match action
The system SHALL display a match action button on each transaction row in the banking transaction list. The button SHALL visually indicate whether the transaction already has invoice matches.

#### Scenario: Unmatched transaction shows match button
- **WHEN** a transaction has no invoice matches
- **THEN** the row displays a match action button in a neutral/default style

#### Scenario: Matched transaction shows match indicator
- **WHEN** a transaction has one or more invoice matches
- **THEN** the row displays a match action button with a visual indicator (e.g., filled icon or badge) showing it has matches

#### Scenario: Clicking match action opens match view
- **WHEN** user clicks the match action button on a transaction row
- **THEN** the TransactionMatchSheet opens for that transaction
