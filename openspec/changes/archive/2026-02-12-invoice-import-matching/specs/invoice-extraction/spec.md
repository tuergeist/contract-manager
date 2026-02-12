## ADDED Requirements

### Requirement: System extracts invoice data via AI
The system SHALL use Claude API to extract invoice_number, invoice_date, total_amount, currency, and customer_name from uploaded invoice PDFs.

#### Scenario: Successful extraction
- **WHEN** an invoice PDF is uploaded with clear invoice number "RE-2025-001234", date "15.01.2025", total "1.234,56 EUR", and customer "Acme GmbH"
- **THEN** system extracts: invoice_number="RE-2025-001234", invoice_date=2025-01-15, total_amount=1234.56, currency="EUR", customer_name="Acme GmbH"

#### Scenario: Handle German number format
- **WHEN** invoice shows amount "12.345,67 €"
- **THEN** system extracts total_amount=12345.67 and currency="EUR"

#### Scenario: Handle various invoice number formats
- **WHEN** invoice shows number as "Rechnungsnummer: 2025/001234" or "Invoice No. 2025-001234"
- **THEN** system extracts the invoice number correctly regardless of label format

### Requirement: Extraction runs automatically after upload
The system SHALL trigger extraction automatically when a new invoice PDF is uploaded, running as a background task.

#### Scenario: Auto-trigger extraction
- **WHEN** user uploads an invoice PDF
- **THEN** system queues extraction job and updates status to "extracting"

#### Scenario: Extraction completes successfully
- **WHEN** extraction job completes without error
- **THEN** system updates invoice with extracted data and sets status to "extracted"

#### Scenario: Extraction fails
- **WHEN** extraction job fails (API error, unreadable PDF)
- **THEN** system sets status to "extraction_failed" and stores error message

### Requirement: User can review and correct extracted data
The system SHALL display extracted data for user review and allow corrections before finalizing.

#### Scenario: View extraction results
- **WHEN** extraction completes
- **THEN** user sees extracted fields with option to edit any field

#### Scenario: Correct extraction error
- **WHEN** AI extracted wrong invoice number "RE-2025-00124" instead of "RE-2025-001234"
- **THEN** user can edit the field and save correction

#### Scenario: Confirm extraction
- **WHEN** user reviews extracted data and clicks confirm
- **THEN** system marks extraction as "confirmed" and proceeds to customer matching

### Requirement: System matches extracted customer to existing customers
The system SHALL attempt to match the extracted customer_name to existing Customer records using fuzzy matching.

#### Scenario: Exact customer match
- **WHEN** extracted customer_name is "Acme GmbH" and Customer "Acme GmbH" exists
- **THEN** system auto-links invoice to that customer with confidence 1.0

#### Scenario: Fuzzy customer match
- **WHEN** extracted customer_name is "Acme GmbH" and Customer "ACME GmbH" exists
- **THEN** system suggests the match with confidence 0.9 for user confirmation

#### Scenario: Multiple potential matches
- **WHEN** extracted customer_name is "Müller" and both "Müller GmbH" and "Hans Müller AG" exist
- **THEN** system presents both options ranked by similarity for user selection

#### Scenario: No match found
- **WHEN** extracted customer_name has no matches above threshold (0.3)
- **THEN** system prompts user to select customer manually or create new one

### Requirement: User can manually trigger re-extraction
The system SHALL allow users to re-run extraction if initial extraction failed or produced poor results.

#### Scenario: Re-extract invoice
- **WHEN** user clicks "Re-extract" on an invoice
- **THEN** system queues new extraction job and resets status to "extracting"
