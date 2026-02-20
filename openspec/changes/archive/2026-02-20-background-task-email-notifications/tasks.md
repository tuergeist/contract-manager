## 1. Backend notification event types & email builders

- [x] 1.1 Add `_build_hubspot_sync_completed_email(**kwargs)` builder in `apps/core/notifications.py` — accepts `results` dict (customers, products, deals dicts with created/updated/skipped counts) and `errors` dict (sync_type → error message), returns subject and HTML body
- [x] 1.2 Add `_build_time_tracking_sync_completed_email(**kwargs)` builder in `apps/core/notifications.py` — accepts `synced` count, `total` count, `failed` count, returns subject and HTML body
- [x] 1.3 Register `hubspot_sync_completed` and `time_tracking_sync_completed` in `NOTIFICATION_TYPES` registry

## 2. Backend HubSpot sync task notification

- [x] 2.1 Modify `_sync_tenant_hubspot()` in `apps/customers/tasks.py` to collect results and errors from each sync type into dicts instead of only logging them
- [x] 2.2 After all syncs complete, query admin users (`User.objects.filter(tenant=tenant, is_active=True, is_admin=True)`) and call `notify()` with `hubspot_sync_completed` event type, passing results and errors

## 3. Backend time tracking sync task notification

- [x] 3.1 Modify `refresh_all_time_tracking_data()` in `apps/contracts/tasks.py` to group mappings by tenant (use `select_related('tenant')`) and track per-tenant synced/failed counts
- [x] 3.2 After processing each tenant's mappings, query admin users and call `notify()` with `time_tracking_sync_completed` event type, passing synced/total/failed counts

## 4. Backend GraphQL notification preferences

- [x] 4.1 Add `hubspot_sync_completed: bool` and `time_tracking_sync_completed: bool` fields to `NotificationPreferencesType` in `apps/tenants/schema.py`
- [x] 4.2 Update `notification_preferences` query resolver to return the two new fields from user preferences
- [x] 4.3 Add `hubspot_sync_completed` and `time_tracking_sync_completed` optional parameters to `update_notification_preferences` mutation

## 5. Backend tests

- [x] 5.1 Write tests for `_build_hubspot_sync_completed_email` — verify subject, body contains counts, body contains error info when present
- [x] 5.2 Write tests for `_build_time_tracking_sync_completed_email` — verify subject, body contains synced/total counts
- [x] 5.3 Write test for HubSpot sync task firing notification to admin users after completion
- [x] 5.4 Write test for time tracking sync task firing notification grouped by tenant

## 6. Frontend notification preferences

- [x] 6.1 Add `hubspotSyncCompleted` and `timeTrackingSyncCompleted` to the notification preferences GraphQL query in `UserSettings.tsx`
- [x] 6.2 Add toggle switches for "HubSpot sync summary" and "Time tracking sync summary" in the Notifications card
- [x] 6.3 Update the `updateNotificationPreferences` mutation call to include the new fields

## 7. Translations & verification

- [x] 7.1 Add i18n keys for notification toggle labels in `en.json` and `de.json` (e.g., "HubSpot sync summary" / "HubSpot-Sync Zusammenfassung", "Time tracking sync summary" / "Zeiterfassung-Sync Zusammenfassung")
- [x] 7.2 Run `npx tsc --noEmit` to confirm no TypeScript errors
- [x] 7.3 Run `make test-back` to confirm all backend tests pass
