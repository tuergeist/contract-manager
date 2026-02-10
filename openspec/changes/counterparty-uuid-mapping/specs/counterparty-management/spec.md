## ADDED Requirements

### Requirement: Counterparty has UUID primary key
The system SHALL identify each counterparty by a UUID primary key. The UUID SHALL be generated automatically on record creation and SHALL remain immutable.

#### Scenario: New counterparty gets UUID
- **WHEN** a counterparty record is created
- **THEN** the system generates a UUID v4 as the primary key

#### Scenario: UUID is stable across renames
- **WHEN** a counterparty's name is updated from "ACME Inc" to "ACME Corporation"
- **THEN** the counterparty's UUID remains unchanged

### Requirement: Counterparty stores name and optional banking details
The system SHALL store for each counterparty: name (required), IBAN (optional), and BIC (optional). Name SHALL be unique within a tenant.

#### Scenario: Create counterparty with name only
- **WHEN** a counterparty is created with name "Deutsche Telekom" and no IBAN/BIC
- **THEN** the system stores the counterparty with empty IBAN and BIC fields

#### Scenario: Create counterparty with full details
- **WHEN** a counterparty is created with name "Vodafone", IBAN "DE89370400440532013000", BIC "COBADEFFXXX"
- **THEN** the system stores all three fields

#### Scenario: Duplicate name rejected
- **WHEN** a counterparty named "ACME Inc" exists and user tries to create another with the same name
- **THEN** the system rejects the creation with a duplicate name error

### Requirement: User can rename a counterparty
The system SHALL allow users with write permission to change a counterparty's name. All transactions referencing that counterparty SHALL automatically reflect the new name.

#### Scenario: Rename counterparty
- **WHEN** user renames counterparty from "Telekom Deutschland" to "Deutsche Telekom AG"
- **THEN** all transactions referencing this counterparty now display "Deutsche Telekom AG"

#### Scenario: Rename to existing name rejected
- **WHEN** user tries to rename a counterparty to a name that already exists
- **THEN** the system rejects the rename with a duplicate name error

### Requirement: User can merge counterparties
The system SHALL allow users to merge two counterparties into one. All transactions from the source counterparty SHALL be reassigned to the target counterparty. The source counterparty SHALL be deleted.

#### Scenario: Merge duplicate counterparties
- **WHEN** user merges "ACME Inc" (source, 10 transactions) into "ACME Inc." (target, 15 transactions)
- **THEN** the target counterparty now has 25 transactions and the source counterparty is deleted

#### Scenario: Merge preserves target details
- **WHEN** source has IBAN "DE111" and target has IBAN "DE222"
- **THEN** the merged counterparty keeps the target's IBAN "DE222"

### Requirement: Counterparty detail page uses UUID in URL
The system SHALL route to counterparty detail pages using the UUID in the URL path (`/banking/counterparty/:id`). The page SHALL display the counterparty name, banking details, and linked transactions.

#### Scenario: Navigate to counterparty by UUID
- **WHEN** user clicks a counterparty link in the transaction table
- **THEN** the browser navigates to `/banking/counterparty/<uuid>` where uuid is the counterparty's ID

#### Scenario: Invalid UUID shows error
- **WHEN** user navigates to `/banking/counterparty/invalid-uuid`
- **THEN** the system displays a "Counterparty not found" error

### Requirement: GraphQL query for counterparty by ID
The system SHALL provide a `counterparty(id: ID!)` GraphQL query that returns the counterparty with its name, IBAN, BIC, and transaction summary.

#### Scenario: Query counterparty by ID
- **WHEN** client queries `counterparty(id: "550e8400-...")`
- **THEN** the response includes name, iban, bic, transactionCount, and totalAmount fields

### Requirement: GraphQL mutations for counterparty management
The system SHALL provide mutations: `updateCounterparty(id, name, iban, bic)` for renaming/updating and `mergeCounterparties(sourceId, targetId)` for merging.

#### Scenario: Update counterparty via mutation
- **WHEN** client calls `updateCounterparty(id: "...", name: "New Name")`
- **THEN** the counterparty's name is updated and the response includes the updated record

#### Scenario: Merge counterparties via mutation
- **WHEN** client calls `mergeCounterparties(sourceId: "...", targetId: "...")`
- **THEN** all transactions are reassigned and the source is deleted

### Requirement: Counterparties are tenant-isolated
Counterparty records SHALL only be visible to users within the same tenant. All queries and mutations SHALL automatically scope to the requesting user's tenant.

#### Scenario: Tenant isolation on query
- **WHEN** tenant A has 50 counterparties and tenant B has 30 counterparties
- **THEN** a user from tenant A querying counterparties receives only their 50 records
