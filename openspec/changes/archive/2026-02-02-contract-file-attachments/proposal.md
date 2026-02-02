## Why

Contracts often have associated documents (PDFs, signed agreements, purchase orders, correspondence) that need to be stored alongside the contract record. Currently there's no way to attach files to contracts. Users need a way to upload, view, and manage these attachments with easy backup/restore and a clear migration path to S3 storage.

## What Changes

- Add ability to upload one or more files per contract
- Display attachments in a new "Attachments" tab on contract detail page
- Allow downloading and deleting attachments
- Store files on local disk (Docker host-mounted volume) for easy backup
- Design storage abstraction to allow future S3 migration without code changes

## Capabilities

### New Capabilities
- `contract-attachments`: File upload, storage, download, and deletion for contract attachments. Includes multi-tenant isolation, file validation, and storage abstraction for S3 migration.

### Modified Capabilities
None - this is additive functionality.

## Impact

- **Backend**: New `ContractAttachment` model, GraphQL mutations/queries, REST download endpoint
- **Frontend**: New Attachments tab in ContractDetail, upload UI component
- **Infrastructure**: New host-mounted volume (`./uploads`) in docker-compose.yml
- **Database**: New migration for ContractAttachment table
- **APIs**: New GraphQL operations (uploadContractAttachment, deleteContractAttachment)
