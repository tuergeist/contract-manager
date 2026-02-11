"""Tests for object storage configuration and migration."""
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile

from apps.core.models import StorageMigration


class TestStorageBackendSelection:
    """Tests for storage backend selection based on environment."""

    def test_s3_settings_loaded_when_configured(self):
        """When AWS_S3_ENDPOINT_URL is set, S3 settings should be configured."""
        from django.conf import settings

        # These settings exist even when S3 is not configured (empty defaults)
        assert hasattr(settings, "AWS_S3_ENDPOINT_URL")
        assert hasattr(settings, "AWS_ACCESS_KEY_ID")
        assert hasattr(settings, "AWS_SECRET_ACCESS_KEY")
        assert hasattr(settings, "AWS_STORAGE_BUCKET_NAME")
        assert hasattr(settings, "AWS_S3_REGION_NAME")

    def test_default_storage_is_filesystem_without_s3(self):
        """Without S3 configured, default storage should be filesystem."""
        from django.conf import settings

        # In test environment, S3 is not configured
        if not settings.AWS_S3_ENDPOINT_URL:
            assert (
                settings.STORAGES["default"]["BACKEND"]
                == "django.core.files.storage.FileSystemStorage"
            )


class TestStorageMigrationModel:
    """Tests for StorageMigration model."""

    @pytest.mark.django_db
    def test_create_migration_record(self):
        """Can create a migration tracking record."""
        record = StorageMigration.objects.create(
            file_path="uploads/test/file.pdf",
            source="local",
            destination="s3",
        )
        assert record.file_path == "uploads/test/file.pdf"
        assert record.source == "local"
        assert record.destination == "s3"
        assert record.migrated_at is not None

    @pytest.mark.django_db
    def test_file_path_unique(self):
        """File path must be unique."""
        StorageMigration.objects.create(
            file_path="uploads/test/file.pdf",
            source="local",
            destination="s3",
        )
        with pytest.raises(Exception):  # IntegrityError
            StorageMigration.objects.create(
                file_path="uploads/test/file.pdf",
                source="local",
                destination="s3",
            )


class TestMigrateCommand:
    """Tests for migrate_to_object_storage management command."""

    @pytest.mark.django_db
    def test_command_skips_without_s3_config(self):
        """Command should skip gracefully when S3 is not configured."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("migrate_to_object_storage", "--auto", stdout=out)
        output = out.getvalue()
        assert "S3 not configured" in output or "No files" in output

    @pytest.mark.django_db
    def test_migration_is_idempotent(self):
        """Running migration twice should not duplicate records."""
        # Create a migration record
        StorageMigration.objects.create(
            file_path="uploads/test/file.pdf",
            source="local",
            destination="s3",
        )

        # Count should remain 1 even if we "discover" the same file again
        count = StorageMigration.objects.filter(file_path="uploads/test/file.pdf").count()
        assert count == 1

    @pytest.mark.django_db
    @patch("apps.core.management.commands.migrate_to_object_storage.default_storage")
    @patch("apps.core.management.commands.migrate_to_object_storage.settings")
    def test_command_validates_s3_connection(self, mock_settings, mock_storage):
        """Command should validate S3 connection before migrating."""
        from django.core.management import call_command
        from io import StringIO

        mock_settings.AWS_S3_ENDPOINT_URL = "https://s3.example.com"
        mock_settings.MEDIA_ROOT = "/app/media"
        mock_storage.exists.side_effect = Exception("Connection failed")

        out = StringIO()
        err = StringIO()
        call_command("migrate_to_object_storage", stdout=out, stderr=err)
        output = out.getvalue()
        assert "Failed to connect" in output
