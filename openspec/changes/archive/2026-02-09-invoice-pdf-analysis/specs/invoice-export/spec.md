## ADDED Requirements

### Requirement: Template settings page shows extraction controls for reference PDFs

The invoice template settings page SHALL display extraction controls alongside each uploaded reference PDF, enabling users to trigger and review data extraction.

#### Scenario: Reference PDF shows extract button
- **WHEN** a reference PDF is listed on the template settings page
- **AND** ANTHROPIC_API_KEY is configured
- **THEN** each reference PDF row displays an "Extract Data" button

#### Scenario: Reference PDF shows extraction status
- **WHEN** a reference PDF has been extracted (extraction_status is "completed")
- **THEN** the reference row displays a success indicator
- **AND** shows an "View Results" button to display the extraction review panel

#### Scenario: Reference PDF shows failed extraction
- **WHEN** a reference PDF extraction has failed (extraction_status is "failed")
- **THEN** the reference row displays a failure indicator
- **AND** shows a "Retry" button to re-attempt extraction

#### Scenario: Extraction controls hidden without API key
- **WHEN** ANTHROPIC_API_KEY is not configured
- **THEN** no extraction buttons are shown for any reference PDF
- **AND** reference PDFs are still uploadable and deletable as before

### Requirement: Template settings page displays extraction review panel

The template settings page SHALL include an expandable review panel showing extraction results with actions to apply the data.

#### Scenario: Review panel displays after extraction
- **WHEN** extraction completes successfully for a reference PDF
- **THEN** a review panel expands below the reference PDF list
- **AND** shows extracted legal data, design settings, and layout description in organized sections

#### Scenario: Review panel has apply actions
- **WHEN** review panel is visible
- **THEN** it displays an "Apply to Company Data" button for legal data
- **AND** an "Apply to Template" button for design settings
- **AND** both buttons are clearly labeled with what they will do

#### Scenario: Review panel is dismissible
- **WHEN** user clicks outside the review panel or clicks a close button
- **THEN** the review panel collapses
- **AND** extraction results remain stored and can be viewed again
