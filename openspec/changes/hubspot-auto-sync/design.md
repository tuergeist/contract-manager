## Technical Approach

Use Celery Beat (already running for time-tracking refresh) with a single periodic task that iterates over all tenants with auto-sync enabled. Follows the same pattern as `refresh_all_time_tracking_data` in `apps/contracts/tasks.py`.

## Key Decisions

### Single periodic task vs per-tenant tasks
**Decision**: One Beat entry → one orchestrator task that loops over tenants, calling existing `HubSpotService` methods directly (not spawning sub-tasks).

**Rationale**: With a small number of tenants (< 50), sequential sync is simple and avoids task fan-out complexity. Each tenant sync takes ~5-10 seconds. If scale becomes an issue later, the orchestrator can dispatch per-tenant sub-tasks.

### Storage of auto-sync setting and results
**Decision**: Store in existing `Tenant.hubspot_config` JSON field — no migration needed.

New keys:
- `auto_sync_enabled` (bool, default false)
- `last_auto_sync_customers` (ISO timestamp)
- `last_auto_sync_products` (ISO timestamp)
- `last_auto_sync_deals` (ISO timestamp)

### Sync order and error isolation
Customers → products → deals (deals depend on both customers and products existing). Each sync type runs in its own try/except so a failure in one doesn't block the others.

## Implementation

### Backend

**New file: `backend/apps/customers/tasks.py`**

```python
@shared_task(acks_late=True)
def sync_all_hubspot_tenants():
    """Periodic task: sync HubSpot data for all tenants with auto-sync enabled."""
    tenants = Tenant.objects.filter(is_active=True)
    for tenant in tenants:
        config = tenant.hubspot_config or {}
        if not config.get("api_key") or not config.get("auto_sync_enabled"):
            continue
        _sync_tenant_hubspot(tenant)
```

Calls `HubSpotService(tenant).sync_companies()`, `.sync_products()`, `.sync_deals()` sequentially, storing timestamps after each.

**`backend/config/settings/base.py`** — add to `CELERY_BEAT_SCHEDULE`:
```python
"sync-hubspot-all-tenants": {
    "task": "apps.customers.tasks.sync_all_hubspot_tenants",
    "schedule": 21600,  # 6 hours
},
```

**`backend/apps/tenants/schema.py`** — expose `autoSyncEnabled` field in `HubSpotSettingsType` and add mutation to toggle it. Also expose `lastAutoSync*` timestamps.

### Frontend

**`frontend/src/features/settings/Settings.tsx`**:
- Add `autoSyncEnabled` and `lastAutoSync{Customers,Products,Deals}` to `HUBSPOT_SETTINGS_QUERY`
- Add toggle Switch in the HubSpot settings card (below the existing sync buttons)
- Add mutation `UPDATE_HUBSPOT_AUTO_SYNC` to toggle the setting
- Show last auto-sync timestamps next to each sync section

## Files to Modify

| File | Change |
|------|--------|
| `backend/apps/customers/tasks.py` | New file — `sync_all_hubspot_tenants` task |
| `backend/config/settings/base.py` | Add Beat schedule entry |
| `backend/apps/tenants/schema.py` | Expose `autoSyncEnabled` + toggle mutation, `lastAutoSync*` fields |
| `frontend/src/features/settings/Settings.tsx` | Auto-sync toggle + last auto-sync timestamps |
| `frontend/src/locales/de.json` | German translations for auto-sync UI |
| `frontend/src/locales/en.json` | English translations for auto-sync UI |
