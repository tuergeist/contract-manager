## ADDED Requirements

### Requirement: Transactions are parsed from MT940 with full metadata
The system SHALL extract the following fields from each MT940 transaction record: entry date, value date, amount (signed — negative for debits, positive for credits), currency, transaction type code, counterparty name, counterparty IBAN, counterparty BIC, booking text (Verwendungszweck), reference (EREF/KREF/MREF), and the raw `:86:` field content.

#### Scenario: Parse debit transaction
- **WHEN** an MT940 file contains a debit entry `:61:2511131113DR1235,82NTRFKREF+` with `:86:` subfields including `?32Bohret Sehmsdorf + Partner` and `?23SVWZ+17065-2025/12038`
- **THEN** the system stores: entry_date=2025-11-13, amount=-1235.82, transaction_type="NTRF", counterparty_name="Bohret Sehmsdorf + Partner mbB", booking_text containing "17065-2025/12038"

#### Scenario: Parse credit transaction
- **WHEN** an MT940 file contains a credit entry `:61:2511131113CR3562,33NTRFKREF+` with `:86:` subfields including `?32SIGMA GROUP A.S.`
- **THEN** the system stores: entry_date=2025-11-13, amount=+3562.33, counterparty_name="SIGMA GROUP A.S."

#### Scenario: Parse booking text from multiple subfields
- **WHEN** a `:86:` record contains `?20EREF+354000270251` through `?29` subfields with Verwendungszweck text
- **THEN** the system assembles the booking text from all `?20`–`?29` subfields concatenated in order

### Requirement: Transactions are deduplicated on import
The system SHALL compute a deterministic hash for each transaction based on (bank_account_id, entry_date, amount, currency, reference, counterparty_name). Transactions with a hash that already exists in the database SHALL be silently skipped during import.

#### Scenario: Identical transaction skipped
- **WHEN** a transaction with entry_date=2025-11-13, amount=-1235.82, reference="507-00000507/1", counterparty="Bohret Sehmsdorf" already exists
- **AND** the same transaction appears in a newly uploaded MT940 file
- **THEN** the system skips it and increments the "skipped" counter

#### Scenario: Same amount different reference is not a duplicate
- **WHEN** two transactions have the same date and amount but different references
- **THEN** the system treats them as distinct transactions and imports both

#### Scenario: Re-importing the same file changes nothing
- **WHEN** user uploads the exact same MT940 file twice for the same account
- **THEN** the second upload reports all transactions as skipped and no new data is created

### Requirement: User can view transactions in a paginated table
The system SHALL display bank transactions in a table with columns: date, counterparty name, booking text, amount, and bank account name. The table SHALL be paginated with 50 rows per page.

#### Scenario: View transaction table
- **WHEN** user navigates to the banking page and selects "all accounts"
- **THEN** the system displays transactions from all accounts, sorted by entry date descending (newest first)

#### Scenario: Pagination
- **WHEN** there are 200 transactions and user is on page 1
- **THEN** the system shows transactions 1–50 and indicates 4 pages total

### Requirement: User can search transactions by text
The system SHALL provide a search input that filters transactions by matching against counterparty name and booking text. The search SHALL be case-insensitive and match partial strings.

#### Scenario: Search by counterparty name
- **WHEN** user types "Piepenbrock" in the search field
- **THEN** the table shows only transactions where the counterparty name contains "Piepenbrock"

#### Scenario: Search by booking text
- **WHEN** user types "BRUTTOMIETE" in the search field
- **THEN** the table shows transactions whose booking text contains "BRUTTOMIETE"

#### Scenario: Search clears
- **WHEN** user clears the search input
- **THEN** the table shows all transactions again (respecting other active filters)

### Requirement: User can filter transactions by bank account
The system SHALL provide a filter to show transactions from a single bank account or all accounts.

#### Scenario: Filter by specific account
- **WHEN** user selects "Geschäftskonto" from the account filter
- **THEN** the table shows only transactions belonging to that account

#### Scenario: Show all accounts
- **WHEN** user selects "All accounts" from the filter
- **THEN** the table shows transactions from all bank accounts

### Requirement: User can filter transactions by date range
The system SHALL provide date-from and date-to filters to restrict transactions to a specific date range based on entry date.

#### Scenario: Filter by date range
- **WHEN** user sets date-from to "2025-11-01" and date-to to "2025-11-30"
- **THEN** the table shows only transactions with entry_date between those dates (inclusive)

#### Scenario: Open-ended date filter
- **WHEN** user sets only date-from to "2025-12-01" and leaves date-to empty
- **THEN** the table shows all transactions from 2025-12-01 onward

### Requirement: User can filter transactions by amount range
The system SHALL provide amount-min and amount-max filters. These SHALL apply to the absolute value of the amount (so filtering 100–500 matches both -300 debit and +200 credit).

#### Scenario: Filter by amount range
- **WHEN** user sets amount-min to "1000" and amount-max to "5000"
- **THEN** the table shows only transactions where |amount| is between 1000 and 5000

### Requirement: User can filter transactions by direction
The system SHALL provide a debit/credit direction filter to show only incoming (credit) or outgoing (debit) transactions.

#### Scenario: Filter debits only
- **WHEN** user selects "Debit" direction filter
- **THEN** the table shows only transactions with negative amounts

#### Scenario: Filter credits only
- **WHEN** user selects "Credit" direction filter
- **THEN** the table shows only transactions with positive amounts

### Requirement: User can sort transactions by column
The system SHALL allow sorting the transaction table by date, amount, or counterparty name. Default sort SHALL be entry date descending.

#### Scenario: Sort by amount ascending
- **WHEN** user clicks the amount column header
- **THEN** the table sorts by amount ascending (largest debits first)

#### Scenario: Sort by counterparty name
- **WHEN** user clicks the counterparty column header
- **THEN** the table sorts alphabetically by counterparty name

### Requirement: Transactions are tenant-isolated
Transactions SHALL only be visible to users within the same tenant. GraphQL queries SHALL automatically scope results to the requesting user's tenant.

#### Scenario: Tenant isolation on query
- **WHEN** tenant A has 1000 transactions and tenant B has 500 transactions
- **THEN** a user from tenant A querying transactions receives only their 1000 transactions
