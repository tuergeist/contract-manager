"""Abstract feedback service with provider implementations."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class FeedbackResult:
    """Result from creating feedback."""

    url: str


class FeedbackService(ABC):
    """Abstract base class for feedback backends."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this backend has all required configuration."""
        ...

    @abstractmethod
    def create_feedback(
        self,
        *,
        title: str,
        description: str,
        feedback_type: str,
        screenshot: Optional[str] = None,
    ) -> FeedbackResult:
        """Create a feedback item and return the result URL.

        Args:
            title: Feedback title
            description: Pre-formatted markdown description with metadata
            feedback_type: One of "bug", "feature", "general"
            screenshot: Optional base64-encoded screenshot
        """
        ...


class TodoistFeedbackService(FeedbackService):
    """Feedback via Todoist tasks."""

    def is_configured(self) -> bool:
        return bool(
            getattr(settings, "TODOIST_API_TOKEN", "")
            and getattr(settings, "TODOIST_PROJECT_ID", "")
        )

    def create_feedback(
        self,
        *,
        title: str,
        description: str,
        feedback_type: str,
        screenshot: Optional[str] = None,
    ) -> FeedbackResult:
        from apps.core.todoist import TodoistService

        service = TodoistService()
        task = service.create_task(
            title=title,
            description=description,
            feedback_type=feedback_type,
        )

        if screenshot:
            try:
                service.upload_screenshot_to_task(
                    task_id=task.id,
                    screenshot_base64=screenshot,
                    filename=f"screenshot-{task.id}.png",
                )
            except Exception as e:
                logger.warning("Failed to upload screenshot to Todoist: %s", e)

        return FeedbackResult(url=task.url)


def get_feedback_service() -> FeedbackService:
    """Return the configured feedback service based on FEEDBACK_BACKEND setting."""
    backend = getattr(settings, "FEEDBACK_BACKEND", "todoist").lower()
    if backend == "github":
        from apps.core.github_feedback import GitHubFeedbackService
        return GitHubFeedbackService()
    return TodoistFeedbackService()
