## Requirements

### Requirement: InvoiceList persists sort and filter preferences
The InvoiceList page SHALL persist sortField, sortOrder, sourceFilter, and paymentStatus using `usePersistedState` with keys following the `cm:invoiceList:<field>` convention. Search, pagination, and uploadStatus SHALL NOT be persisted.

#### Scenario: Sort preference restored on return
- **WHEN** user sets sort to "Amount descending" on InvoiceList, navigates away, and returns
- **THEN** the list displays sorted by Amount descending

#### Scenario: Source filter restored on return
- **WHEN** user filters by source "GENERATED", navigates away, and returns
- **THEN** the source filter is set to "GENERATED"

#### Scenario: Payment status filter restored on return
- **WHEN** user filters by payment status "paid", navigates away, and returns
- **THEN** the payment status filter is set to "paid"

#### Scenario: Search term is not persisted
- **WHEN** user types a search term, navigates away, and returns
- **THEN** the search field is empty

### Requirement: BankingPage persists tab and sort preferences
The BankingPage SHALL persist activeTab, sortBy, sortOrder, cpSortBy, and cpSortOrder using `usePersistedState` with keys following the `cm:banking:<field>` convention. Search, date filters, amount filters, pagination, direction filter, and unmatchedCredits SHALL NOT be persisted.

#### Scenario: Active tab restored on return
- **WHEN** user switches to the counterparties tab, navigates away, and returns
- **THEN** the counterparties tab is active

#### Scenario: Transaction sort restored on return
- **WHEN** user sorts transactions by date ascending, navigates away, and returns
- **THEN** transactions are sorted by date ascending

#### Scenario: Counterparty sort restored on return
- **WHEN** user sorts counterparties by name, navigates away, and returns
- **THEN** counterparties are sorted by name

#### Scenario: Date filter is not persisted
- **WHEN** user sets a date range filter, navigates away, and returns
- **THEN** the date range filter is at its default value

### Requirement: CounterpartyDetailPage persists sort preferences
The CounterpartyDetailPage SHALL persist sortBy and sortOrder using `usePersistedState` with keys following the `cm:counterpartyDetail:<field>` convention. Search, date filters, amount filters, and pagination SHALL NOT be persisted.

#### Scenario: Sort preference restored on return
- **WHEN** user sorts transactions by amount descending, navigates away, and returns
- **THEN** transactions are sorted by amount descending

#### Scenario: Search is not persisted
- **WHEN** user types a search term, navigates away, and returns
- **THEN** the search field is empty

### Requirement: AuditLogPage persists filter preferences
The AuditLogPage SHALL persist entityTypeFilter and actionFilter using `usePersistedState` with keys following the `cm:auditLog:<field>` convention. Search, date filters, and userFilter SHALL NOT be persisted.

#### Scenario: Entity type filter restored on return
- **WHEN** user filters audit log by entity type "Contract", navigates away, and returns
- **THEN** the entity type filter is set to "Contract"

#### Scenario: Action filter restored on return
- **WHEN** user filters audit log by action "updated", navigates away, and returns
- **THEN** the action filter is set to "updated"

#### Scenario: Date filter is not persisted
- **WHEN** user sets a date range, navigates away, and returns
- **THEN** the date range is at its default value

### Requirement: ProjectList persists filter preferences
The ProjectList page SHALL persist statusFilter using `usePersistedState` with the key `cm:projectList:statusFilter`. No other state on this page requires persistence.

#### Scenario: Status filter restored on return
- **WHEN** user filters projects by status "pending", navigates away, and returns
- **THEN** the status filter is set to "pending"

### Requirement: CustomerDetail persists tab and contract sort preferences
The CustomerDetail page SHALL persist activeTab and contract table sort column/order using `usePersistedState` with keys following the `cm:customerDetail:<field>` convention. Modal state SHALL NOT be persisted.

#### Scenario: Active tab restored on return
- **WHEN** user switches to a non-default tab, navigates away, and returns
- **THEN** the previously selected tab is active

#### Scenario: Contract sort preference restored on return
- **WHEN** user sorts contracts by value descending, navigates away, and returns
- **THEN** contracts are sorted by value descending

### Requirement: Consistent key naming convention
All new localStorage keys SHALL follow the pattern `cm:<page>:<field>` (e.g., `cm:invoiceList:sortField`, `cm:banking:activeTab`). Existing keys on CustomerList, ProductList, and ContractList SHALL NOT be renamed.

#### Scenario: New keys use consistent prefix
- **WHEN** any new persisted state is added
- **THEN** the localStorage key matches the pattern `cm:<pageName>:<fieldName>`

#### Scenario: Existing keys are unchanged
- **WHEN** the change is deployed
- **THEN** existing localStorage keys on CustomerList, ProductList, and ContractList remain unchanged
