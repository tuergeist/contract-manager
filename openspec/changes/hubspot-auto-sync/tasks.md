## Tasks

### 1. Backend: Celery task

- [x] 1.1 Create `backend/apps/customers/tasks.py` with `sync_all_hubspot_tenants` task — iterate active tenants, skip those without `api_key` or `auto_sync_enabled`, call `sync_companies()` → `sync_products()` → `sync_deals()` sequentially, store `last_auto_sync_*` timestamps in `hubspot_config`
- [x] 1.2 Add `sync-hubspot-all-tenants` entry to `CELERY_BEAT_SCHEDULE` in `config/settings/base.py` with 21600s (6h) interval

### 2. Backend: GraphQL schema

- [x] 2.1 Add `auto_sync_enabled`, `last_auto_sync_customers`, `last_auto_sync_products`, `last_auto_sync_deals` fields to `HubSpotSettingsType` in `tenants/schema.py`
- [x] 2.2 Add `set_hubspot_auto_sync(enabled: bool)` mutation in `tenants/schema.py` that toggles `hubspot_config.auto_sync_enabled`

### 3. Frontend: Settings UI

- [x] 3.1 Update `HUBSPOT_SETTINGS_QUERY` in `Settings.tsx` to fetch `autoSyncEnabled`, `lastAutoSyncCustomers`, `lastAutoSyncProducts`, `lastAutoSyncDeals`
- [x] 3.2 Add `SET_HUBSPOT_AUTO_SYNC` mutation
- [x] 3.3 Add auto-sync toggle Switch in the HubSpot settings card (visible only when API key is configured), with label "Automatic sync every 6 hours"
- [x] 3.4 Show last auto-sync timestamps next to each sync section when available

### 4. Translations

- [x] 4.1 Add German and English translations for auto-sync toggle label, tooltip, and timestamp labels

### 5. Verification

- [x] 5.1 Run `make test-back` — all tests pass
- [x] 5.2 Run `npx tsc --noEmit` — no type errors
