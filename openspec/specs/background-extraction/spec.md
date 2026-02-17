## Requirements

### Requirement: Automatic extraction trigger
The system SHALL automatically trigger PDF extraction as a background task immediately after a PDF file is successfully uploaded.

#### Scenario: PDF upload triggers extraction
- **WHEN** user uploads an invoice PDF via `uploadInvoice` or `uploadInvoices` mutation
- **THEN** the system saves the file and queues an extraction task
- **THEN** the mutation returns immediately with `extraction_status: EXTRACTING`

#### Scenario: CSV-imported invoice with PDF upload
- **WHEN** user uploads a PDF that matches an expected invoice from CSV import
- **THEN** the system updates the record and queues an extraction task
- **THEN** the extraction begins automatically without manual trigger

### Requirement: Extraction status tracking
The system SHALL track extraction status with the following states: PENDING, EXTRACTING, EXTRACTED, EXTRACTION_FAILED.

#### Scenario: Status transitions during extraction
- **WHEN** extraction task starts processing
- **THEN** status changes from PENDING to EXTRACTING

#### Scenario: Successful extraction
- **WHEN** extraction completes successfully
- **THEN** status changes to EXTRACTED
- **THEN** extracted data is saved to the invoice record

#### Scenario: Failed extraction
- **WHEN** extraction fails after all retry attempts
- **THEN** status changes to EXTRACTION_FAILED
- **THEN** error message is stored in `extraction_error` field

### Requirement: Extraction retry on failure
The system SHALL retry failed extractions once with a 10-second delay before marking as failed.

#### Scenario: Transient failure recovery
- **WHEN** extraction fails due to a transient error (API timeout, rate limit)
- **THEN** system waits 10 seconds and retries extraction once
- **THEN** if retry succeeds, status becomes EXTRACTED

#### Scenario: Persistent failure
- **WHEN** extraction fails on both initial attempt and retry
- **THEN** status becomes EXTRACTION_FAILED
- **THEN** user can manually trigger re-extraction via `extractInvoice` mutation

### Requirement: Frontend status polling
The frontend SHALL poll for extraction status updates while invoices are in EXTRACTING state.

#### Scenario: Polling during extraction
- **WHEN** user is viewing the invoices list with items in EXTRACTING status
- **THEN** frontend polls `invoices` query every 2 seconds
- **THEN** UI updates when status changes to EXTRACTED or EXTRACTION_FAILED

#### Scenario: Polling stops when complete
- **WHEN** all visible invoices have status EXTRACTED, EXTRACTION_FAILED, or CONFIRMED
- **THEN** frontend stops polling to reduce server load

### Requirement: Celery worker in production
The system SHALL run a Celery worker service in production to process extraction tasks.

#### Scenario: Worker processes queued tasks
- **WHEN** extraction tasks are queued in Redis
- **THEN** Celery worker picks up and processes tasks
- **THEN** multiple uploads can be extracted concurrently

#### Scenario: Worker restart recovery
- **WHEN** Celery worker crashes or restarts
- **THEN** incomplete tasks are re-queued and processed
- **THEN** no extraction tasks are lost
