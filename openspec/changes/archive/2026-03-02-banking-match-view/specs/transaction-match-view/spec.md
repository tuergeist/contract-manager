## ADDED Requirements

### Requirement: User can open the match view for a transaction
The system SHALL provide a match action on each transaction row in the banking transaction list. Activating this action SHALL open a slide-over panel (Sheet) on the right side displaying the transaction's match details.

#### Scenario: Open match view from transaction list
- **WHEN** user clicks the match action on a transaction row
- **THEN** a slide-over panel opens showing the transaction details and its current invoice matches

#### Scenario: Close match view
- **WHEN** user closes the slide-over panel (via close button or clicking outside)
- **THEN** the panel closes and the transaction list remains in its current state

#### Scenario: Switch transaction without closing
- **WHEN** user has the match panel open for transaction A and clicks the match action on transaction B
- **THEN** the panel updates to show transaction B's details and matches

### Requirement: Match view displays transaction details
The system SHALL display the selected transaction's key fields in the panel header: entry date, value date, amount with currency, counterparty name, booking text, reference, and bank account name.

#### Scenario: Transaction header shows all fields
- **WHEN** user opens the match view for a transaction with amount +5.000,00 EUR from counterparty "ACME Corp" on 2026-01-15
- **THEN** the panel header displays the entry date, amount "5.000,00 EUR", counterparty "ACME Corp", and all other transaction metadata

### Requirement: Match view displays all matched invoices
The system SHALL display a list of all invoices currently matched to the selected transaction. Each matched invoice row SHALL show: invoice number, invoice type (imported/generated), customer name, invoice amount, match type, and a remove button.

#### Scenario: Transaction with one matched invoice
- **WHEN** user opens the match view for a transaction matched to invoice "INV-2026-001" with amount 5.000,00 EUR
- **THEN** the matched invoices list shows one row with "INV-2026-001", the invoice amount, and a remove button

#### Scenario: Transaction with multiple matched invoices
- **WHEN** user opens the match view for a transaction matched to invoices "INV-001" (3.200,00 EUR) and "INV-002" (1.800,00 EUR)
- **THEN** the matched invoices list shows both rows with their respective amounts

#### Scenario: Transaction with no matches
- **WHEN** user opens the match view for a transaction with no invoice matches
- **THEN** the matched invoices list is empty and a hint is displayed to search and add invoices

### Requirement: Match view shows running balance and difference
The system SHALL display the total matched amount (sum of all matched invoice amounts) and the difference (transaction amount minus total matched). The difference SHALL be color-coded.

#### Scenario: Fully matched transaction
- **WHEN** transaction amount is 5.000,00 EUR and matched invoices total 5.000,00 EUR
- **THEN** difference displays as "0,00 EUR" with green styling

#### Scenario: Underpaid transaction
- **WHEN** transaction amount is 5.000,00 EUR and matched invoices total 4.200,00 EUR
- **THEN** difference displays as "800,00 EUR remaining" with yellow styling

#### Scenario: Overpaid within tolerance
- **WHEN** transaction amount is 5.000,00 EUR and matched invoices total 5.100,00 EUR (2% over)
- **THEN** difference displays as "-100,00 EUR" with green styling (within 3% tolerance)

#### Scenario: Overbooking beyond tolerance
- **WHEN** transaction amount is 5.000,00 EUR and matched invoices total 5.500,00 EUR (10% over)
- **THEN** difference displays as "-500,00 EUR" with orange warning styling and an overbooking warning message

#### Scenario: Rounding tolerance
- **WHEN** transaction amount is 1.000,00 EUR and matched invoices total 1.000,01 EUR
- **THEN** difference displays as "0,00 EUR" with green styling (within rounding tolerance of 0,01 EUR)

### Requirement: User can remove an invoice match
The system SHALL allow removing an existing invoice match from the match view. Removing a match SHALL update the running balance immediately.

#### Scenario: Remove a match
- **WHEN** user clicks the remove button on a matched invoice row
- **THEN** the system deletes the payment match, removes the row from the list, and updates the running balance

#### Scenario: Remove last match
- **WHEN** user removes the only matched invoice from a transaction
- **THEN** the matched invoices list becomes empty, the difference equals the full transaction amount, and the styling changes to yellow

### Requirement: User can search invoices to add matches
The system SHALL provide an invoice search panel within the match view. Users SHALL be able to search by invoice number (text, partial match), and filter by unmatched-only toggle.

#### Scenario: Search by invoice number
- **WHEN** user types "2026-001" in the invoice search field
- **THEN** the search results show imported invoices and generated invoice records whose invoice number contains "2026-001"

#### Scenario: Filter unmatched only
- **WHEN** user enables the "unmatched only" toggle
- **THEN** the search results exclude invoices that are already fully paid

#### Scenario: Search results show invoice details
- **WHEN** search returns results
- **THEN** each result row shows: invoice number, customer name, invoice amount, invoice type (imported/generated), and current status

### Requirement: User can add an invoice match from search results
The system SHALL allow adding a match by clicking on an invoice in the search results. Adding a match SHALL update the matched invoices list and running balance immediately.

#### Scenario: Add imported invoice match
- **WHEN** user clicks on an imported invoice in the search results
- **THEN** the system creates a payment match (manual type), the invoice appears in the matched invoices list, and the running balance updates

#### Scenario: Add generated invoice record match
- **WHEN** user clicks on a generated invoice record in the search results
- **THEN** the system creates a payment match for the record (manual type), the record appears in the matched invoices list, and the running balance updates

#### Scenario: Duplicate match prevented
- **WHEN** user tries to add an invoice that is already matched to this transaction
- **THEN** the system shows an error and does not create a duplicate match

#### Scenario: Add match with overbooking warning
- **WHEN** adding an invoice would cause the total matched to exceed the transaction amount by more than 3%
- **THEN** the system still creates the match but the overbooking warning becomes visible

### Requirement: Backend provides transaction match details query
The system SHALL provide a `transactionMatchDetails` GraphQL query that returns a single transaction with all its invoice matches, total matched amount, and difference. The query SHALL be tenant-scoped.

#### Scenario: Query returns all matches
- **WHEN** a transaction has 3 invoice matches (2 imported, 1 generated)
- **THEN** the query returns all 3 matches with invoice number, amount, customer name, match type, confidence, and matched-at timestamp

#### Scenario: Query calculates totals
- **WHEN** a transaction of 5.000,00 EUR has matches to invoices of 3.200,00 EUR and 1.800,00 EUR
- **THEN** the query returns totalMatched=5000.00 and difference=0.00

#### Scenario: Tenant isolation
- **WHEN** tenant A queries transaction match details for a transaction belonging to tenant B
- **THEN** the query returns an error or empty result

### Requirement: Backend provides invoice search for matching query
The system SHALL provide a `searchInvoicesForMatching` GraphQL query that searches both imported invoices and generated invoice records. Results SHALL include invoice number, amount, customer name, type, and payment status.

#### Scenario: Search finds both imported and generated invoices
- **WHEN** user searches for "2026"
- **THEN** results include matching imported invoices and matching invoice records, each tagged with their type

#### Scenario: Results are paginated
- **WHEN** search returns more than 20 results
- **THEN** only the first 20 are returned with a hasMore indicator
