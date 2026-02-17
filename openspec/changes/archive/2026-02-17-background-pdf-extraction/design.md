## Context

Currently, when a user uploads an invoice PDF, extraction happens synchronously in the request. The Anthropic API call can take 5-30 seconds depending on PDF complexity, causing:
- Poor UX (user waits with no feedback)
- Potential request timeouts (especially with large PDFs)
- No retry capability on transient failures

Redis is already configured in docker-compose.prod.yml as a service, making Celery a natural fit.

## Goals / Non-Goals

**Goals:**
- Extraction happens in background immediately after upload
- User sees real-time status updates (pending → extracting → extracted/failed)
- Failed extractions retry once automatically
- No changes to extraction logic itself, only where it runs

**Non-Goals:**
- WebSocket-based real-time updates (polling is sufficient for this use case)
- Batch processing or scheduled extraction
- Changes to the extraction algorithm or AI prompts

## Decisions

### 1. Use Celery with Redis broker
**Choice:** Celery with Redis as message broker
**Alternatives considered:**
- Django-Q2: Simpler but less mature, fewer monitoring tools
- Python threading: No persistence, harder to scale
- AWS Lambda/Cloud Functions: Adds complexity, vendor lock-in

**Rationale:** Celery is battle-tested, Redis is already available, and it provides retry logic, monitoring (Flower), and scales horizontally.

### 2. Auto-trigger on upload
**Choice:** Trigger Celery task immediately in upload mutation after saving file
**Alternatives considered:**
- Manual trigger via separate mutation: Extra step for users
- Periodic task that checks for pending: Adds latency

**Rationale:** Immediate trigger provides best UX - user uploads and extraction starts instantly.

### 3. Frontend polling for status
**Choice:** Poll `importedInvoices` query every 2 seconds while extraction is pending
**Alternatives considered:**
- WebSockets/SSE: More complex infrastructure for minimal benefit
- Long polling: Similar complexity to WebSockets

**Rationale:** Extraction typically completes in 5-30 seconds. Polling every 2s means max 15 extra queries - acceptable trade-off for simplicity.

### 4. Retry configuration
**Choice:** 1 automatic retry with 10-second delay, then mark as failed
**Alternatives considered:**
- No retries: Transient API errors would require manual re-extraction
- Multiple retries with backoff: Over-engineered for this use case

**Rationale:** Single retry catches transient failures without masking persistent issues.

## Risks / Trade-offs

**[Risk] Celery worker crashes mid-extraction** → Task will be retried on worker restart (Celery default behavior with acks_late=True)

**[Risk] Redis unavailable** → Uploads still succeed, extraction status stays "pending". Worker processes backlog when Redis recovers.

**[Risk] Memory usage with large PDFs** → Extraction already loads PDF into memory; no change in peak usage, just happens in worker process instead of web process.

**[Trade-off] Polling vs real-time** → Polling adds ~15 requests per extraction but avoids WebSocket infrastructure complexity.

## Migration Plan

1. Add Celery configuration to Django settings
2. Create extraction task in `apps/invoices/tasks.py`
3. Modify upload mutations to trigger task instead of calling extraction directly
4. Add Celery worker service to docker-compose.prod.yml
5. Deploy: Pull new images, start celery worker, restart backend
6. Rollback: Remove celery service, revert to sync extraction (mutations still work)

## Open Questions

- Should we add Flower (Celery monitoring) to production? (Nice to have, not required)
- Timeout for extraction task? (Suggest 120 seconds to handle slow API responses)
