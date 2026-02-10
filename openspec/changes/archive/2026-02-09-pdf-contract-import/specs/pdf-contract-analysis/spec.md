## ADDED Requirements

### Requirement: Analyze PDF attachment for contract data
The system SHALL extract structured contract data from a PDF attachment using the Claude API. The extraction SHALL return line items, metadata, and totals as structured JSON. The system SHALL support English and German language PDFs.

#### Scenario: Successful PDF analysis
- **WHEN** user triggers analysis on a PDF attachment belonging to a contract in their tenant
- **THEN** system reads the PDF file from storage and sends it to the Claude API
- **THEN** system returns structured extraction results containing: line items (description, quantity, unit price, billing period, one-off flag), contract metadata (PO number, order confirmation number, minimum duration months), discount information, and total amounts

#### Scenario: Attachment is not a PDF
- **WHEN** user triggers analysis on a non-PDF attachment (e.g., .xlsx, .png)
- **THEN** system returns an error "Only PDF files can be analyzed"
- **THEN** no API call is made

#### Scenario: Attachment not found or wrong tenant
- **WHEN** user triggers analysis on a non-existent attachment or one belonging to a different tenant
- **THEN** system returns an error "Attachment not found"

#### Scenario: Claude API key not configured
- **WHEN** user triggers analysis but the ANTHROPIC_API_KEY environment variable is not set
- **THEN** system returns an error "PDF analysis is not configured"

#### Scenario: Claude API call fails
- **WHEN** the Claude API returns an error or times out
- **THEN** system returns an error describing the failure
- **THEN** no data is modified

### Requirement: Extract line items from PDF
The system SHALL extract individual line items from the PDF, each with description, quantity, unit price, and billing period. Items SHALL be classified as recurring or one-off based on PDF content.

#### Scenario: Recurring line items extracted
- **WHEN** PDF contains recurring items (e.g., "Software License: 2 x 150.00 EUR/month")
- **THEN** system extracts each item with description, quantity, unit_price, price_period (monthly/annual/etc.), and is_one_off=false

#### Scenario: One-off line items extracted
- **WHEN** PDF contains one-time fees (e.g., "Setup Fee: 1 x 500.00 EUR")
- **THEN** system extracts each item with is_one_off=true and no recurring period

#### Scenario: Discount lines identified
- **WHEN** PDF contains discount lines (negative amounts, or descriptions containing "discount"/"Rabatt")
- **THEN** system extracts the discount as a separate field (total discount amount)
- **THEN** discount lines are NOT included in the regular line items list

### Requirement: Extract contract metadata from PDF
The system SHALL extract contract-level metadata from the PDF including PO number, order confirmation number, and minimum contract duration.

#### Scenario: PO number extracted
- **WHEN** PDF contains a purchase order number (e.g., "PO #2025020")
- **THEN** system returns it in the metadata as po_number

#### Scenario: Minimum duration extracted
- **WHEN** PDF specifies a minimum contract duration (e.g., "Minimum Duration: 36 months")
- **THEN** system returns it in the metadata as min_duration_months (integer)

#### Scenario: Order confirmation number extracted
- **WHEN** PDF contains an order confirmation or AB number
- **THEN** system returns it in the metadata as order_confirmation_number

#### Scenario: Metadata field not present in PDF
- **WHEN** PDF does not contain a particular metadata field
- **THEN** system returns null for that field

### Requirement: Match extracted items to products
The system SHALL fuzzy-match each extracted line item description against the tenant's product catalog using rapidfuzz. Discount lines SHALL NOT be matched to products.

#### Scenario: High-confidence product match
- **WHEN** an extracted item description matches a product name or netsuite_item_name with confidence >= 80%
- **THEN** system returns the matched product ID, name, and confidence score

#### Scenario: Low-confidence or no match
- **WHEN** an extracted item description matches no product above 80% confidence
- **THEN** system returns no product match for that item
- **THEN** the item is still included in results for manual product selection

#### Scenario: Discount lines excluded from matching
- **WHEN** an extracted line is identified as a discount
- **THEN** system does NOT attempt product matching on that line

### Requirement: Compare extraction with existing contract
The system SHALL compare extracted data against the existing contract's items and metadata, indicating what is new, what differs, and what already exists.

#### Scenario: Existing contract has matching items
- **WHEN** an extracted line item matches an existing ContractItem (same product and similar price)
- **THEN** system marks the item as "existing" in the comparison result
- **THEN** system indicates any price differences

#### Scenario: Extracted item is new
- **WHEN** an extracted line item has no matching ContractItem
- **THEN** system marks the item as "new" in the comparison result

#### Scenario: Metadata differs from existing
- **WHEN** extracted PO number differs from the contract's current po_number (or contract has none)
- **THEN** system shows both values in the comparison for user review
