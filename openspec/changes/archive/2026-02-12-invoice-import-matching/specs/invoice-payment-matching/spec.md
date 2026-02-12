## ADDED Requirements

### Requirement: System matches invoices to incoming payments by invoice number
The system SHALL search for the invoice number in the booking_text of credit transactions (incoming payments) using fuzzy matching.

#### Scenario: Exact invoice number match
- **WHEN** invoice has number "RE-2025-001234" and a credit transaction has booking_text containing "RE-2025-001234"
- **THEN** system creates a match with type="invoice_number" and confidence=1.0

#### Scenario: Fuzzy invoice number match
- **WHEN** invoice has number "RE-2025-001234" and booking_text contains "RE 2025 001234" (spaces instead of dashes)
- **THEN** system creates a match with type="invoice_number" and confidence=0.9

#### Scenario: Partial invoice number match
- **WHEN** invoice has number "RE-2025-001234" and booking_text contains only "001234"
- **THEN** system creates a match with type="invoice_number" and confidence=0.7 (requires confirmation)

### Requirement: System matches invoices to payments by amount and customer
The system SHALL match invoices to credit transactions where the amount matches exactly and the counterparty is linked to the invoice's customer.

#### Scenario: Amount and customer match
- **WHEN** invoice for Customer A has amount 1234.56 EUR and a credit transaction from Counterparty X (linked to Customer A) has amount +1234.56 EUR
- **THEN** system creates a match with type="amount_customer" and confidence=0.8

#### Scenario: Amount matches but customer different
- **WHEN** invoice amount matches transaction amount but counterparty is not linked to the invoice's customer
- **THEN** system does NOT create an automatic match

#### Scenario: Multiple invoices same amount same customer
- **WHEN** two invoices for Customer A both have amount 500.00 EUR and one payment of 500.00 EUR arrives
- **THEN** system suggests both invoices as potential matches for user selection

### Requirement: User can manually match invoice to transaction
The system SHALL allow users to manually link an invoice to any credit transaction.

#### Scenario: Manual match
- **WHEN** user selects an invoice and a transaction and clicks "Link"
- **THEN** system creates a match with type="manual" and confidence=1.0

#### Scenario: Manual unmatch
- **WHEN** user clicks "Unlink" on an existing match
- **THEN** system removes the InvoicePaymentMatch record

### Requirement: System stores payment matches
The system SHALL store each invoice-to-transaction match with: invoice_id, transaction_id, match_type, confidence, matched_at, and matched_by (for manual matches).

#### Scenario: Match record created
- **WHEN** system or user creates a match
- **THEN** InvoicePaymentMatch record is created with all required fields

#### Scenario: One invoice can have multiple payment matches
- **WHEN** customer pays invoice in two installments (two transactions)
- **THEN** system allows both transactions to be matched to the same invoice

### Requirement: Invoice shows payment status
The system SHALL display whether an invoice has been paid based on existence of payment matches.

#### Scenario: Unpaid invoice
- **WHEN** invoice has no payment matches
- **THEN** system displays status as "Unpaid"

#### Scenario: Paid invoice
- **WHEN** invoice has at least one payment match
- **THEN** system displays status as "Paid" with link to matched transaction(s)

### Requirement: User can trigger payment matching
The system SHALL allow users to run payment matching for a specific invoice or for all unmatched invoices.

#### Scenario: Match single invoice
- **WHEN** user clicks "Find Payment" on an invoice
- **THEN** system searches recent transactions and shows potential matches

#### Scenario: Match all unmatched invoices
- **WHEN** user clicks "Match All Unmatched"
- **THEN** system runs matching for all invoices without payment matches and reports results

### Requirement: Payment matching searches within date window
The system SHALL only search for payments within a configurable window around the invoice date (default: invoice_date to invoice_date + 90 days).

#### Scenario: Payment within window
- **WHEN** invoice dated 2025-01-15 and payment received 2025-02-20
- **THEN** system considers this transaction for matching (within 90 days)

#### Scenario: Payment outside window
- **WHEN** invoice dated 2025-01-15 and payment received 2025-06-01
- **THEN** system does NOT automatically consider this transaction (beyond 90 days) unless user expands search
