## Context

The application currently stores all file uploads (contract attachments, customer attachments, invoice logos, reference PDFs) on the local filesystem under `MEDIA_ROOT`. This creates stateful containers and complicates horizontal scaling. Scaleway Object Storage (S3-compatible) will be used as the target storage backend.

**Current upload paths:**
- `uploads/{tenant_id}/contracts/{contract_id}/` - Contract attachments
- `uploads/{tenant_id}/customers/{customer_id}/` - Customer attachments
- `uploads/{tenant_id}/invoices/logos/` - Invoice template logos
- `uploads/{tenant_id}/invoices/references/` - Reference PDFs

**Models with FileField:**
- `ContractAttachment.file`
- `CustomerAttachment.file`
- `InvoiceTemplate.logo`
- `InvoiceReferencePDF.file`

## Goals / Non-Goals

**Goals:**
- Enable S3-compatible object storage via environment configuration
- Automatically migrate existing local files to object storage on startup
- Maintain backwards compatibility when object storage is not configured
- Track migration status to prevent duplicate uploads
- Preserve existing URL structure and file paths

**Non-Goals:**
- CDN integration (can be added later at Scaleway/infrastructure level)
- File versioning or soft delete in object storage
- Migrating temporary files (MT940 banking imports)
- Supporting multiple storage backends simultaneously after migration

## Decisions

### 1. Use django-storages with boto3
**Decision:** Use `django-storages[s3]` package which provides `S3Boto3Storage`.

**Rationale:** Well-maintained, widely used, handles S3 quirks. Direct boto3 would require reimplementing file handling logic.

**Alternatives considered:**
- Direct boto3: More control but significant boilerplate
- MinIO client: Less Django integration

### 2. Environment-based storage selection
**Decision:** Check for `S3_ENDPOINT_URL` env var to determine storage backend.

```python
if env("S3_ENDPOINT_URL", default=""):
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
```

**Rationale:** Simple feature flag via environment. No code changes needed to switch.

### 3. Migration via management command on startup
**Decision:** Create `migrate_to_object_storage` management command that:
1. Scans all FileField records in affected models
2. Checks if file exists locally but not in S3
3. Uploads to S3 preserving the same path
4. Records migrated files in a tracking table

**Rationale:** Management command can be run manually or via Docker entrypoint. Idempotent design allows safe re-runs.

### 4. Migration tracking table
**Decision:** Create `StorageMigration` model to track migrated files:

```python
class StorageMigration(models.Model):
    file_path = models.CharField(max_length=500, unique=True)
    migrated_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20)  # 'local'
    destination = models.CharField(max_length=20)  # 's3'
```

**Rationale:** Prevents re-uploading already migrated files. Provides audit trail.

### 5. Entrypoint integration
**Decision:** Add migration check to Docker entrypoint script:

```bash
if [ -n "$S3_ENDPOINT_URL" ]; then
    python manage.py migrate_to_object_storage --auto
fi
```

**Rationale:** Automatic migration on container start. `--auto` flag skips if no pending files.

## Risks / Trade-offs

**[Risk] Migration takes too long on startup** → Add `--async` flag to run migration in background thread. First startup may have brief period where old files serve from local.

**[Risk] S3 credentials misconfigured** → Validate S3 connection before switching storage backend. Fail loudly with clear error message.

**[Risk] File path mismatch between local and S3** → Use identical paths. S3 "folders" are just key prefixes, same structure works.

**[Risk] Existing file URLs break** → Django's `FileField.url` automatically uses the configured storage backend. URLs will point to S3 after migration.

**[Trade-off] Local files remain after migration** → Not automatically deleted. Can add `--cleanup` flag later for manual cleanup after verification.

## Migration Plan

1. **Preparation:**
   - Create Scaleway Object Storage bucket
   - Configure CORS if direct browser uploads needed (not currently)
   - Set env vars: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`

2. **Deployment:**
   - Deploy new image with django-storages
   - Migration runs automatically on startup
   - Monitor logs for migration progress

3. **Rollback:**
   - Remove S3 env vars to revert to local storage
   - Local files still exist (not deleted during migration)
   - No data loss scenario

## Open Questions

- Should we set a max batch size for migration to limit startup time?
- Do we need signed URLs for private files, or is bucket-level access sufficient?
