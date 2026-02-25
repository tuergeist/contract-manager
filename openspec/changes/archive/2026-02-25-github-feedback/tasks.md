## Tasks

### 1. Settings

- [x] 1.1 Add `FEEDBACK_BACKEND = env("FEEDBACK_BACKEND", default="todoist")` to `config/settings/base.py`
- [x] 1.2 Add `GITHUB_FEEDBACK_REPO = env("GITHUB_FEEDBACK_REPO", default="")` (format: `owner/repo`)
- [x] 1.3 Add `GITHUB_FEEDBACK_TOKEN = env("GITHUB_FEEDBACK_TOKEN", default="")`

### 2. Abstract feedback service

- [x] 2.1 Create `backend/apps/core/feedback.py` with `FeedbackResult` dataclass (`url: str`) and `FeedbackService` ABC with `is_configured() -> bool` and `create_feedback(title, description, feedback_type, screenshot) -> FeedbackResult`
- [x] 2.2 Add `get_feedback_service() -> FeedbackService` factory that reads `FEEDBACK_BACKEND` and returns `TodoistFeedbackService` or `GitHubFeedbackService`

### 3. Todoist adapter

- [x] 3.1 Create `TodoistFeedbackService(FeedbackService)` in `feedback.py` that wraps existing `TodoistService`
- [x] 3.2 `is_configured()`: check `TODOIST_API_TOKEN` and `TODOIST_PROJECT_ID` are set
- [x] 3.3 `create_feedback()`: move description-building and screenshot-upload logic from `submit_feedback` mutation into this method

### 4. GitHub service

- [x] 4.1 Create `backend/apps/core/github_feedback.py` with `GitHubFeedbackService(FeedbackService)`
- [x] 4.2 `is_configured()`: check `GITHUB_FEEDBACK_REPO` and `GITHUB_FEEDBACK_TOKEN` are set
- [x] 4.3 `create_feedback()`: POST to `https://api.github.com/repos/{repo}/issues` with title, markdown body, and labels
- [x] 4.4 Label mapping: `bug` → `bug`, `feature` → `enhancement`, `general` → `feedback`
- [x] 4.5 Skip screenshot with debug log when provided

### 5. Refactor GraphQL mutation

- [x] 5.1 Update `feedback_enabled` query to use `get_feedback_service().is_configured()`
- [x] 5.2 Update `submit_feedback` mutation to use `get_feedback_service().create_feedback()` instead of direct `TodoistService` calls
- [x] 5.3 Map `FeedbackResult.url` to `task_url` in `FeedbackResult` GraphQL type

### 6. Tests

- [x] 6.1 Test `get_feedback_service()` returns `TodoistFeedbackService` by default
- [x] 6.2 Test `get_feedback_service()` returns `GitHubFeedbackService` when `FEEDBACK_BACKEND=github`
- [x] 6.3 Test `GitHubFeedbackService.is_configured()` with/without env vars
- [x] 6.4 Test `GitHubFeedbackService.create_feedback()` creates issue (mock httpx)
- [x] 6.5 Test label mapping for all three feedback types
- [x] 6.6 Test screenshot is skipped with debug log
- [x] 6.7 Test `feedback_enabled` query works with both backends
- [x] 6.8 Test existing Todoist tests still pass after refactor
