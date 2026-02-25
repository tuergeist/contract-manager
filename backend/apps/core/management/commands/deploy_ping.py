"""Send a deploy notification to Todoist."""
import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.todoist import TodoistService, TodoistError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send a deploy ping to Todoist with the current version"

    def handle(self, *args, **options):
        # Read version from build-info.json
        build_info_path = Path("/app/build-info.json")
        if build_info_path.exists():
            info = json.loads(build_info_path.read_text())
            version = info.get("version", "unknown")
            build_date = info.get("buildDate", "")
        else:
            version = "dev"
            build_date = ""

        if version == "dev":
            self.stdout.write("Skipping deploy ping in dev mode")
            return

        title = f"Deployed contract-manager {version}"
        description = f"**Version:** {version}"
        if build_date:
            description += f"\n**Build date:** {build_date}"

        try:
            service = TodoistService()
            task = service.create_task(
                title=title,
                description=description,
                feedback_type="general",
                labels=["deploy"],
            )
            self.stdout.write(f"Deploy ping sent: {task.url}")
        except TodoistError as e:
            # Don't fail the deploy if Todoist is unreachable
            self.stderr.write(f"Deploy ping failed (non-fatal): {e}")
