## ADDED Requirements

### Requirement: S3-compatible storage backend configuration
The system SHALL support S3-compatible object storage (Scaleway) as an alternative to local filesystem storage, configured via environment variables.

#### Scenario: Object storage enabled via environment
- **WHEN** `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `S3_BUCKET_NAME` environment variables are set
- **THEN** the system SHALL use S3-compatible storage for all file uploads

#### Scenario: Object storage disabled (default)
- **WHEN** `S3_ENDPOINT_URL` environment variable is not set or empty
- **THEN** the system SHALL use local filesystem storage (current behavior)

#### Scenario: Invalid S3 credentials
- **WHEN** S3 environment variables are set but credentials are invalid
- **THEN** the system SHALL fail startup with a clear error message indicating credential validation failure

### Requirement: Automatic migration of existing files
The system SHALL automatically migrate existing local files to object storage on application startup when object storage is configured.

#### Scenario: Migration on first startup with object storage
- **WHEN** object storage is configured AND local files exist that have not been migrated
- **THEN** the system SHALL upload all existing files to object storage preserving their path structure

#### Scenario: Migration is idempotent
- **WHEN** the migration process runs multiple times
- **THEN** files already migrated SHALL NOT be re-uploaded

#### Scenario: Migration tracking
- **WHEN** a file is successfully migrated to object storage
- **THEN** the system SHALL record the migration in a tracking table with file path, timestamp, and source/destination

#### Scenario: No local files to migrate
- **WHEN** object storage is configured AND no local files exist (fresh deployment)
- **THEN** the system SHALL complete startup without errors

### Requirement: File uploads use configured storage
The system SHALL route all new file uploads through the configured storage backend.

#### Scenario: Upload with object storage enabled
- **WHEN** a user uploads a file AND object storage is configured
- **THEN** the file SHALL be stored directly in object storage

#### Scenario: Upload with local storage (default)
- **WHEN** a user uploads a file AND object storage is not configured
- **THEN** the file SHALL be stored on local filesystem (current behavior)

### Requirement: File retrieval uses configured storage
The system SHALL serve files from the configured storage backend.

#### Scenario: Retrieve file from object storage
- **WHEN** a user requests a file AND object storage is configured
- **THEN** the system SHALL return the file URL pointing to object storage

#### Scenario: Retrieve file from local storage
- **WHEN** a user requests a file AND object storage is not configured
- **THEN** the system SHALL serve the file from local filesystem

### Requirement: Preserve file path structure
The system SHALL maintain identical file path structure between local and object storage.

#### Scenario: Path preservation during migration
- **WHEN** a local file at `uploads/{tenant_id}/contracts/{contract_id}/file.pdf` is migrated
- **THEN** the object storage key SHALL be `uploads/{tenant_id}/contracts/{contract_id}/file.pdf`

#### Scenario: Path preservation for new uploads
- **WHEN** a new file is uploaded with object storage enabled
- **THEN** the object storage key SHALL follow the same path pattern as local storage would use
