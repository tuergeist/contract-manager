## MODIFIED Requirements

### Requirement: Transactions are parsed from MT940 with full metadata
The system SHALL extract the following fields from each MT940 transaction record: entry date, value date, amount (signed — negative for debits, positive for credits), currency, transaction type code, booking text (Verwendungszweck), reference (EREF/KREF/MREF), and the raw `:86:` field content. Counterparty data (name, IBAN, BIC) SHALL be extracted and used to find or create a Counterparty record, which is then linked via foreign key.

#### Scenario: Parse debit transaction
- **WHEN** an MT940 file contains a debit entry `:61:2511131113DR1235,82NTRFKREF+` with `:86:` subfields including `?32Bohret Sehmsdorf + Partner` and `?23SVWZ+17065-2025/12038`
- **THEN** the system stores: entry_date=2025-11-13, amount=-1235.82, transaction_type="NTRF", booking_text containing "17065-2025/12038", and links to a Counterparty record with name "Bohret Sehmsdorf + Partner mbB"

#### Scenario: Parse credit transaction
- **WHEN** an MT940 file contains a credit entry `:61:2511131113CR3562,33NTRFKREF+` with `:86:` subfields including `?32SIGMA GROUP A.S.`
- **THEN** the system stores: entry_date=2025-11-13, amount=+3562.33, and links to a Counterparty record with name "SIGMA GROUP A.S."

#### Scenario: Parse booking text from multiple subfields
- **WHEN** a `:86:` record contains `?20EREF+354000270251` through `?29` subfields with Verwendungszweck text
- **THEN** the system assembles the booking text from all `?20`–`?29` subfields concatenated in order

#### Scenario: Counterparty is created if not exists
- **WHEN** a transaction references counterparty "New Company GmbH" that does not exist
- **THEN** the system creates a new Counterparty record with that name and links the transaction to it

#### Scenario: Counterparty is reused if exists
- **WHEN** a transaction references counterparty "Existing Company" that already exists
- **THEN** the system links the transaction to the existing Counterparty record

### Requirement: User can view transactions in a paginated table
The system SHALL display bank transactions in a table with columns: date, counterparty name (linked to counterparty detail page), booking text, amount, and bank account name. The table SHALL be paginated with 50 rows per page.

#### Scenario: View transaction table
- **WHEN** user navigates to the banking page and selects "all accounts"
- **THEN** the system displays transactions from all accounts, sorted by entry date descending (newest first)

#### Scenario: Pagination
- **WHEN** there are 200 transactions and user is on page 1
- **THEN** the system shows transactions 1–50 and indicates 4 pages total

#### Scenario: Counterparty name links to detail page
- **WHEN** user clicks on a counterparty name in the transaction table
- **THEN** the browser navigates to the counterparty detail page using the counterparty's UUID

## ADDED Requirements

### Requirement: Transaction references counterparty by foreign key
Each BankTransaction record SHALL reference a Counterparty via a foreign key instead of storing counterparty_name, counterparty_iban, counterparty_bic as inline string fields.

#### Scenario: Transaction has counterparty FK
- **WHEN** querying a transaction via GraphQL
- **THEN** the response includes a `counterparty` object with `id`, `name`, `iban`, `bic` fields

#### Scenario: Filter transactions by counterparty ID
- **WHEN** client queries transactions with `counterpartyId` filter
- **THEN** the response includes only transactions linked to that counterparty

### Requirement: Data migration creates counterparties from existing transactions
The system SHALL provide a data migration that extracts unique counterparty names from existing transactions, creates Counterparty records, and updates all transactions to reference them via FK.

#### Scenario: Migration creates counterparties by name
- **WHEN** migration runs and 100 transactions reference 25 unique counterparty names
- **THEN** 25 Counterparty records are created, each linked to their respective transactions

#### Scenario: Migration preserves first IBAN found
- **WHEN** migration runs and counterparty "ACME" has 5 transactions, 2 with IBAN "DE123"
- **THEN** the created Counterparty record for "ACME" has IBAN "DE123"

#### Scenario: Migration is idempotent
- **WHEN** migration runs twice
- **THEN** no duplicate counterparties are created
