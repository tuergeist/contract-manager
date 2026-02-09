## 1. Backend: Todoist Service

- [x] 1.1 Add TODOIST_API_TOKEN and TODOIST_PROJECT_ID to environment/settings
- [x] 1.2 Create TodoistService class with methods for task creation
- [x] 1.3 Implement file upload to Todoist (for screenshots)
- [x] 1.4 Implement comment creation with attachment
- [x] 1.5 Add error handling for Todoist API failures (timeout, rate limit)
- [x] 1.6 Add logging for Todoist API interactions

## 2. Backend: Feedback Mutation

- [x] 2.1 Create FeedbackInput type (type, title, description, screenshot base64)
- [x] 2.2 Create submitFeedback GraphQL mutation
- [x] 2.3 Implement context gathering (URL, user info, timestamp, browser)
- [x] 2.4 Integrate with TodoistService to create task
- [x] 2.5 Handle screenshot upload as task comment
- [x] 2.6 Return task URL on success

## 3. Frontend: Screenshot Utility

- [x] 3.1 Install html2canvas dependency
- [x] 3.2 Create captureScreenshot utility function
- [x] 3.3 Add compression to reduce screenshot file size
- [x] 3.4 Handle screenshot capture errors gracefully

## 4. Frontend: Feedback Components

- [x] 4.1 Create FeedbackButton component (floating, bottom-right)
- [x] 4.2 Create FeedbackModal component with form
- [x] 4.3 Add feedback type selector (Bug, Feature, General)
- [x] 4.4 Add title and description fields with validation
- [x] 4.5 Add screenshot preview with retake/remove options
- [x] 4.6 Implement loading and error states
- [x] 4.7 Add success confirmation on submit

## 5. Frontend: Integration

- [x] 5.1 Add FeedbackButton to App layout (visible on all pages)
- [x] 5.2 Create submitFeedback GraphQL mutation hook
- [x] 5.3 Connect modal form to mutation
- [x] 5.4 Gather context info (URL, viewport) on submit

## 6. Testing

- [x] 6.1 Write backend tests for TodoistService (mock API)
- [x] 6.2 Write backend tests for submitFeedback mutation
- [ ] 6.3 Write frontend tests for FeedbackModal component
- [ ] 6.4 Add E2E test for feedback submission flow

## 7. Documentation

- [ ] 7.1 Document environment variables in README/docker-compose
- [ ] 7.2 Document feedback feature for end users
