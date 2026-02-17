## Why

PDF extraction currently blocks the upload request, causing slow response times and potential timeouts when the Anthropic API is slow or processing large files. Moving extraction to a background process improves UX and reliability.

## What Changes

- Add Celery worker to production Docker Compose
- Trigger extraction task automatically after PDF upload
- Add extraction status polling for real-time UI updates
- Implement retry logic (1 retry on failure, then mark as failed)
- Frontend shows extraction progress with status updates

## Capabilities

### New Capabilities
- `background-extraction`: Celery-based background task system for PDF extraction with automatic triggering, retry logic, and status tracking

### Modified Capabilities
<!-- None - this is an implementation change, not a spec-level requirement change -->

## Impact

- **Backend**: New Celery configuration, task definitions, Redis as broker (already in compose)
- **Docker**: Add celery worker service to docker-compose.prod.yml
- **Frontend**: Add polling mechanism for extraction status updates
- **API**: Extraction mutations return immediately, status checked via query
