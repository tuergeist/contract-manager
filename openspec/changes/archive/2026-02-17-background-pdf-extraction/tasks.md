## 1. Celery Configuration

- [x] 1.1 Add Celery to backend dependencies (pyproject.toml)
- [x] 1.2 Create Celery app configuration in `config/celery.py`
- [x] 1.3 Update Django settings with Celery/Redis broker configuration
- [x] 1.4 Add `__init__.py` import for Celery app in config module

## 2. Extraction Task

- [x] 2.1 Create `apps/invoices/tasks.py` with extraction task
- [x] 2.2 Configure task retry logic (1 retry, 10s delay, acks_late=True)
- [x] 2.3 Update extraction status to EXTRACTING when task starts
- [x] 2.4 Handle success: set status to EXTRACTED, save extracted data
- [x] 2.5 Handle failure: set status to EXTRACTION_FAILED, store error message

## 3. Upload Mutation Changes

- [x] 3.1 Modify `upload_invoice` mutation to trigger Celery task after save
- [x] 3.2 Modify `upload_invoices` (bulk) mutation to trigger tasks for each upload
- [x] 3.3 Return EXTRACTING status immediately instead of waiting for extraction
- [x] 3.4 Keep `extract_invoice` mutation for manual re-extraction

## 4. Docker Configuration

- [x] 4.1 Add Celery worker service to `docker-compose.prod.yml`
- [x] 4.2 Configure worker to use same image as backend with different entrypoint
- [x] 4.3 Add Celery worker to local `docker-compose.yml` for development

## 5. Frontend Polling

- [x] 5.1 Add polling logic to invoice list when items have EXTRACTING status
- [x] 5.2 Set polling interval to 2 seconds
- [x] 5.3 Stop polling when no items are in EXTRACTING status
- [x] 5.4 Update UI to show extraction progress indicator (already had spinner)

## 6. Testing & Verification

- [ ] 6.1 Test extraction task runs successfully in local Docker environment
- [ ] 6.2 Verify retry logic works on simulated failure
- [ ] 6.3 Test frontend polling updates UI correctly
- [ ] 6.4 Verify worker restart doesn't lose queued tasks
