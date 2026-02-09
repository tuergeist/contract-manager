## ADDED Requirements

### Requirement: User can create a bank account
The system SHALL allow users with `banking.write` permission to create a bank account by providing a name, bank code, and account number. IBAN and BIC are optional. The bank account SHALL be scoped to the user's tenant.

#### Scenario: Create bank account with required fields
- **WHEN** user submits a new bank account with name "Geschäftskonto", bank code "85090000", and account number "2721891006"
- **THEN** the system creates the bank account and displays it in the account list

#### Scenario: Create bank account with all fields
- **WHEN** user submits a bank account with name, bank code, account number, IBAN "DE02850900002721891006", and BIC "GENODEF1DRS"
- **THEN** the system creates the bank account with all fields stored

#### Scenario: Duplicate account number rejected
- **WHEN** user creates a bank account with the same bank code and account number as an existing account in the same tenant
- **THEN** the system SHALL reject the creation with an error message

### Requirement: User can edit a bank account
The system SHALL allow users with `banking.write` permission to edit the name, IBAN, and BIC of an existing bank account. Bank code and account number SHALL NOT be editable after creation (they are identity fields used for MT940 matching).

#### Scenario: Edit bank account name
- **WHEN** user changes the name of a bank account from "Geschäftskonto" to "Hauptkonto Dresden"
- **THEN** the system updates the name and displays the new name

#### Scenario: Bank code and account number are read-only
- **WHEN** user views the edit form for a bank account
- **THEN** the bank code and account number fields SHALL be displayed but not editable

### Requirement: User can delete a bank account
The system SHALL allow users with `banking.write` permission to delete a bank account. Deleting an account SHALL also delete all associated transactions.

#### Scenario: Delete account with transactions
- **WHEN** user deletes a bank account that has 500 imported transactions
- **THEN** the system deletes the account and all 500 transactions, and the account no longer appears in the list

#### Scenario: Confirm before delete
- **WHEN** user clicks delete on a bank account
- **THEN** the system SHALL show a confirmation dialog before proceeding

### Requirement: User can list bank accounts
The system SHALL display all bank accounts for the current tenant. Each account SHALL show its name, bank code, account number, IBAN (if set), and the count of imported transactions.

#### Scenario: List accounts with transaction counts
- **WHEN** user navigates to the banking page
- **THEN** the system displays all bank accounts with their names and the number of imported transactions per account

#### Scenario: No accounts exist
- **WHEN** user navigates to the banking page and no bank accounts exist
- **THEN** the system displays an empty state prompting the user to create their first bank account

### Requirement: User can upload MT940 files to a bank account
The system SHALL allow users with `banking.write` permission to upload one or more MT940/MTA files for a specific bank account. The system SHALL parse the file, extract all transactions, and store them. The upload response SHALL report how many transactions were imported and how many were skipped as duplicates.

#### Scenario: Upload single MT940 file
- **WHEN** user uploads an MT940 file containing 50 transactions to a bank account
- **THEN** the system parses the file, stores the transactions, and reports "50 imported, 0 skipped"

#### Scenario: Upload file with overlapping data
- **WHEN** user uploads an MT940 file where 30 of 50 transactions already exist in the database
- **THEN** the system imports only the 20 new transactions and reports "20 imported, 30 skipped"

#### Scenario: Upload file for wrong account
- **WHEN** user uploads an MT940 file whose bank code/account number in the `:25:` field does not match the target bank account
- **THEN** the system SHALL reject the upload with an error indicating the account mismatch

#### Scenario: Upload invalid file
- **WHEN** user uploads a file that is not valid MT940 format
- **THEN** the system SHALL reject the upload with a parsing error message

### Requirement: Bank accounts are tenant-isolated
Bank accounts and their transactions SHALL only be visible to users within the same tenant. Users SHALL NOT be able to access bank accounts from other tenants.

#### Scenario: Tenant isolation
- **WHEN** tenant A has 2 bank accounts and tenant B has 1 bank account
- **THEN** users of tenant A see only their 2 accounts, and users of tenant B see only their 1 account
