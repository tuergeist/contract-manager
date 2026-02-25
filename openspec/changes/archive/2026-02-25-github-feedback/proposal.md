## Why

Feedback submission currently only works via Todoist, which requires a Todoist account and API token. Many teams already use GitHub for issue tracking. Adding GitHub Issues as an alternative backend makes the feedback feature accessible without additional tooling, and keeps feedback alongside code in a single repository.

## What Changes

- Introduce a backend-agnostic feedback service interface with two implementations: Todoist (existing) and GitHub Issues (new)
- Add `FEEDBACK_BACKEND` setting to select the active provider (`todoist` or `github`)
- Add `GITHUB_FEEDBACK_REPO` and `GITHUB_FEEDBACK_TOKEN` settings for the GitHub backend
- GitHub backend creates issues with labels matching feedback type (bug, feature-request, feedback)
- Screenshot handling: GitHub backend uploads the image as a base64-embedded markdown image in the issue body (no separate upload API needed)
- `feedback_enabled` query remains the single check — returns true if the selected backend is configured
- Frontend unchanged — the GraphQL API stays the same, only the backend routing changes

## Capabilities

### New Capabilities

- `github-feedback`: GitHub Issues backend for feedback submission — creates issues, attaches screenshots, maps feedback types to labels

### Modified Capabilities

- (none — the existing Todoist integration is preserved as-is, just wrapped behind the provider selection)

## Impact

- **Backend**: New `github.py` service module alongside existing `todoist.py`, refactored `submit_feedback` mutation to dispatch to selected backend
- **Settings**: 3 new env vars (`FEEDBACK_BACKEND`, `GITHUB_FEEDBACK_REPO`, `GITHUB_FEEDBACK_TOKEN`)
- **Dependencies**: `httpx` already available (used by Todoist), no new dependencies
- **Frontend**: No changes — same `submitFeedback` mutation and `feedbackEnabled` query
