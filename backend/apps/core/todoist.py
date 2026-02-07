"""Todoist integration service for feedback submission."""
import logging
import base64
from dataclasses import dataclass
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class TodoistError(Exception):
    """Base exception for Todoist API errors."""
    pass


class TodoistNotConfiguredError(TodoistError):
    """Raised when Todoist credentials are not configured."""
    pass


class TodoistAPIError(TodoistError):
    """Raised when Todoist API returns an error."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class TodoistTask:
    """Represents a created Todoist task."""
    id: str
    url: str


class TodoistService:
    """Service for interacting with Todoist API."""

    BASE_URL = "https://api.todoist.com/rest/v2"
    SYNC_URL = "https://api.todoist.com/sync/v9"
    TIMEOUT = 30  # seconds

    # Label mapping for feedback types
    FEEDBACK_LABELS = {
        "bug": "bug",
        "feature": "feature-request",
        "general": "feedback",
    }

    def __init__(self):
        self.api_token = getattr(settings, "TODOIST_API_TOKEN", "")
        self.project_id = getattr(settings, "TODOIST_PROJECT_ID", "")

    def _check_configured(self) -> None:
        """Check if Todoist is properly configured."""
        if not self.api_token:
            raise TodoistNotConfiguredError("TODOIST_API_TOKEN is not configured")
        if not self.project_id:
            raise TodoistNotConfiguredError("TODOIST_PROJECT_ID is not configured")

    def _get_headers(self) -> dict:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response, operation: str) -> dict:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 401:
            logger.error(f"Todoist API authentication failed for {operation}")
            raise TodoistAPIError("Invalid Todoist API token", response.status_code)

        if response.status_code == 429:
            logger.warning(f"Todoist API rate limited for {operation}")
            raise TodoistAPIError("Todoist API rate limit exceeded. Please try again later.", response.status_code)

        if not response.is_success:
            logger.error(f"Todoist API error for {operation}: {response.status_code} - {response.text}")
            raise TodoistAPIError(f"Todoist API error: {response.text}", response.status_code)

        return response.json() if response.text else {}

    def create_task(
        self,
        title: str,
        description: str,
        feedback_type: str = "general",
        labels: Optional[list[str]] = None,
    ) -> TodoistTask:
        """Create a new task in Todoist.

        Args:
            title: Task title
            description: Task description (supports markdown)
            feedback_type: Type of feedback (bug, feature, general)
            labels: Additional labels to add

        Returns:
            TodoistTask with id and url
        """
        self._check_configured()

        # Build labels list
        task_labels = []
        if feedback_type in self.FEEDBACK_LABELS:
            task_labels.append(self.FEEDBACK_LABELS[feedback_type])
        if labels:
            task_labels.extend(labels)

        payload = {
            "content": title,
            "description": description,
            "project_id": self.project_id,
            "labels": task_labels,
        }

        logger.info(f"Creating Todoist task: {title[:50]}...")

        try:
            response = httpx.post(
                f"{self.BASE_URL}/tasks",
                json=payload,
                headers=self._get_headers(),
                timeout=self.TIMEOUT,
            )
        except httpx.TimeoutException:
            logger.error("Todoist API timeout while creating task")
            raise TodoistAPIError("Todoist API timeout. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Todoist API request failed: {e}")
            raise TodoistAPIError(f"Failed to connect to Todoist: {e}")

        data = self._handle_response(response, "create_task")

        task_id = data.get("id")
        task_url = data.get("url", f"https://todoist.com/showTask?id={task_id}")

        logger.info(f"Created Todoist task {task_id}")

        return TodoistTask(id=str(task_id), url=task_url)

    def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload a file to Todoist and return the file URL.

        Args:
            file_data: Raw file bytes
            filename: Name for the uploaded file

        Returns:
            URL of the uploaded file
        """
        self._check_configured()

        logger.info(f"Uploading file to Todoist: {filename} ({len(file_data)} bytes)")

        try:
            response = httpx.post(
                f"{self.SYNC_URL}/uploads/add",
                headers={"Authorization": f"Bearer {self.api_token}"},
                files={"file": (filename, file_data)},
                timeout=self.TIMEOUT,
            )
        except httpx.TimeoutException:
            logger.error("Todoist API timeout while uploading file")
            raise TodoistAPIError("Todoist API timeout during file upload. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Todoist API file upload failed: {e}")
            raise TodoistAPIError(f"Failed to upload file to Todoist: {e}")

        data = self._handle_response(response, "upload_file")

        file_url = data.get("file_url")
        if not file_url:
            raise TodoistAPIError("Todoist did not return file URL")

        logger.info(f"Uploaded file to Todoist: {file_url}")

        return file_url

    def add_comment_with_attachment(
        self,
        task_id: str,
        comment: str,
        file_url: str,
    ) -> None:
        """Add a comment with an attachment to a task.

        Args:
            task_id: ID of the task
            comment: Comment text
            file_url: URL of previously uploaded file
        """
        self._check_configured()

        payload = {
            "task_id": task_id,
            "content": comment,
            "attachment": {
                "file_url": file_url,
                "file_type": "image/png",
                "resource_type": "file",
            },
        }

        logger.info(f"Adding comment with attachment to task {task_id}")

        try:
            response = httpx.post(
                f"{self.BASE_URL}/comments",
                json=payload,
                headers=self._get_headers(),
                timeout=self.TIMEOUT,
            )
        except httpx.TimeoutException:
            logger.error("Todoist API timeout while adding comment")
            raise TodoistAPIError("Todoist API timeout. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Todoist API comment failed: {e}")
            raise TodoistAPIError(f"Failed to add comment to Todoist: {e}")

        self._handle_response(response, "add_comment")

        logger.info(f"Added comment to task {task_id}")

    def upload_screenshot_to_task(
        self,
        task_id: str,
        screenshot_base64: str,
        filename: str = "screenshot.png",
    ) -> None:
        """Upload a screenshot and attach it as a comment to a task.

        Args:
            task_id: ID of the task
            screenshot_base64: Base64-encoded screenshot data
            filename: Name for the screenshot file
        """
        # Decode base64 screenshot
        try:
            # Handle data URL format (data:image/png;base64,...)
            if "," in screenshot_base64:
                screenshot_base64 = screenshot_base64.split(",", 1)[1]
            screenshot_data = base64.b64decode(screenshot_base64)
        except Exception as e:
            logger.error(f"Failed to decode screenshot: {e}")
            raise TodoistAPIError(f"Invalid screenshot data: {e}")

        # Upload file
        file_url = self.upload_file(screenshot_data, filename)

        # Add as comment
        self.add_comment_with_attachment(
            task_id=task_id,
            comment="Screenshot attached",
            file_url=file_url,
        )
