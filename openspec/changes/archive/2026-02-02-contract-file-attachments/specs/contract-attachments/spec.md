## ADDED Requirements

### Requirement: Upload file attachment to contract
The system SHALL allow authenticated users to upload files to contracts within their tenant. Files SHALL be stored with a path structure that enables per-tenant backup and S3 migration.

#### Scenario: Successful file upload
- **WHEN** user uploads a valid PDF file to a contract
- **THEN** system stores the file at `uploads/{tenant_id}/contracts/{contract_id}/{uuid}_{filename}`
- **THEN** system creates a ContractAttachment record with original filename, file size, and content type
- **THEN** system returns the attachment details including download URL

#### Scenario: File type not allowed
- **WHEN** user attempts to upload a file with disallowed extension (e.g., .exe)
- **THEN** system rejects the upload with error "File type not allowed"
- **THEN** no file is stored

#### Scenario: File too large
- **WHEN** user attempts to upload a file exceeding 10MB
- **THEN** system rejects the upload with error indicating maximum size
- **THEN** no file is stored

### Requirement: Download file attachment
The system SHALL allow authenticated users to download attachments from contracts within their tenant.

#### Scenario: Successful download
- **WHEN** user requests download of an attachment they have access to
- **THEN** system streams the file with correct content-type header
- **THEN** system sets Content-Disposition header with original filename

#### Scenario: Attachment not found or unauthorized
- **WHEN** user requests download of non-existent attachment or attachment from another tenant
- **THEN** system returns 404 error
- **THEN** no file content is exposed

### Requirement: Delete file attachment
The system SHALL allow authenticated users to delete attachments from contracts within their tenant.

#### Scenario: Successful deletion
- **WHEN** user deletes an attachment
- **THEN** system removes the file from storage
- **THEN** system deletes the ContractAttachment record
- **THEN** system returns success confirmation

#### Scenario: Delete non-existent or unauthorized attachment
- **WHEN** user attempts to delete attachment from another tenant or non-existent attachment
- **THEN** system returns error "Attachment not found"
- **THEN** no data is modified

### Requirement: List contract attachments
The system SHALL display all attachments for a contract to authenticated users within the same tenant.

#### Scenario: View attachments on contract detail
- **WHEN** user views a contract detail page
- **THEN** system displays an Attachments tab
- **THEN** tab shows list of attachments with filename, size, upload date, and uploader
- **THEN** each attachment has download and delete actions

#### Scenario: Contract has no attachments
- **WHEN** user views attachments tab for contract with no files
- **THEN** system displays empty state message "No attachments"

### Requirement: Multi-tenant isolation
The system SHALL enforce strict tenant isolation for all attachment operations.

#### Scenario: Cross-tenant access prevented
- **WHEN** user attempts to access attachment belonging to different tenant
- **THEN** system treats it as "not found"
- **THEN** no information about the attachment is leaked

### Requirement: Storage abstraction for S3 migration
The system SHALL use Django's storage abstraction so files can be migrated to S3 by changing configuration only.

#### Scenario: S3 migration path
- **WHEN** administrator syncs files to S3 and changes DEFAULT_FILE_STORAGE setting
- **THEN** system serves existing files from S3 using same relative paths
- **THEN** new uploads go to S3
- **THEN** no code changes are required

### Requirement: File validation
The system SHALL validate files before storage.

#### Scenario: Allowed file types
- **WHEN** user uploads file with extension .pdf, .doc, .docx, .xls, .xlsx, .csv, .txt, .png, .jpg, .jpeg, .gif, .zip
- **THEN** system accepts the file

#### Scenario: Invalid base64 content
- **WHEN** upload contains malformed base64 data
- **THEN** system returns error "Invalid file content"
- **THEN** no file is stored
