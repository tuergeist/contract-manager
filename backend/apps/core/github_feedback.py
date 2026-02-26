"""GitHub Issues feedback backend."""
import base64
import logging
import uuid
from typing import Optional

import httpx
from django.conf import settings

from apps.core.feedback import FeedbackResult, FeedbackService

logger = logging.getLogger(__name__)

# Map feedback types to GitHub issue labels
LABEL_MAP = {
    "bug": "bug",
    "feature": "enhancement",
    "general": "feedback",
}


class GitHubFeedbackError(Exception):
    """Raised when the GitHub API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubFeedbackService(FeedbackService):
    """Feedback via GitHub Issues."""

    API_URL = "https://api.github.com"
    TIMEOUT = 30

    def __init__(self):
        self.repo = getattr(settings, "GITHUB_FEEDBACK_REPO", "")
        self.token = getattr(settings, "GITHUB_FEEDBACK_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.repo and self.token)

    def create_feedback(
        self,
        *,
        title: str,
        description: str,
        feedback_type: str,
        screenshot: Optional[str] = None,
    ) -> FeedbackResult:
        if not self.is_configured():
            raise GitHubFeedbackError("GitHub feedback is not configured")

        body = description
        if screenshot:
            screenshot_url = self._upload_screenshot(screenshot)
            if screenshot_url:
                body += f"\n\n### Screenshot\n\n![Screenshot]({screenshot_url})"

        label = LABEL_MAP.get(feedback_type, "feedback")

        payload = {
            "title": title,
            "body": body,
            "labels": [label],
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"{self.API_URL}/repos/{self.repo}/issues"

        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.TIMEOUT,
            )
        except httpx.TimeoutException:
            raise GitHubFeedbackError("GitHub API timeout")
        except httpx.RequestError as e:
            raise GitHubFeedbackError(f"Failed to connect to GitHub: {e}")

        if response.status_code == 401:
            raise GitHubFeedbackError("Invalid GitHub token", 401)

        if response.status_code == 404:
            raise GitHubFeedbackError(
                f"Repository '{self.repo}' not found or token lacks issues:write permission",
                404,
            )

        if not response.is_success:
            raise GitHubFeedbackError(
                f"GitHub API error: {response.text}",
                response.status_code,
            )

        data = response.json()
        issue_url = data.get("html_url", "")

        logger.info("Created GitHub issue #%s in %s", data.get("number"), self.repo)

        return FeedbackResult(url=issue_url)

    def _upload_screenshot(self, screenshot: str) -> Optional[str]:
        """Upload screenshot to the repo and return the raw URL."""
        try:
            img_data = screenshot
            if "," in img_data:
                img_data = img_data.split(",", 1)[1]
            # Validate it's valid base64
            base64.b64decode(img_data)

            filename = f".feedback/screenshots/{uuid.uuid4().hex}.png"
            url = f"{self.API_URL}/repos/{self.repo}/contents/{filename}"

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            payload = {
                "message": f"Upload feedback screenshot",
                "content": img_data,
                "branch": "main",
            }

            response = httpx.put(
                url, json=payload, headers=headers, timeout=self.TIMEOUT
            )

            if not response.is_success:
                logger.warning("Failed to upload screenshot to GitHub: %s", response.text)
                return None

            data = response.json()
            return data.get("content", {}).get("download_url")
        except Exception as e:
            logger.warning("Failed to upload screenshot: %s", e)
            return None
