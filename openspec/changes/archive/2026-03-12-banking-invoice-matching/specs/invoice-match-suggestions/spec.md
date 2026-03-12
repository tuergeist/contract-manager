## ADDED Requirements

### Requirement: Backend provides suggested invoice candidates for a transaction
The system SHALL provide a `suggestedInvoiceMatches` GraphQL query that accepts a `transactionId` and returns a ranked list of invoice candidates from the counterparty's linked customer. The query SHALL be tenant-scoped.

#### Scenario: Counterparty linked to customer with unpaid invoices
- **WHEN** a transaction's counterparty is linked to customer "Acme Corp" and Acme Corp has 3 unpaid invoices dated before the transaction's entry date
- **THEN** the query returns all 3 invoices as candidates

#### Scenario: Counterparty not linked to any customer
- **WHEN** a transaction's counterparty has no linked customer
- **THEN** the query returns an empty candidate list

#### Scenario: No unpaid invoices for linked customer
- **WHEN** a transaction's counterparty is linked to a customer whose invoices are all paid
- **THEN** the query returns an empty candidate list

#### Scenario: Tenant isolation
- **WHEN** tenant A queries suggested matches for a transaction belonging to tenant B
- **THEN** the query returns null or an error

### Requirement: Candidates are filtered by invoice date
The system SHALL only include invoices where `invoice_date <= transaction.entry_date`. Invoices dated after the payment date SHALL NOT appear as candidates.

#### Scenario: Invoice dated before transaction
- **WHEN** transaction entry date is 2026-03-15 and customer has an invoice dated 2026-03-01
- **THEN** the invoice appears as a candidate

#### Scenario: Invoice dated after transaction
- **WHEN** transaction entry date is 2026-03-15 and customer has an invoice dated 2026-03-20
- **THEN** the invoice does NOT appear as a candidate

#### Scenario: Invoice with null date
- **WHEN** an unpaid invoice has no invoice_date set
- **THEN** the invoice still appears as a candidate (no date filter applied)

### Requirement: Candidates are ranked by amount proximity
The system SHALL rank candidates by how close their amount is to the absolute transaction amount. The closest amount match SHALL appear first.

#### Scenario: Exact amount match ranked first
- **WHEN** transaction amount is 1.500,00 EUR and customer has invoices for 1.500,00 EUR, 2.000,00 EUR, and 500,00 EUR
- **THEN** the 1.500,00 EUR invoice appears first in the list

#### Scenario: Multiple candidates with different proximity
- **WHEN** transaction amount is 1.000,00 EUR and customer has invoices for 950,00 EUR, 1.200,00 EUR, and 500,00 EUR
- **THEN** candidates are ordered: 950,00 EUR (diff 50), 1.200,00 EUR (diff 200), 500,00 EUR (diff 500)

### Requirement: Candidates include both imported and generated invoices
The system SHALL search both ImportedInvoice (with status confirmed or sent) and InvoiceRecord (excluding voided and paid) for the linked customer.

#### Scenario: Mixed invoice types
- **WHEN** a customer has 2 unpaid imported invoices and 1 unpaid generated invoice record
- **THEN** all 3 appear as candidates, each tagged with their type ("imported" or "generated")

#### Scenario: Paid invoices excluded
- **WHEN** an imported invoice has extraction_status "paid" or an invoice record has status "paid"
- **THEN** those invoices do NOT appear as candidates

#### Scenario: Already matched invoices excluded
- **WHEN** an invoice is already matched to this specific transaction
- **THEN** that invoice does NOT appear as a candidate

### Requirement: Candidate response includes match metadata
Each candidate SHALL include: invoice id, invoice number, invoice amount, customer name, invoice type (imported/generated), invoice date, and an amount difference field showing the gap between the invoice amount and the transaction amount.

#### Scenario: Candidate fields populated
- **WHEN** the query returns candidates
- **THEN** each candidate includes invoiceNumber, amount, customerName, invoiceType, invoiceDate, and amountDifference
