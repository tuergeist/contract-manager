## Context

Feedback currently goes through Todoist via `TodoistService` in `backend/apps/core/todoist.py`. The GraphQL mutation `submit_feedback` in `core/schema.py` directly instantiates `TodoistService`. The `feedback_enabled` query checks for `TODOIST_API_TOKEN` + `TODOIST_PROJECT_ID`.

The goal is to add GitHub Issues as an alternative backend, selectable via env var, without changing the frontend or GraphQL API.

## Goals / Non-Goals

**Goals:**
- Add GitHub Issues as a feedback backend (create issues with labels, embed screenshots)
- Make the backend selectable via a single `FEEDBACK_BACKEND` env var
- Keep the same `submitFeedback` mutation and `feedbackEnabled` query contract
- Preserve the existing Todoist backend exactly as-is

**Non-Goals:**
- No UI for selecting the feedback backend (env var only)
- No bidirectional sync (reading issues back from GitHub)
- No support for GitHub Enterprise Server (public GitHub API only, for now)
- No migration of existing Todoist feedback to GitHub

## Decisions

### 1. Provider pattern via abstract base class

Introduce a `FeedbackService` abstract base class with `create_feedback()` and `is_configured()` methods. `TodoistFeedbackService` wraps the existing `TodoistService`. `GitHubFeedbackService` is the new implementation.

A factory function `get_feedback_service()` reads `FEEDBACK_BACKEND` and returns the appropriate instance.

**Why not duck typing / protocol?** An ABC makes the contract explicit and gives clear errors if a method is missing. The two implementations are small enough that the overhead is negligible.

### 2. `FEEDBACK_BACKEND` setting with `todoist` default

```
FEEDBACK_BACKEND = "todoist"  # or "github"
```

Default is `todoist` so existing deployments work unchanged. If set to `github`, requires `GITHUB_FEEDBACK_REPO` and `GITHUB_FEEDBACK_TOKEN`.

**Why not auto-detect from which env vars are set?** Explicit selection avoids ambiguity when both are configured (e.g., during migration). The admin chooses which one to use.

### 3. GitHub Issues API via httpx

Use the GitHub REST API v3 (`POST /repos/{owner}/{repo}/issues`) with a personal access token (PAT) or fine-grained token with `issues:write` scope.

**Why not PyGithub?** Adding a dependency for a single API call is unnecessary. httpx is already in the project. The Issues API is straightforward: one POST to create, labels in the body.

### 4. Screenshots as inline base64 markdown images

GitHub Issues support markdown with inline images via `![screenshot](data:image/png;base64,...)`. However, data URIs in GitHub markdown are not rendered. Instead, we'll include the screenshot as a collapsible details block with the base64 data, and note that it can be viewed by copying the data URI.

**Better alternative:** Upload the image via the GitHub API isn't publicly available for issues. Instead, skip screenshot embedding for GitHub — just mention that a screenshot was provided but couldn't be attached. The feedback text and metadata are the important parts.

**Final decision:** For GitHub backend, skip screenshot upload. Log a note that screenshot was provided but not attached. This keeps the implementation simple and avoids fragile workarounds.

### 5. Label mapping

Map feedback types to GitHub issue labels:
- `bug` → `bug`
- `feature` → `enhancement`
- `general` → `feedback`

Labels are created automatically by the GitHub API if they don't exist on the repo (the API accepts label names directly).

### 6. Refactor `submit_feedback` mutation

The mutation currently directly calls `TodoistService`. Refactor to:
1. Call `get_feedback_service()` to get the active provider
2. Call `service.create_feedback(title, description, feedback_type, screenshot)`
3. Return the result URL (Todoist task URL or GitHub issue URL)

The existing Todoist logic (description building, screenshot upload) moves into `TodoistFeedbackService.create_feedback()`.

## Risks / Trade-offs

- **Screenshot loss on GitHub** → Acceptable trade-off. Text feedback + metadata is the primary value. Can be revisited later with a file storage upload approach.
- **GitHub API rate limiting** → 5,000 req/hour for authenticated requests. Feedback volume is far below this. No mitigation needed.
- **Token permissions** → Fine-grained PAT with `issues:write` on a single repo is the minimum. Document this in settings.
- **Label auto-creation** → GitHub API creates labels if they don't exist, but with a default color. Not a problem — admin can customize colors in GitHub.
