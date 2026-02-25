"""Tests for feedback service abstraction and GitHub backend."""
import logging
from unittest.mock import Mock, patch

import httpx
import pytest

from apps.core.feedback import (
    FeedbackResult,
    TodoistFeedbackService,
    get_feedback_service,
)
from apps.core.github_feedback import (
    GitHubFeedbackError,
    GitHubFeedbackService,
    LABEL_MAP,
)
from apps.core.schema import CoreQuery, FeedbackInput, FeedbackMutation, FeedbackType


class TestGetFeedbackService:
    """Tests for the feedback service factory."""

    def test_returns_todoist_by_default(self, settings):
        settings.FEEDBACK_BACKEND = "todoist"
        service = get_feedback_service()
        assert isinstance(service, TodoistFeedbackService)

    def test_returns_todoist_when_unset(self, settings):
        if hasattr(settings, "FEEDBACK_BACKEND"):
            delattr(settings, "FEEDBACK_BACKEND")
        service = get_feedback_service()
        assert isinstance(service, TodoistFeedbackService)

    def test_returns_github_when_configured(self, settings):
        settings.FEEDBACK_BACKEND = "github"
        service = get_feedback_service()
        assert isinstance(service, GitHubFeedbackService)

    def test_case_insensitive_backend(self, settings):
        settings.FEEDBACK_BACKEND = "GitHub"
        service = get_feedback_service()
        assert isinstance(service, GitHubFeedbackService)


class TestGitHubFeedbackServiceConfiguration:
    """Tests for GitHubFeedbackService.is_configured()."""

    def test_configured_when_both_set(self, settings):
        settings.GITHUB_FEEDBACK_REPO = "owner/repo"
        settings.GITHUB_FEEDBACK_TOKEN = "ghp_test123"
        service = GitHubFeedbackService()
        assert service.is_configured() is True

    def test_not_configured_without_repo(self, settings):
        settings.GITHUB_FEEDBACK_REPO = ""
        settings.GITHUB_FEEDBACK_TOKEN = "ghp_test123"
        service = GitHubFeedbackService()
        assert service.is_configured() is False

    def test_not_configured_without_token(self, settings):
        settings.GITHUB_FEEDBACK_REPO = "owner/repo"
        settings.GITHUB_FEEDBACK_TOKEN = ""
        service = GitHubFeedbackService()
        assert service.is_configured() is False

    def test_not_configured_when_both_empty(self, settings):
        settings.GITHUB_FEEDBACK_REPO = ""
        settings.GITHUB_FEEDBACK_TOKEN = ""
        service = GitHubFeedbackService()
        assert service.is_configured() is False


class TestGitHubFeedbackServiceCreateFeedback:
    """Tests for GitHubFeedbackService.create_feedback()."""

    @pytest.fixture
    def configured_settings(self, settings):
        settings.FEEDBACK_BACKEND = "github"
        settings.GITHUB_FEEDBACK_REPO = "owner/repo"
        settings.GITHUB_FEEDBACK_TOKEN = "ghp_test123"
        return settings

    @patch("apps.core.github_feedback.httpx.post")
    def test_creates_issue_successfully(self, mock_post, configured_settings):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/issues/42",
        }
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        result = service.create_feedback(
            title="Bug report",
            description="Something is broken",
            feedback_type="bug",
        )

        assert isinstance(result, FeedbackResult)
        assert result.url == "https://github.com/owner/repo/issues/42"

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/repos/owner/repo/issues" in call_args[0][0]
        assert call_args[1]["json"]["title"] == "Bug report"
        assert call_args[1]["json"]["body"] == "Something is broken"
        assert "Bearer ghp_test123" in call_args[1]["headers"]["Authorization"]

    @patch("apps.core.github_feedback.httpx.post")
    def test_label_mapping_bug(self, mock_post, configured_settings):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        service.create_feedback(title="t", description="d", feedback_type="bug")

        labels = mock_post.call_args[1]["json"]["labels"]
        assert labels == ["bug"]

    @patch("apps.core.github_feedback.httpx.post")
    def test_label_mapping_feature(self, mock_post, configured_settings):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        service.create_feedback(title="t", description="d", feedback_type="feature")

        labels = mock_post.call_args[1]["json"]["labels"]
        assert labels == ["enhancement"]

    @patch("apps.core.github_feedback.httpx.post")
    def test_label_mapping_general(self, mock_post, configured_settings):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        service.create_feedback(title="t", description="d", feedback_type="general")

        labels = mock_post.call_args[1]["json"]["labels"]
        assert labels == ["feedback"]

    def test_label_map_covers_all_types(self):
        assert LABEL_MAP["bug"] == "bug"
        assert LABEL_MAP["feature"] == "enhancement"
        assert LABEL_MAP["general"] == "feedback"

    def test_raises_when_not_configured(self, settings):
        settings.GITHUB_FEEDBACK_REPO = ""
        settings.GITHUB_FEEDBACK_TOKEN = ""
        service = GitHubFeedbackService()

        with pytest.raises(GitHubFeedbackError, match="not configured"):
            service.create_feedback(title="t", description="d", feedback_type="bug")

    @patch("apps.core.github_feedback.httpx.post")
    def test_screenshot_skipped_with_debug_log(self, mock_post, configured_settings, caplog):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        with caplog.at_level(logging.DEBUG, logger="apps.core.github_feedback"):
            service.create_feedback(
                title="Visual bug",
                description="desc",
                feedback_type="bug",
                screenshot="data:image/png;base64,abc123",
            )

        assert "Screenshot provided but not supported" in caplog.text
        # Only one API call (no upload)
        mock_post.assert_called_once()

    @patch("apps.core.github_feedback.httpx.post")
    def test_handles_401_error(self, mock_post, configured_settings):
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        with pytest.raises(GitHubFeedbackError, match="Invalid GitHub token"):
            service.create_feedback(title="t", description="d", feedback_type="bug")

    @patch("apps.core.github_feedback.httpx.post")
    def test_handles_404_error(self, mock_post, configured_settings):
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_post.return_value = mock_response

        service = GitHubFeedbackService()
        with pytest.raises(GitHubFeedbackError, match="not found"):
            service.create_feedback(title="t", description="d", feedback_type="bug")

    @patch("apps.core.github_feedback.httpx.post")
    def test_handles_timeout(self, mock_post, configured_settings):
        mock_post.side_effect = httpx.TimeoutException("timeout")

        service = GitHubFeedbackService()
        with pytest.raises(GitHubFeedbackError, match="timeout"):
            service.create_feedback(title="t", description="d", feedback_type="bug")


class TestFeedbackEnabledQuery:
    """Tests for feedback_enabled via get_feedback_service().is_configured()."""

    def test_enabled_with_todoist_configured(self, settings):
        settings.FEEDBACK_BACKEND = "todoist"
        settings.TODOIST_API_TOKEN = "test-token"
        settings.TODOIST_PROJECT_ID = "test-project"

        service = get_feedback_service()
        assert service.is_configured() is True

    def test_disabled_with_todoist_unconfigured(self, settings):
        settings.FEEDBACK_BACKEND = "todoist"
        settings.TODOIST_API_TOKEN = ""
        settings.TODOIST_PROJECT_ID = ""

        service = get_feedback_service()
        assert service.is_configured() is False

    def test_enabled_with_github_configured(self, settings):
        settings.FEEDBACK_BACKEND = "github"
        settings.GITHUB_FEEDBACK_REPO = "owner/repo"
        settings.GITHUB_FEEDBACK_TOKEN = "ghp_test123"

        service = get_feedback_service()
        assert service.is_configured() is True

    def test_disabled_with_github_unconfigured(self, settings):
        settings.FEEDBACK_BACKEND = "github"
        settings.GITHUB_FEEDBACK_REPO = ""
        settings.GITHUB_FEEDBACK_TOKEN = ""

        service = get_feedback_service()
        assert service.is_configured() is False


class TestSubmitFeedbackWithGitHub:
    """Tests for submit_feedback mutation using GitHub backend."""

    @pytest.fixture
    def configured_settings(self, settings):
        settings.FEEDBACK_BACKEND = "github"
        settings.GITHUB_FEEDBACK_REPO = "owner/repo"
        settings.GITHUB_FEEDBACK_TOKEN = "ghp_test123"
        return settings

    @pytest.fixture
    def mock_info(self):
        user = Mock()
        user.first_name = "Test"
        user.last_name = "User"
        user.email = "test@example.com"
        info = Mock()
        info.context = Mock()
        info.context.user = user
        return info

    @patch("apps.core.github_feedback.httpx.post")
    def test_submits_via_github(self, mock_post, configured_settings, mock_info):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/issues/42",
        }
        mock_post.return_value = mock_response

        mutation = FeedbackMutation()
        input_data = FeedbackInput(
            type=FeedbackType.BUG,
            title="Bug via GitHub",
            description="Something broke",
        )

        result = mutation.submit_feedback(mock_info, input_data)

        assert result.success is True
        assert result.task_url == "https://github.com/owner/repo/issues/42"
