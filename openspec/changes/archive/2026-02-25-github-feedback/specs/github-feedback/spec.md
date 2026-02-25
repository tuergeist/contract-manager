## ADDED Requirements

### Requirement: Feedback backend selection via environment variable

The system SHALL support selecting the feedback backend via a `FEEDBACK_BACKEND` setting. Valid values are `todoist` (default) and `github`. When unset or empty, the system SHALL default to `todoist`.

#### Scenario: Default backend is Todoist
- **WHEN** `FEEDBACK_BACKEND` is not set
- **THEN** the system uses Todoist as the feedback backend

#### Scenario: GitHub backend selected
- **WHEN** `FEEDBACK_BACKEND` is set to `github`
- **THEN** the system uses GitHub Issues as the feedback backend

### Requirement: Feedback enabled check supports both backends

The `feedbackEnabled` GraphQL query SHALL return `true` when the selected backend is fully configured, and `false` otherwise.

#### Scenario: Todoist backend configured
- **WHEN** `FEEDBACK_BACKEND` is `todoist` and both `TODOIST_API_TOKEN` and `TODOIST_PROJECT_ID` are set
- **THEN** `feedbackEnabled` returns `true`

#### Scenario: GitHub backend configured
- **WHEN** `FEEDBACK_BACKEND` is `github` and both `GITHUB_FEEDBACK_REPO` and `GITHUB_FEEDBACK_TOKEN` are set
- **THEN** `feedbackEnabled` returns `true`

#### Scenario: GitHub backend missing config
- **WHEN** `FEEDBACK_BACKEND` is `github` and `GITHUB_FEEDBACK_TOKEN` is empty
- **THEN** `feedbackEnabled` returns `false`

### Requirement: GitHub feedback creates an issue

When the GitHub backend is active, `submitFeedback` SHALL create a GitHub issue in the configured repository via the GitHub REST API.

#### Scenario: Issue created with title and description
- **WHEN** a user submits feedback with title "Login broken" and description "Cannot log in after password change"
- **THEN** the system creates a GitHub issue with that title, a markdown body containing the description and user metadata, and returns the issue URL

#### Scenario: Issue includes user metadata
- **WHEN** feedback is submitted
- **THEN** the issue body includes submitter name, email, feedback type, timestamp, page URL, and viewport (when provided)

### Requirement: GitHub feedback maps types to labels

The system SHALL map feedback types to GitHub issue labels: `bug` → `bug`, `feature` → `enhancement`, `general` → `feedback`.

#### Scenario: Bug feedback gets bug label
- **WHEN** feedback of type `bug` is submitted
- **THEN** the created GitHub issue has the label `bug`

#### Scenario: Feature feedback gets enhancement label
- **WHEN** feedback of type `feature` is submitted
- **THEN** the created GitHub issue has the label `enhancement`

### Requirement: GitHub feedback skips screenshot attachment

The GitHub backend SHALL NOT attempt to attach screenshots. If a screenshot is provided, it SHALL be silently ignored (logged at debug level).

#### Scenario: Screenshot provided but not attached
- **WHEN** feedback includes a base64 screenshot
- **THEN** the issue is created successfully without the screenshot, and a debug log is emitted

### Requirement: Abstract feedback service interface

The system SHALL use an abstract `FeedbackService` base class with `create_feedback()` and `is_configured()` methods. Both Todoist and GitHub implementations SHALL conform to this interface.

#### Scenario: Factory returns correct service
- **WHEN** `FEEDBACK_BACKEND` is `github`
- **THEN** `get_feedback_service()` returns a `GitHubFeedbackService` instance

#### Scenario: Factory returns Todoist by default
- **WHEN** `FEEDBACK_BACKEND` is `todoist` or unset
- **THEN** `get_feedback_service()` returns a `TodoistFeedbackService` instance

### Requirement: GraphQL API unchanged

The `submitFeedback` mutation and `feedbackEnabled` query SHALL maintain their existing GraphQL schema. No input or return type changes.

#### Scenario: Frontend works without changes
- **WHEN** the backend is switched from Todoist to GitHub
- **THEN** the frontend `submitFeedback` mutation works identically, returning `success`, `error`, and `taskUrl` (which is the GitHub issue URL)
