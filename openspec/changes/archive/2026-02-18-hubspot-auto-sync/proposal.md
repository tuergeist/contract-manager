## Why

HubSpot sync (customers, products, deals) currently requires a user to manually click "Sync now" in Settings. This means data drifts until someone remembers to sync. Automatic background sync every 6 hours keeps the system current without manual intervention.

## What Changes

- Add a Celery Beat periodic task that runs HubSpot sync (customers → products → deals) every 6 hours for all tenants with HubSpot enabled
- Add an "Auto-sync" toggle in the HubSpot settings UI so tenants can opt in/out
- Store last auto-sync timestamp and result per sync type
- Manual "Sync now" buttons remain unchanged and work independently
- Log sync results (created/skipped/errors) for observability

## Capabilities

### New Capabilities
- `hubspot-auto-sync`: Periodic background sync of HubSpot data (customers, products, deals) via Celery Beat, with per-tenant opt-in setting

### Modified Capabilities
_(none — existing manual sync mutations and UI are unchanged)_

## Impact

- **Backend**: New Celery task in `apps/customers/tasks.py`, new field in `Tenant.hubspot_config` JSON for auto-sync toggle, addition to `CELERY_BEAT_SCHEDULE`
- **Frontend**: Small addition to Settings HubSpot section — auto-sync toggle + last auto-sync timestamp display
- **Infrastructure**: Celery Beat must be running (already required for `refresh-time-tracking-data`)
- **Dependencies**: None new — uses existing Celery, Redis, HubSpotService
