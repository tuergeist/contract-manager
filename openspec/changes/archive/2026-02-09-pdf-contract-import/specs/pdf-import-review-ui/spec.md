## ADDED Requirements

### Requirement: Display PDF analysis results inline
The system SHALL display PDF analysis results as an inline panel on the contract detail page, showing extracted data alongside existing contract data for comparison.

#### Scenario: Analysis results displayed
- **WHEN** user triggers PDF analysis and results are returned
- **THEN** system displays an inline review panel on the contract detail page
- **THEN** the panel shows metadata comparison, extracted line items, and action buttons

#### Scenario: Analysis in progress
- **WHEN** user triggers PDF analysis and the API call is pending
- **THEN** system displays a loading indicator with message indicating analysis is in progress

#### Scenario: Analysis returns error
- **WHEN** PDF analysis fails (API error, invalid PDF, etc.)
- **THEN** system displays the error message in the review panel
- **THEN** user can dismiss the panel

### Requirement: Display metadata comparison
The system SHALL show a side-by-side comparison of extracted metadata vs. current contract values for PO number, order confirmation number, minimum duration, and discount amount.

#### Scenario: Metadata field differs
- **WHEN** extracted value differs from the current contract value (e.g., PO number extracted but contract has none)
- **THEN** system highlights the difference showing current value and extracted value
- **THEN** each metadata field has a checkbox to include it in the import

#### Scenario: Metadata field matches
- **WHEN** extracted value matches the current contract value
- **THEN** system shows the value as "already set" without a checkbox

### Requirement: Display extracted line items with product matches
The system SHALL display extracted line items in a table with columns for: description, quantity, unit price, billing period, matched product, status (new/existing), and an import checkbox.

#### Scenario: Item with high-confidence product match
- **WHEN** an extracted item has a product match with confidence >= 80%
- **THEN** system shows the matched product name and confidence percentage
- **THEN** the import checkbox is checked by default

#### Scenario: Item with no product match
- **WHEN** an extracted item has no product match above threshold
- **THEN** system shows a product selection dropdown for manual matching
- **THEN** the import checkbox is unchecked by default

#### Scenario: Item already exists on contract
- **WHEN** an extracted item matches an existing ContractItem
- **THEN** system shows the item as "existing" with dimmed styling
- **THEN** the import checkbox is unchecked and disabled

#### Scenario: User overrides product match
- **WHEN** user selects a different product from the dropdown for an extracted item
- **THEN** system updates the matched product for that item
- **THEN** the item remains eligible for import

### Requirement: Import selected items and metadata
The system SHALL allow users to import selected line items as ContractItems and update selected metadata fields on the contract via a single action.

#### Scenario: Import selected items
- **WHEN** user checks one or more extracted items and clicks "Import Selected"
- **THEN** system creates ContractItem records for each selected item with the matched product, quantity, unit price, price period, and one-off flag
- **THEN** system displays a success message with the count of imported items
- **THEN** the contract's items list refreshes to show newly added items

#### Scenario: Import metadata updates
- **WHEN** user checks metadata fields (PO number, min duration, etc.) and clicks "Import Selected"
- **THEN** system updates the corresponding contract fields
- **THEN** updated metadata is reflected in the contract detail view

#### Scenario: Import discount amount
- **WHEN** extracted discount is selected for import
- **THEN** system updates the contract's discount_amount field

#### Scenario: No items or metadata selected
- **WHEN** user clicks "Import Selected" with nothing checked
- **THEN** system displays a message "No items selected for import"
- **THEN** no changes are made

#### Scenario: Import fails
- **WHEN** the import mutation returns an error
- **THEN** system displays the error message
- **THEN** no partial changes are persisted (atomic operation)

### Requirement: Dismiss analysis panel
The system SHALL allow users to dismiss the analysis review panel without importing.

#### Scenario: User cancels review
- **WHEN** user clicks "Cancel" or closes the review panel
- **THEN** the panel is dismissed
- **THEN** no changes are made to the contract
- **THEN** the contract detail page returns to its normal state

### Requirement: Amendment tracking for active contracts
The system SHALL create ContractAmendment records when importing items into non-draft contracts, consistent with the existing item addition flow.

#### Scenario: Import into active contract
- **WHEN** user imports items into a contract with status "active"
- **THEN** system creates ContractAmendment records for each added item
- **THEN** amendments are visible in the contract's amendment history

#### Scenario: Import into draft contract
- **WHEN** user imports items into a contract with status "draft"
- **THEN** system creates ContractItem records without amendments
