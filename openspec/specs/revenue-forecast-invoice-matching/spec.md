## ADDED Requirements

### Requirement: Billing event includes matched invoice data
The billing schedule query SHALL return matched invoice information for each billing event when an imported invoice is linked to the contract and matches the billing date.

#### Scenario: Forecast event with matching invoice
- **WHEN** a billing event is calculated for a contract
- **AND** an imported invoice exists with the same contract_id
- **AND** the invoice date is within 15 days of the billing event date
- **THEN** the billing event SHALL include the matched invoice's id, invoice_number, is_paid status, and pdf_url

#### Scenario: Forecast event with no matching invoice
- **WHEN** a billing event is calculated for a contract
- **AND** no imported invoice matches the criteria
- **THEN** the billing event SHALL have null for the matched_invoice field

#### Scenario: Multiple invoices match same billing date
- **WHEN** multiple imported invoices match a billing event
- **THEN** the system SHALL return the invoice with the closest date to the billing event

### Requirement: Forecast table displays invoice column
The revenue forecast table in ContractDetail SHALL display an Invoice column showing matched invoice information.

#### Scenario: Display invoice number with link
- **WHEN** a forecast event has a matched invoice
- **THEN** the Invoice column SHALL display the invoice number as a clickable link
- **AND** clicking the link SHALL open the invoice PDF in a new tab (if pdf_url exists)

#### Scenario: Display payment status badge
- **WHEN** a forecast event has a matched invoice
- **AND** the invoice is_paid is true
- **THEN** the Invoice column SHALL display a green "Paid" badge

#### Scenario: Display unpaid status badge
- **WHEN** a forecast event has a matched invoice
- **AND** the invoice is_paid is false
- **THEN** the Invoice column SHALL display a gray "Unpaid" badge

#### Scenario: No invoice for forecast event
- **WHEN** a forecast event has no matched invoice
- **THEN** the Invoice column SHALL display a dash or be empty
