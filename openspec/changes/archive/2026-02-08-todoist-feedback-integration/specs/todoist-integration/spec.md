## ADDED Requirements

### Requirement: Todoist configuration via environment

The system SHALL read Todoist API credentials from environment variables.

#### Scenario: Configuration loaded from environment
- **WHEN** application starts
- **THEN** Todoist API token is read from TODOIST_API_TOKEN environment variable
- **AND** Todoist project ID is read from TODOIST_PROJECT_ID environment variable

#### Scenario: Missing configuration detected
- **WHEN** feedback is submitted but TODOIST_API_TOKEN is not set
- **THEN** error is returned indicating Todoist is not configured

### Requirement: Create Todoist task from feedback

The system SHALL create a Todoist task when feedback is submitted.

#### Scenario: Task created with feedback details
- **WHEN** feedback is submitted
- **THEN** new task is created in configured Todoist project
- **AND** task title matches feedback title
- **AND** task description includes feedback type, description, page URL, and user info

#### Scenario: Task labeled by feedback type
- **WHEN** feedback is submitted
- **THEN** task is created with label matching feedback type (bug, feature, feedback)

### Requirement: Upload screenshot as task attachment

The system SHALL upload screenshots to Todoist as task comment attachments.

#### Scenario: Screenshot attached to task
- **WHEN** feedback with screenshot is submitted
- **THEN** screenshot is uploaded to Todoist
- **AND** comment with screenshot attachment is added to the task

#### Scenario: Feedback without screenshot succeeds
- **WHEN** feedback without screenshot is submitted
- **THEN** task is created successfully without attachment

### Requirement: API token security

The system SHALL protect Todoist API tokens from exposure.

#### Scenario: Token only on server
- **WHEN** application is running
- **THEN** Todoist API token is only accessible server-side via environment variable
- **AND** token is never sent to client in any API response

### Requirement: Graceful degradation when Todoist unavailable

The system SHALL handle Todoist API failures gracefully.

#### Scenario: Todoist API timeout
- **WHEN** Todoist API does not respond within timeout period
- **THEN** error is returned to user with message to try again later
- **AND** submission is not lost (can be retried)

#### Scenario: Todoist not configured
- **WHEN** feedback is submitted but Todoist environment variables are not set
- **THEN** clear error message is displayed indicating Todoist is not configured

### Requirement: Feedback GraphQL mutation

The system SHALL provide a GraphQL mutation for submitting feedback.

#### Scenario: Submit feedback mutation
- **WHEN** `submitFeedback` mutation is called with type, title, description, and optional screenshot
- **THEN** feedback is processed and Todoist task is created
- **AND** mutation returns success status and task URL

#### Scenario: Authentication required
- **WHEN** unauthenticated request calls `submitFeedback` mutation
- **THEN** authentication error is returned
