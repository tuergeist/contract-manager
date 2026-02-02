## Context

The contract manager application needs to store files associated with contracts. Users want to attach documents like signed PDFs, purchase orders, and correspondence. The solution must support easy backup of files and allow migration to S3 storage later without code changes.

Current state:
- No file storage exists in the application
- Django settings have `MEDIA_ROOT` configured but unused
- Existing file upload pattern in contract import uses base64 encoding over GraphQL

## Goals / Non-Goals

**Goals:**
- Upload, download, and delete files attached to contracts
- Multi-tenant isolation (each tenant can only access their own files)
- Store files in a host-mounted directory for easy backup (`./uploads`)
- Enable S3 migration by changing only Django settings (no code changes)
- Validate file types and sizes before storage

**Non-Goals:**
- Image thumbnails or previews (out of scope)
- Full-text search within attachments
- Version history for attachments
- Drag-and-drop upload (can be added later)
- S3 implementation (only prepare the migration path)

## Decisions

### 1. Storage Backend: Django FileSystemStorage with host mount

**Decision**: Use Django's default `FileSystemStorage` with files stored in `./uploads` mounted into the container.

**Alternatives considered**:
- Named Docker volume: Harder to backup (requires `docker cp` or volume backup tools)
- Database BLOB storage: Poor performance, complicates backups

**Rationale**: Host-mounted directory allows simple `rsync` or `tar` backup. Path structure `uploads/{tenant_id}/contracts/{contract_id}/{uuid}_{filename}` enables per-tenant backup and S3 sync.

### 2. Upload Method: Base64 over GraphQL

**Decision**: Send files as base64-encoded strings in GraphQL mutations (existing pattern).

**Alternatives considered**:
- Multipart form upload: Requires separate REST endpoint, different auth handling
- Presigned URLs: Adds complexity, better suited for large files

**Rationale**: Matches existing `upload_contract_import` pattern. Simple, works with Apollo Client, keeps auth consistent. 10MB limit is reasonable for contract documents.

### 3. Download Method: Authenticated REST endpoint

**Decision**: Create `/api/attachments/{id}/download/` REST endpoint that verifies auth and tenant ownership.

**Alternatives considered**:
- Return base64 in GraphQL query: Memory-intensive for large files
- Signed URLs: Good for S3, overkill for local storage

**Rationale**: REST endpoint with `FileResponse` streams files efficiently. Can be swapped for S3 signed URLs later with minimal changes.

### 4. File Path Structure

**Decision**: `uploads/{tenant_id}/contracts/{contract_id}/{uuid}_{original_extension}`

**Rationale**:
- Tenant ID first enables per-tenant backup/restore
- UUID prefix prevents filename collisions
- Preserves extension for content-type hints
- Easy to sync to S3 with same structure

## Risks / Trade-offs

**[Risk] Large file uploads may timeout** → Set 10MB limit. For larger files, would need chunked upload (future enhancement).

**[Risk] Disk space exhaustion** → Monitor disk usage. S3 migration eliminates this concern.

**[Risk] File deletion leaves orphans if model delete fails** → Delete file in model's `delete()` method within same operation.

**[Trade-off] Base64 encoding increases payload size ~33%** → Acceptable for documents under 10MB. Keeps implementation simple.

**[Trade-off] No virus scanning** → Out of scope. Enterprise deployments could add scanning proxy.

## Migration Path to S3

When ready to migrate:

```bash
# 1. Sync files to S3 (preserving path structure)
aws s3 sync ./uploads s3://bucket/uploads

# 2. Update Django settings
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'bucket'
# ... other AWS settings

# 3. Deploy - Django uses same relative paths, now served from S3
```

No database changes needed. The `file` field stores relative paths that work with any storage backend.
