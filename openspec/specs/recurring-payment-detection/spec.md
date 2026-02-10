## ADDED Requirements

### Requirement: Detect recurring payments from transaction history
The system SHALL analyze bank transactions to identify recurring payment patterns based on similarity scoring. A pattern is detected when transactions share 2 or more of: same counterparty, same/similar amount, consistent timing.

#### Scenario: Detect monthly subscription with same amount and counterparty
- **WHEN** 3+ transactions exist with identical counterparty name and amount within ±3 days of same day-of-month
- **THEN** system creates a recurring pattern with frequency "monthly" and confidence score ≥ 0.8

#### Scenario: Detect quarterly payment with same counterparty but varying amounts
- **WHEN** 2+ transactions exist with identical counterparty name at ~90 day intervals but different amounts
- **THEN** system creates a recurring pattern with frequency "quarterly", average amount, and confidence score ≥ 0.6

#### Scenario: Ignore one-time payments
- **WHEN** a transaction has no similar transactions (counterparty, amount, or timing)
- **THEN** system does NOT create a recurring pattern for it

### Requirement: Score-based similarity matching
The system SHALL compute a similarity score for transaction pairs using: counterparty match (+1), amount match within 5% (+1), timing pattern match (+1). Minimum score of 2 required to consider as recurring.

#### Scenario: Calculate similarity score for identical transactions
- **WHEN** two transactions have same counterparty, same amount, and 30-day interval
- **THEN** similarity score is 3

#### Scenario: Calculate similarity score for partial match
- **WHEN** two transactions have same counterparty and same amount but no timing pattern
- **THEN** similarity score is 2 and transactions are considered potentially recurring

#### Scenario: Reject low similarity transactions
- **WHEN** two transactions share only counterparty name (different amounts, irregular timing)
- **THEN** similarity score is 1 and transactions are NOT grouped as recurring

### Requirement: Store detected patterns persistently
The system SHALL store detected recurring patterns with: counterparty info, average amount, frequency, day-of-month, confidence score, confirmation status, and links to source transactions.

#### Scenario: Create pattern record from detected transactions
- **WHEN** system detects a recurring pattern
- **THEN** a RecurringPattern record is created with calculated average_amount, detected frequency, typical day_of_month, and M2M links to source BankTransactions

#### Scenario: Update pattern when new matching transaction arrives
- **WHEN** a new transaction matches an existing pattern
- **THEN** system updates last_occurrence date and recalculates average_amount

### Requirement: User confirmation of patterns
The system SHALL allow users to confirm or dismiss detected patterns. Confirmed patterns are always projected; dismissed patterns are hidden from forecast.

#### Scenario: User confirms a detected pattern
- **WHEN** user clicks "Confirm" on a detected pattern
- **THEN** is_confirmed is set to true and pattern appears in forecast projections

#### Scenario: User dismisses a detected pattern
- **WHEN** user clicks "Ignore" on a detected pattern
- **THEN** is_ignored is set to true and pattern is excluded from forecast

#### Scenario: User can undo dismissal
- **WHEN** user views ignored patterns and clicks "Restore"
- **THEN** is_ignored is set to false and pattern reappears in detection list
