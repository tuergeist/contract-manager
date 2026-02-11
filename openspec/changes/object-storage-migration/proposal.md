## Why

Local file storage limits scalability and makes container deployments stateful. Moving to object storage (Scaleway S3-compatible) enables stateless containers, better reliability, and easier backups. Files currently stored locally include contract attachments, customer attachments, invoice logos, and reference PDFs.

## What Changes

- Add optional S3-compatible object storage backend (Scaleway) configured via environment variables
- Automatic migration of existing local files to object storage on application startup
- Once migrated, all new uploads go directly to object storage
- Local storage remains the default when object storage is not configured
- MT940 banking imports remain as temporary uploads (not stored)

## Capabilities

### New Capabilities
- `object-storage`: S3-compatible storage backend with automatic migration from local filesystem

### Modified Capabilities
<!-- None - this is a transparent storage backend change, not a requirement change -->

## Impact

- **Backend settings**: New env vars for S3 endpoint, bucket, access key, secret key
- **Django storage**: Custom storage backend that checks migration status
- **Startup**: Migration command runs automatically, tracks migrated files
- **Models affected**: ContractAttachment, CustomerAttachment, InvoiceTemplate (logo), InvoiceReferencePDF
- **Dependencies**: `boto3` or `django-storages` package
- **Deployment**: Object storage bucket must be provisioned before enabling
