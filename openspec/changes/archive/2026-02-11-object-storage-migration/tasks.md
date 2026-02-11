## 1. Dependencies & Configuration

- [x] 1.1 Add `django-storages[s3]` and `boto3` to backend dependencies
- [x] 1.2 Add S3 environment variables to settings (S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME, S3_REGION)
- [x] 1.3 Configure DEFAULT_FILE_STORAGE based on S3_ENDPOINT_URL presence
- [x] 1.4 Add S3Boto3Storage settings (endpoint_url, access_key, secret_key, bucket_name, region, addressing_style)

## 2. Migration Tracking Model

- [x] 2.1 Create StorageMigration model with file_path, migrated_at, source, destination fields
- [x] 2.2 Generate and run migration for StorageMigration model

## 3. Migration Management Command

- [x] 3.1 Create `migrate_to_object_storage` management command
- [x] 3.2 Implement file discovery (scan FileField records in ContractAttachment, CustomerAttachment, InvoiceTemplate, InvoiceReferencePDF)
- [x] 3.3 Implement migration logic (check local exists, upload to S3, record in tracking table)
- [x] 3.4 Add `--auto` flag to skip if no pending files
- [x] 3.5 Add progress logging during migration

## 4. Startup Integration

- [x] 4.1 Update Docker entrypoint to run migration command when S3_ENDPOINT_URL is set
- [x] 4.2 Add S3 connection validation before running migration

## 5. Testing

- [x] 5.1 Add unit tests for storage backend selection logic
- [x] 5.2 Add unit tests for migration command (mock S3)
- [x] 5.3 Add integration test for file upload with S3 storage configured
- [x] 5.4 Test migration idempotency (running twice doesn't duplicate)

## 6. Documentation & Deployment

- [x] 6.1 Document required environment variables in README or deployment docs
- [x] 6.2 Add example S3 configuration for Scaleway to docker-compose.prod.yml comments
