## Why

Users need an easy way to report bugs and request features directly from the application. Currently, feedback requires switching to email or other tools, which creates friction and often results in missing context (no screenshots, unclear which page/state the issue occurred on). Integrating with Todoist provides a familiar task management interface while capturing rich context automatically.

## What Changes

- Add a floating feedback button accessible from all pages
- Implement a feedback modal with:
  - Type selection (bug report / feature request / general feedback)
  - Title and description fields
  - Screenshot capture capability (automatic or manual)
  - Optional file attachment
- Create Todoist integration backend:
  - Configure Todoist API credentials globally (environment variables)
  - Create tasks in designated Todoist project
  - Upload screenshots/attachments as task comments
  - Include page URL and user context in task description

## Capabilities

### New Capabilities

- `feedback-ui`: Frontend feedback button and modal for capturing user feedback with screenshots
- `todoist-integration`: Backend service for creating Todoist tasks with attachments and managing API configuration

### Modified Capabilities

<!-- No existing capabilities need spec-level changes -->

## Impact

- **Frontend**: New FeedbackButton component, FeedbackModal, screenshot capture utility
- **Backend**: New Todoist service, feedback API endpoints
- **Configuration**: Environment variables for Todoist API token and project ID
- **Dependencies**: Todoist API (external service), html2canvas or similar for screenshot capture
