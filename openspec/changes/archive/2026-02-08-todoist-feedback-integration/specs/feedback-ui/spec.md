## ADDED Requirements

### Requirement: Feedback button is always visible

The system SHALL display a floating feedback button in the bottom-right corner of every page for authenticated users.

#### Scenario: Button visible on all pages
- **WHEN** user navigates to any page in the application
- **THEN** feedback button is visible in the bottom-right corner

#### Scenario: Button hidden for unauthenticated users
- **WHEN** user is not logged in
- **THEN** feedback button is not displayed

### Requirement: Feedback modal with type selection

The system SHALL display a modal dialog when the feedback button is clicked, allowing users to select feedback type and enter details.

#### Scenario: Open feedback modal
- **WHEN** user clicks the feedback button
- **THEN** modal opens with feedback type selection (Bug Report, Feature Request, General Feedback)

#### Scenario: Submit feedback with required fields
- **WHEN** user selects a feedback type, enters a title, and clicks submit
- **THEN** feedback is submitted to the backend
- **AND** modal closes with success confirmation

#### Scenario: Validation prevents empty submission
- **WHEN** user clicks submit without entering a title
- **THEN** validation error is displayed
- **AND** form is not submitted

### Requirement: Screenshot capture capability

The system SHALL allow users to capture a screenshot of the current page and attach it to their feedback.

#### Scenario: Capture screenshot automatically
- **WHEN** user opens feedback modal
- **THEN** screenshot of current page is captured automatically
- **AND** preview thumbnail is displayed in the modal

#### Scenario: Retake screenshot
- **WHEN** user clicks "Retake Screenshot" button
- **THEN** new screenshot is captured
- **AND** preview is updated

#### Scenario: Remove screenshot
- **WHEN** user clicks remove button on screenshot preview
- **THEN** screenshot is removed from the feedback
- **AND** feedback can be submitted without screenshot

### Requirement: Context information included automatically

The system SHALL automatically include contextual information with each feedback submission.

#### Scenario: Context captured on submit
- **WHEN** user submits feedback
- **THEN** current page URL is included
- **AND** user's name and email are included
- **AND** timestamp is included
- **AND** browser/viewport information is included

### Requirement: Loading and error states

The system SHALL display appropriate loading and error states during feedback submission.

#### Scenario: Loading state during submission
- **WHEN** feedback is being submitted
- **THEN** submit button shows loading indicator
- **AND** form inputs are disabled

#### Scenario: Error handling on submission failure
- **WHEN** feedback submission fails
- **THEN** error message is displayed
- **AND** user can retry submission
