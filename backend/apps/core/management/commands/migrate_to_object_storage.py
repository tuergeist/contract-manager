"""Management command to migrate local files to object storage."""
import logging
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from apps.contracts.models import ContractAttachment
from apps.core.models import StorageMigration
from apps.customers.models import CustomerAttachment
from apps.invoices.models import InvoiceTemplate, InvoiceTemplateReference

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate local files to S3-compatible object storage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto",
            action="store_true",
            help="Skip if no files need migration (for startup scripts)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without actually migrating",
        )

    def handle(self, *args, **options):
        auto_mode = options["auto"]
        dry_run = options["dry_run"]

        # Check if S3 is configured
        if not settings.AWS_S3_ENDPOINT_URL:
            if auto_mode:
                self.stdout.write("S3 not configured, skipping migration.")
                return
            self.stdout.write(
                self.style.ERROR("S3 is not configured. Set S3_ENDPOINT_URL to enable.")
            )
            return

        # Validate S3 connection
        if not self._validate_s3_connection():
            self.stdout.write(
                self.style.ERROR("Failed to connect to S3. Check credentials and endpoint.")
            )
            return

        # Collect all files to migrate
        files_to_migrate = self._discover_files()

        if not files_to_migrate:
            self.stdout.write(self.style.SUCCESS("No files need migration."))
            return

        if auto_mode and not files_to_migrate:
            return

        self.stdout.write(f"Found {len(files_to_migrate)} files to migrate.")

        if dry_run:
            for file_path in files_to_migrate:
                self.stdout.write(f"  Would migrate: {file_path}")
            return

        # Migrate files
        migrated = 0
        failed = 0

        for file_path in files_to_migrate:
            try:
                if self._migrate_file(file_path):
                    migrated += 1
                    self.stdout.write(f"  Migrated: {file_path}")
                else:
                    failed += 1
                    self.stdout.write(self.style.WARNING(f"  Skipped (not found): {file_path}"))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  Failed: {file_path} - {e}"))
                logger.exception(f"Failed to migrate {file_path}")

        self.stdout.write(
            self.style.SUCCESS(f"Migration complete: {migrated} migrated, {failed} failed/skipped")
        )

    def _validate_s3_connection(self) -> bool:
        """Test S3 connection by listing bucket contents."""
        try:
            # Try to check if we can access the storage
            default_storage.exists("__connection_test__")
            return True
        except Exception as e:
            logger.error(f"S3 connection validation failed: {e}")
            return False

    def _discover_files(self) -> list[str]:
        """Find all files that need migration."""
        files = []
        already_migrated = set(
            StorageMigration.objects.values_list("file_path", flat=True)
        )

        # Contract attachments
        for attachment in ContractAttachment.objects.exclude(file=""):
            if attachment.file.name and attachment.file.name not in already_migrated:
                files.append(attachment.file.name)

        # Customer attachments
        for attachment in CustomerAttachment.objects.exclude(file=""):
            if attachment.file.name and attachment.file.name not in already_migrated:
                files.append(attachment.file.name)

        # Invoice logos
        for template in InvoiceTemplate.objects.exclude(logo=""):
            if template.logo.name and template.logo.name not in already_migrated:
                files.append(template.logo.name)

        # Invoice reference PDFs
        for ref_pdf in InvoiceTemplateReference.objects.exclude(file=""):
            if ref_pdf.file.name and ref_pdf.file.name not in already_migrated:
                files.append(ref_pdf.file.name)

        return files

    def _migrate_file(self, file_path: str) -> bool:
        """Migrate a single file from local storage to S3."""
        local_path = Path(settings.MEDIA_ROOT) / file_path

        if not local_path.exists():
            return False

        # Read local file
        with open(local_path, "rb") as f:
            content = f.read()

        # Upload to S3
        default_storage.save(file_path, ContentFile(content))

        # Record migration
        StorageMigration.objects.create(
            file_path=file_path,
            source="local",
            destination="s3",
        )

        return True
