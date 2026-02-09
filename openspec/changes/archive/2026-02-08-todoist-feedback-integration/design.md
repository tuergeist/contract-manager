## Context

The contract-manager application currently has no built-in feedback mechanism. Users report issues via email or Slack, often without sufficient context (page URL, application state, visual reference). This leads to back-and-forth clarification and slower resolution.

ReviewSpark (a sister project) has a working implementation of Todoist-integrated feedback that we can reference. The pattern involves a floating button, modal form, screenshot capture, and backend API that creates Todoist tasks with file attachments.

Todoist was chosen as the task management backend because it's already used by the team for project management, has a well-documented API, and supports file attachments via comments.

## Goals / Non-Goals

**Goals:**
- Provide a low-friction way to submit feedback from any page
- Automatically capture context (URL, user, timestamp)
- Support screenshot capture for visual bug reports
- Store feedback as Todoist tasks for existing workflow integration
- Allow per-tenant configuration of Todoist credentials

**Non-Goals:**
- Building a full ticket/issue management system
- Two-way sync with Todoist (read tasks back into the app)
- Support for other task management systems (Asana, Jira, etc.)
- Public/anonymous feedback submission (requires authentication)

## Decisions

### 1. Screenshot Capture Library: html2canvas

**Decision**: Use `html2canvas` for client-side screenshot capture.

**Alternatives considered**:
- `dom-to-image`: Similar functionality but less maintained
- Browser native `getDisplayMedia()`: Requires user permission prompt, captures entire screen not just app
- Server-side rendering: Would require sending DOM state, complex and slow

**Rationale**: html2canvas is mature, well-maintained, and captures the current viewport without additional user interaction. It works entirely client-side.

### 2. Attachment Upload Flow: Via Backend Proxy

**Decision**: Upload files through our backend, which then uploads to Todoist.

**Alternatives considered**:
- Direct browser-to-Todoist upload: Would expose API token to client
- Pre-signed URLs: Todoist API doesn't support this pattern

**Rationale**: Keeps Todoist API token secure on the server. Backend receives base64 screenshot, converts to file, uploads to Todoist as comment attachment.

### 3. API Structure: Single Endpoint with GraphQL Mutation

**Decision**: Add `submitFeedback` GraphQL mutation that handles task creation and file upload.

**Alternatives considered**:
- REST endpoint: Would be inconsistent with existing API pattern
- Separate mutations for task and attachments: Unnecessary complexity

**Rationale**: Consistent with existing GraphQL API. Single mutation simplifies frontend code.

### 4. Todoist Configuration: Environment Variables

**Decision**: Store Todoist API token and project ID in environment variables.

**Alternatives considered**:
- Database storage per tenant: Unnecessary complexity for single-team deployment
- Per-user configuration: Unnecessary complexity, feedback goes to shared project

**Rationale**: Simple and secure. Environment variables are the standard way to handle API credentials. No database storage needed, no UI configuration required.

### 5. Feedback Button Position: Fixed Bottom-Right

**Decision**: Floating button fixed to bottom-right corner, always visible.

**Alternatives considered**:
- In navigation bar: Takes up nav space, less discoverable
- In user menu: Too hidden, reduces usage
- Keyboard shortcut only: Not discoverable for new users

**Rationale**: Bottom-right is conventional placement for support/feedback widgets. Always visible encourages usage without being intrusive.

## Risks / Trade-offs

**[Risk] Todoist API rate limiting** → Feedback submissions are infrequent (likely <10/day). Well within Todoist limits. Could add client-side debouncing if needed.

**[Risk] Large screenshot files** → Compress screenshots client-side before upload. Set max file size limit (e.g., 5MB).

**[Risk] Todoist API token exposure** → Token stored encrypted in database, never sent to client. All Todoist API calls go through backend.

**[Risk] html2canvas rendering issues** → Some CSS features may not render correctly. Accept this limitation; screenshots are "good enough" for context, not pixel-perfect.

**[Trade-off] Single Todoist project** → All feedback goes to one configured project. Simplifies setup but requires manual triage. Could add label-based routing later.

## Migration Plan

1. Add tenant configuration fields for Todoist (API token, project ID)
2. Deploy backend with new feedback mutation
3. Deploy frontend with feedback button/modal
4. Document setup process for admins
5. No data migration needed - new feature

**Rollback**: Remove frontend components to disable feature. Backend changes are additive and harmless.
