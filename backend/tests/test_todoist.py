"""Tests for TodoistService and Feedback mutation."""
import base64
from unittest.mock import Mock, patch

import httpx
import pytest

from apps.core.todoist import (
    TodoistService,
    TodoistAPIError,
    TodoistNotConfiguredError,
    TodoistTask,
)
from apps.core.schema import FeedbackType, FeedbackInput, FeedbackMutation


class TestTodoistServiceConfiguration:
    """Tests for Todoist configuration checks."""

    def test_create_task_raises_when_no_api_token(self, settings):
        """Should raise error when API token not configured."""
        settings.TODOIST_API_TOKEN = ""
        settings.TODOIST_PROJECT_ID = "test-project"

        service = TodoistService()

        with pytest.raises(TodoistNotConfiguredError) as exc_info:
            service.create_task("title", "description")

        assert "TODOIST_API_TOKEN" in str(exc_info.value)

    def test_create_task_raises_when_no_project_id(self, settings):
        """Should raise error when project ID not configured."""
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = ""

        service = TodoistService()

        with pytest.raises(TodoistNotConfiguredError) as exc_info:
            service.create_task("title", "description")

        assert "TODOIST_PROJECT_ID" in str(exc_info.value)


class TestTodoistCreateTask:
    """Tests for task creation."""

    @pytest.fixture
    def configured_settings(self, settings):
        """Configure Todoist settings for tests."""
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = "test-project-123"
        return settings

    @patch("apps.core.todoist.httpx.post")
    def test_creates_task_successfully(self, mock_post, configured_settings):
        """Should create task and return TodoistTask."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "url": "https://todoist.com/showTask?id=12345",
        }
        mock_response.text = '{"id": "12345"}'
        mock_post.return_value = mock_response

        service = TodoistService()
        result = service.create_task(
            title="Bug: Login fails",
            description="Users cannot login",
            feedback_type="bug",
        )

        assert isinstance(result, TodoistTask)
        assert result.id == "12345"
        assert "12345" in result.url

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.todoist.com/rest/v2/tasks"
        assert call_args[1]["json"]["content"] == "Bug: Login fails"
        assert call_args[1]["json"]["description"] == "Users cannot login"
        assert call_args[1]["json"]["project_id"] == "test-project-123"
        assert "bug" in call_args[1]["json"]["labels"]

    @patch("apps.core.todoist.httpx.post")
    def test_adds_correct_label_for_feature(self, mock_post, configured_settings):
        """Should add feature-request label for feature type."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "url": "http://test"}
        mock_response.text = '{"id": "123"}'
        mock_post.return_value = mock_response

        service = TodoistService()
        service.create_task("Feature", "desc", feedback_type="feature")

        call_args = mock_post.call_args
        assert "feature-request" in call_args[1]["json"]["labels"]

    @patch("apps.core.todoist.httpx.post")
    def test_adds_correct_label_for_general(self, mock_post, configured_settings):
        """Should add feedback label for general type."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "url": "http://test"}
        mock_response.text = '{"id": "123"}'
        mock_post.return_value = mock_response

        service = TodoistService()
        service.create_task("General", "desc", feedback_type="general")

        call_args = mock_post.call_args
        assert "feedback" in call_args[1]["json"]["labels"]

    @patch("apps.core.todoist.httpx.post")
    def test_handles_timeout_error(self, mock_post, configured_settings):
        """Should raise TodoistAPIError on timeout."""
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        service = TodoistService()

        with pytest.raises(TodoistAPIError) as exc_info:
            service.create_task("title", "description")

        assert "timeout" in str(exc_info.value).lower()

    @patch("apps.core.todoist.httpx.post")
    def test_handles_rate_limit(self, mock_post, configured_settings):
        """Should raise TodoistAPIError on rate limit (429)."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_post.return_value = mock_response

        service = TodoistService()

        with pytest.raises(TodoistAPIError) as exc_info:
            service.create_task("title", "description")

        assert exc_info.value.status_code == 429
        assert "rate limit" in str(exc_info.value).lower()

    @patch("apps.core.todoist.httpx.post")
    def test_handles_auth_error(self, mock_post, configured_settings):
        """Should raise TodoistAPIError on authentication failure (401)."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        service = TodoistService()

        with pytest.raises(TodoistAPIError) as exc_info:
            service.create_task("title", "description")

        assert exc_info.value.status_code == 401
        assert "token" in str(exc_info.value).lower()


class TestTodoistUploadFile:
    """Tests for file upload."""

    @pytest.fixture
    def configured_settings(self, settings):
        """Configure Todoist settings for tests."""
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = "test-project-123"
        return settings

    @patch("apps.core.todoist.httpx.post")
    def test_uploads_file_successfully(self, mock_post, configured_settings):
        """Should upload file and return URL."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_url": "https://todoist.com/uploads/abc123.png"
        }
        mock_response.text = '{"file_url": "https://todoist.com/uploads/abc123.png"}'
        mock_post.return_value = mock_response

        service = TodoistService()
        result = service.upload_file(b"fake image data", "screenshot.png")

        assert result == "https://todoist.com/uploads/abc123.png"

        # Verify API call used sync URL
        call_args = mock_post.call_args
        assert "sync/v9/uploads/add" in call_args[0][0]

    @patch("apps.core.todoist.httpx.post")
    def test_raises_error_when_no_file_url_returned(self, mock_post, configured_settings):
        """Should raise error if Todoist doesn't return file URL."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = "{}"
        mock_post.return_value = mock_response

        service = TodoistService()

        with pytest.raises(TodoistAPIError) as exc_info:
            service.upload_file(b"data", "file.png")

        assert "file URL" in str(exc_info.value)


class TestTodoistAddComment:
    """Tests for adding comments with attachments."""

    @pytest.fixture
    def configured_settings(self, settings):
        """Configure Todoist settings for tests."""
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = "test-project-123"
        return settings

    @patch("apps.core.todoist.httpx.post")
    def test_adds_comment_with_attachment(self, mock_post, configured_settings):
        """Should add comment with file attachment."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "comment-123"}
        mock_response.text = '{"id": "comment-123"}'
        mock_post.return_value = mock_response

        service = TodoistService()
        service.add_comment_with_attachment(
            task_id="task-123",
            comment="Screenshot attached",
            file_url="https://todoist.com/uploads/abc.png",
        )

        call_args = mock_post.call_args
        assert "comments" in call_args[0][0]
        assert call_args[1]["json"]["task_id"] == "task-123"
        assert call_args[1]["json"]["content"] == "Screenshot attached"
        assert call_args[1]["json"]["attachment"]["file_url"] == "https://todoist.com/uploads/abc.png"


class TestTodoistUploadScreenshot:
    """Tests for screenshot upload workflow."""

    @pytest.fixture
    def configured_settings(self, settings):
        """Configure Todoist settings for tests."""
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = "test-project-123"
        return settings

    @patch("apps.core.todoist.httpx.post")
    def test_uploads_screenshot_with_data_url_prefix(self, mock_post, configured_settings):
        """Should handle base64 with data URL prefix."""
        # Create mock responses for upload and comment
        upload_response = Mock()
        upload_response.is_success = True
        upload_response.status_code = 200
        upload_response.json.return_value = {"file_url": "https://todoist.com/uploads/abc.png"}
        upload_response.text = '{"file_url": "https://todoist.com/uploads/abc.png"}'

        comment_response = Mock()
        comment_response.is_success = True
        comment_response.status_code = 200
        comment_response.json.return_value = {"id": "comment-123"}
        comment_response.text = '{"id": "comment-123"}'

        mock_post.side_effect = [upload_response, comment_response]

        service = TodoistService()

        # Base64 encoded PNG (minimal valid PNG header)
        raw_data = b"fake png data"
        base64_data = base64.b64encode(raw_data).decode()
        data_url = f"data:image/png;base64,{base64_data}"

        service.upload_screenshot_to_task("task-123", data_url)

        # Verify upload was called with decoded data
        assert mock_post.call_count == 2

    @patch("apps.core.todoist.httpx.post")
    def test_uploads_screenshot_without_prefix(self, mock_post, configured_settings):
        """Should handle plain base64 without data URL prefix."""
        upload_response = Mock()
        upload_response.is_success = True
        upload_response.status_code = 200
        upload_response.json.return_value = {"file_url": "https://todoist.com/uploads/abc.png"}
        upload_response.text = '{"file_url": "https://todoist.com/uploads/abc.png"}'

        comment_response = Mock()
        comment_response.is_success = True
        comment_response.status_code = 200
        comment_response.json.return_value = {"id": "comment-123"}
        comment_response.text = '{"id": "comment-123"}'

        mock_post.side_effect = [upload_response, comment_response]

        service = TodoistService()

        raw_data = b"fake png data"
        base64_data = base64.b64encode(raw_data).decode()

        service.upload_screenshot_to_task("task-123", base64_data)

        assert mock_post.call_count == 2

    def test_raises_error_for_invalid_base64(self, configured_settings):
        """Should raise error for invalid base64 data."""
        service = TodoistService()

        with pytest.raises(TodoistAPIError) as exc_info:
            service.upload_screenshot_to_task("task-123", "not valid base64!!!")

        assert "Invalid screenshot" in str(exc_info.value)


class TestSubmitFeedbackMutation:
    """Tests for the submitFeedback GraphQL mutation."""

    @pytest.fixture
    def configured_settings(self, settings):
        """Configure Todoist settings for tests."""
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = "test-project-123"
        return settings

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock()
        user.first_name = "Test"
        user.last_name = "User"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_info(self, mock_user):
        """Create mock GraphQL info with user context."""
        info = Mock()
        info.context = Mock()
        info.context.user = mock_user
        return info

    def test_requires_authentication(self):
        """Should return error when user not authenticated."""
        info = Mock()
        info.context = Mock()
        info.context.user = None

        mutation = FeedbackMutation()
        input_data = FeedbackInput(
            type=FeedbackType.BUG,
            title="Test bug",
        )

        result = mutation.submit_feedback(info, input_data)

        assert result.success is False
        assert "Authentication" in result.error

    @patch("apps.core.todoist.httpx.post")
    def test_submits_feedback_successfully(self, mock_post, configured_settings, mock_info):
        """Should create Todoist task and return URL."""
        # Mock successful task creation
        task_response = Mock()
        task_response.is_success = True
        task_response.status_code = 200
        task_response.json.return_value = {
            "id": "task-456",
            "url": "https://todoist.com/showTask?id=task-456",
        }
        task_response.text = '{"id": "task-456"}'
        mock_post.return_value = task_response

        mutation = FeedbackMutation()
        input_data = FeedbackInput(
            type=FeedbackType.BUG,
            title="Login button broken",
            description="Cannot click the login button",
            page_url="https://app.example.com/login",
            viewport="1920x1080",
        )

        result = mutation.submit_feedback(mock_info, input_data)

        assert result.success is True
        assert result.task_url == "https://todoist.com/showTask?id=task-456"
        assert result.error is None

    @patch("apps.core.todoist.httpx.post")
    def test_includes_user_info_in_description(self, mock_post, configured_settings, mock_info):
        """Should include user info in task description."""
        task_response = Mock()
        task_response.is_success = True
        task_response.status_code = 200
        task_response.json.return_value = {"id": "123", "url": "http://test"}
        task_response.text = '{"id": "123"}'
        mock_post.return_value = task_response

        mutation = FeedbackMutation()
        input_data = FeedbackInput(
            type=FeedbackType.FEATURE,
            title="New feature request",
            description="Please add dark mode",
        )

        mutation.submit_feedback(mock_info, input_data)

        # Check the description passed to Todoist
        call_args = mock_post.call_args
        description = call_args[1]["json"]["description"]
        assert "Test User" in description
        assert "test@example.com" in description
        assert "Please add dark mode" in description

    @patch("apps.core.todoist.httpx.post")
    def test_uploads_screenshot_when_provided(self, mock_post, configured_settings, mock_info):
        """Should upload screenshot and attach to task."""
        # Mock task creation
        task_response = Mock()
        task_response.is_success = True
        task_response.status_code = 200
        task_response.json.return_value = {"id": "task-789", "url": "http://test"}
        task_response.text = '{"id": "task-789"}'

        # Mock file upload
        upload_response = Mock()
        upload_response.is_success = True
        upload_response.status_code = 200
        upload_response.json.return_value = {"file_url": "https://todoist.com/uploads/abc.png"}
        upload_response.text = '{"file_url": "https://todoist.com/uploads/abc.png"}'

        # Mock comment creation
        comment_response = Mock()
        comment_response.is_success = True
        comment_response.status_code = 200
        comment_response.json.return_value = {"id": "comment-123"}
        comment_response.text = '{"id": "comment-123"}'

        mock_post.side_effect = [task_response, upload_response, comment_response]

        mutation = FeedbackMutation()

        # Create valid base64 data
        screenshot_data = base64.b64encode(b"fake png data").decode()

        input_data = FeedbackInput(
            type=FeedbackType.BUG,
            title="Visual bug",
            screenshot=f"data:image/png;base64,{screenshot_data}",
        )

        result = mutation.submit_feedback(mock_info, input_data)

        assert result.success is True
        # Should have 3 API calls: create task, upload file, add comment
        assert mock_post.call_count == 3

    def test_returns_error_when_todoist_not_configured(self, settings, mock_info):
        """Should return user-friendly error when Todoist not configured."""
        settings.TODOIST_API_TOKEN = ""
        settings.TODOIST_PROJECT_ID = ""

        mutation = FeedbackMutation()
        input_data = FeedbackInput(
            type=FeedbackType.GENERAL,
            title="Test feedback",
        )

        result = mutation.submit_feedback(mock_info, input_data)

        assert result.success is False
        assert "not configured" in result.error

    @patch("apps.core.todoist.httpx.post")
    def test_handles_todoist_api_error(self, mock_post, configured_settings, mock_info):
        """Should return error on Todoist API failure."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        mutation = FeedbackMutation()
        input_data = FeedbackInput(
            type=FeedbackType.BUG,
            title="Test bug",
        )

        result = mutation.submit_feedback(mock_info, input_data)

        assert result.success is False
        assert result.error is not None
