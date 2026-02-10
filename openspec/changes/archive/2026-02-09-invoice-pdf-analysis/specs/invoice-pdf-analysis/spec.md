## ADDED Requirements

### Requirement: User can trigger data extraction from a reference invoice PDF

The system SHALL allow users to analyze an uploaded reference invoice PDF to extract company legal data, template styling, and layout information using the Claude API.

#### Scenario: Trigger extraction for a reference PDF
- **WHEN** user clicks "Extract Data" on an uploaded reference PDF in the template settings page
- **THEN** system sends the PDF to the Claude API for analysis
- **AND** displays a loading spinner during extraction (2-5 seconds)
- **AND** stores the extraction results on the reference record

#### Scenario: Extraction returns structured data
- **WHEN** extraction completes successfully
- **THEN** system returns a JSON result with three sections: legal_data, design, and layout
- **AND** legal_data keys match CompanyLegalData model fields (company_name, street, zip_code, city, country, tax_number, vat_id, commercial_register_court, commercial_register_number, managing_directors, bank_name, iban, bic, phone, email, website, share_capital, default_tax_rate)
- **AND** design contains accent_color (hex), header_text, and footer_text
- **AND** layout contains logo_position, footer_columns, and description

#### Scenario: Extraction handles missing fields gracefully
- **WHEN** the reference PDF does not contain a particular field (e.g., no BIC visible)
- **THEN** that field SHALL be null in the extraction result
- **AND** extraction SHALL still succeed with all other fields populated

#### Scenario: Extraction unavailable without API key
- **WHEN** ANTHROPIC_API_KEY is not configured
- **THEN** the "Extract Data" button SHALL NOT be visible in the UI

### Requirement: Extraction results are persisted on the reference record

The system SHALL store extraction results durably on the InvoiceTemplateReference model so re-extraction is not needed.

#### Scenario: Results stored after successful extraction
- **WHEN** extraction completes successfully
- **THEN** extracted_data JSONField is populated with the full result
- **AND** extraction_status is set to "completed"

#### Scenario: Failed extraction tracked
- **WHEN** Claude API call fails (network error, API error, invalid response)
- **THEN** extraction_status is set to "failed"
- **AND** system displays an error message to the user
- **AND** user can retry the extraction

#### Scenario: Previously extracted data is shown without re-extraction
- **WHEN** user views a reference PDF that has already been extracted (extraction_status is "completed")
- **THEN** system displays the stored extraction results immediately
- **AND** does not make another Claude API call

#### Scenario: User can re-extract to update results
- **WHEN** user clicks "Re-extract" on a reference with existing extraction results
- **THEN** system sends the PDF to Claude again
- **AND** overwrites the previous extracted_data with fresh results

### Requirement: User can review extracted data before applying

The system SHALL display extraction results in a review panel, allowing users to inspect what was found before applying it to settings.

#### Scenario: Review panel shows legal data fields
- **WHEN** extraction results are available for a reference PDF
- **THEN** system displays all extracted legal_data fields in a readable format
- **AND** empty/null fields are clearly marked as "not found"

#### Scenario: Review panel shows design data
- **WHEN** extraction results include design data
- **THEN** system displays the extracted accent color as a color swatch with hex value
- **AND** displays header_text and footer_text if found

#### Scenario: Review panel shows layout description
- **WHEN** extraction results include layout data
- **THEN** system displays logo position, footer column count, and layout description text

### Requirement: User can apply extracted legal data to Company Data settings

The system SHALL allow users to apply extracted legal_data fields to the CompanyLegalData form.

#### Scenario: Apply legal data navigates to Company Data settings
- **WHEN** user clicks "Apply to Company Data" in the extraction review panel
- **THEN** system navigates to `/settings/company-data`
- **AND** pre-fills the form fields with the extracted legal_data values

#### Scenario: Apply does not overwrite with empty values
- **WHEN** extracted legal_data has null values for some fields
- **AND** the CompanyLegalData form already has values for those fields
- **THEN** existing values SHALL be preserved for null extracted fields
- **AND** only non-null extracted values SHALL pre-fill the form

#### Scenario: User can edit pre-filled values before saving
- **WHEN** form is pre-filled with extracted data
- **THEN** all fields remain editable
- **AND** user MUST explicitly click "Save" to persist the data

### Requirement: User can apply extracted design data to template settings

The system SHALL allow users to apply extracted design fields to the InvoiceTemplate settings.

#### Scenario: Apply accent color
- **WHEN** user clicks "Apply to Template" in the extraction review panel
- **AND** extraction includes an accent_color value
- **THEN** system updates the accent color field on the template settings form

#### Scenario: Apply header and footer text
- **WHEN** extraction includes header_text or footer_text
- **THEN** system updates the respective fields on the template settings form
- **AND** user MUST click "Save" to persist the changes

### Requirement: Extraction requires appropriate permissions

The system SHALL restrict extraction to users with the settings.write permission.

#### Scenario: Authorized user can extract
- **WHEN** user has settings.write permission
- **THEN** "Extract Data" button is visible and functional

#### Scenario: Unauthorized user cannot extract
- **WHEN** user does not have settings.write permission
- **THEN** "Extract Data" button is not visible
- **AND** GraphQL mutation returns a permission error if called directly
