## MODIFIED Requirements

### Requirement: List contract attachments
The system SHALL display all attachments for a contract to authenticated users within the same tenant.

#### Scenario: View attachments on contract detail
- **WHEN** user views a contract detail page
- **THEN** system displays an Attachments tab
- **THEN** tab shows list of attachments with filename, size, upload date, and uploader
- **THEN** each attachment has download and delete actions
- **THEN** PDF attachments SHALL additionally display an "Analyze" action button

#### Scenario: Contract has no attachments
- **WHEN** user views attachments tab for contract with no files
- **THEN** system displays empty state message "No attachments"

#### Scenario: Analyze button triggers PDF analysis
- **WHEN** user clicks the "Analyze" button on a PDF attachment
- **THEN** system triggers the PDF analysis flow for that attachment
- **THEN** the analysis review panel is displayed on the contract detail page

#### Scenario: Analyze button only on PDFs
- **WHEN** attachment is not a PDF (e.g., .xlsx, .png, .doc)
- **THEN** no "Analyze" button is shown for that attachment
