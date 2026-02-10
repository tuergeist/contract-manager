## MODIFIED Requirements

### Requirement: Detect recurring payments from transaction history
The system SHALL analyze bank transactions to identify recurring payment patterns based on similarity scoring. A pattern is detected when transactions share 2 or more of: same counterparty (by FK reference), same/similar amount, consistent timing.

#### Scenario: Detect monthly subscription with same amount and counterparty
- **WHEN** 3+ transactions exist linked to the same Counterparty with identical amount within ±3 days of same day-of-month
- **THEN** system creates a recurring pattern with frequency "monthly", linked to that Counterparty, and confidence score ≥ 0.8

#### Scenario: Detect quarterly payment with same counterparty but varying amounts
- **WHEN** 2+ transactions exist linked to the same Counterparty at ~90 day intervals but different amounts
- **THEN** system creates a recurring pattern with frequency "quarterly", linked to that Counterparty, average amount, and confidence score ≥ 0.6

#### Scenario: Ignore one-time payments
- **WHEN** a transaction's Counterparty has no other similar transactions (amount or timing)
- **THEN** system does NOT create a recurring pattern for it

### Requirement: Store detected patterns persistently
The system SHALL store detected recurring patterns with: counterparty reference (FK), average amount, frequency, day-of-month, confidence score, confirmation status, and links to source transactions.

#### Scenario: Create pattern record from detected transactions
- **WHEN** system detects a recurring pattern
- **THEN** a RecurringPattern record is created with counterparty FK, calculated average_amount, detected frequency, typical day_of_month, and M2M links to source BankTransactions

#### Scenario: Update pattern when new matching transaction arrives
- **WHEN** a new transaction matches an existing pattern's Counterparty
- **THEN** system updates last_occurrence date and recalculates average_amount

## ADDED Requirements

### Requirement: RecurringPattern references counterparty by foreign key
Each RecurringPattern record SHALL reference a Counterparty via a foreign key instead of storing counterparty_name and counterparty_iban as inline string fields.

#### Scenario: Pattern has counterparty FK
- **WHEN** querying a recurring pattern via GraphQL
- **THEN** the response includes a `counterparty` object with `id`, `name`, `iban`, `bic` fields

#### Scenario: Pattern reflects counterparty rename
- **WHEN** a counterparty is renamed from "Old Name" to "New Name"
- **THEN** all patterns referencing that counterparty now display "New Name"

### Requirement: Patterns are grouped by counterparty
The system SHALL group patterns by Counterparty when displaying in the UI. This ensures consistent identification even if counterparty names change.

#### Scenario: Counterparty with renamed pattern
- **WHEN** pattern was created when counterparty was named "ACME" and counterparty is now named "ACME Corp"
- **THEN** pattern displays as "ACME Corp" and links to the same counterparty detail page
