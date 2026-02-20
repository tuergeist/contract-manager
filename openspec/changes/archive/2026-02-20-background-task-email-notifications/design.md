## Context

The notification system (`apps/core/notifications.py`) already supports event-based email notifications with an opt-out subscription model. Two event types exist: `todo_assigned` and `hubspot_new_contract`. The `notify()` function takes a tenant, event type, recipients list, and kwargs, then iterates recipients, checks subscription, builds the email, and sends via SMTP.

Two periodic Celery tasks run on a schedule:
- **HubSpot sync** (`apps/customers/tasks.py`): Every 6 hours. Syncs companies, products, and deals per tenant. Each sync returns `{"created": N, "updated": N}` or `{"created": N, "skipped": N}` dicts. Errors are caught per sync type.
- **Time tracking refresh** (`apps/contracts/tasks.py`): Every 12 hours. Refreshes cached Clockodo data for all mappings across tenants. Tracks synced/total counts. Errors are caught per mapping.

The `NotificationPreferencesType` in `apps/tenants/schema.py` has hardcoded fields (`todo_assigned`, `hubspot_new_contract`) and the `update_notification_preferences` mutation has matching hardcoded parameters. Adding new notification types requires extending both.

Admin users are identified via `User.is_admin` boolean field or through role-based permissions. The "Admin" default role has all permissions.

## Goals / Non-Goals

**Goals:**
- Send a summary email to Admin users after each periodic background task completes
- Include task name, timestamp, and result summary (counts, errors) in the email
- Allow Admin users to opt out of background task notification types independently
- Add subscription toggles in the user profile notification preferences UI

**Non-Goals:**
- Real-time push notifications or in-app notification center
- Configuring which tasks produce notifications at the tenant level (all periodic tasks notify)
- Retry logic for failed notification delivery (existing `notify()` behavior: log and continue)
- Task execution history or audit log (just fire-and-forget email)
- Notifying non-admin users (Managers/Viewers don't need background task visibility)

## Decisions

### 1. Two new event types rather than one generic type

Add `hubspot_sync_completed` and `time_tracking_sync_completed` as separate event types in `NOTIFICATION_TYPES`, rather than a single `background_task_completed` with a task-type parameter.

**Why separate?** The subscription model uses event type keys in `notification_preferences`. Separate types let admins subscribe to HubSpot sync results but not time tracking (or vice versa). The email content differs significantly between task types (companies/products/deals vs mapping counts). Each gets its own email builder function.

**Why not a plugin/registry for arbitrary tasks?** Only two periodic tasks exist. A generic framework would be over-engineering. If more tasks are added later, following the same pattern (add event type + email builder) is straightforward.

### 2. Recipients: Admin users only, filtered in the task

Each task collects admin users for the tenant: `User.objects.filter(tenant=tenant, is_active=True, is_admin=True)`. This list is passed to `notify()` which then checks individual subscription preferences.

**Why `is_admin` instead of a permission check?** Background task notifications are operational — they're about system health, not business data. The `is_admin` flag is the simplest filter. Non-admin users wouldn't benefit from sync statistics.

### 3. Fire notification at end of `_sync_tenant_hubspot()` and `refresh_all_time_tracking_data()`

For HubSpot sync: fire notification inside `_sync_tenant_hubspot()` after all three syncs complete (companies, products, deals). This is tenant-scoped already, so we have the right context. The email summarizes all three sync results in one message.

For time tracking: fire one notification per tenant after all that tenant's mappings are synced. The current task iterates all mappings across tenants — we'll group results by tenant, then notify each tenant's admins.

**Why not fire from the top-level task?** HubSpot: `_sync_tenant_hubspot()` already has the per-tenant context and results. Time tracking: `refresh_all_time_tracking_data()` processes mappings across tenants but doesn't group by tenant — we'll add grouping.

### 4. Email format: compact HTML summary

The email body follows the user's requested format:

```
HubSpot Sync Summary

Customers (Companies): 16 created, 1349 updated
Products: 0 created, 42 updated
Deals: 2 created, 5 skipped

⚠ Products sync failed: [error message]  (if applicable)
```

For time tracking:
```
Time Tracking Sync Summary

Mappings refreshed: 12/15
⚠ 3 mappings failed to sync
```

Simple inline-styled HTML, consistent with existing notification emails.

### 5. Extend NotificationPreferencesType and mutation with new fields

Add `hubspot_sync_completed: bool` and `time_tracking_sync_completed: bool` to `NotificationPreferencesType`. Add matching optional parameters to `update_notification_preferences` mutation. Same pattern as existing fields.

Frontend: add two new toggles in the notification preferences section of user settings.

### 6. Default subscription behavior

The opt-out model means new event types are subscribed by default (missing key = True). However, we only send to `is_admin=True` users, so non-admin users won't receive these regardless of their preference setting. The preference toggles will only appear in the UI for admin users (or we show them but they're effectively no-ops for non-admins — simpler to just show them for everyone since the backend filters recipients).

**Decision:** Show toggles for all users in the UI (consistent UX), but the backend only sends to admin users. This avoids conditional UI complexity.

## Risks / Trade-offs

- **Email volume**: HubSpot syncs every 6 hours = up to 4 emails/day per admin. Time tracking every 12 hours = 2 emails/day. This is acceptable for operational visibility.
  → Mitigation: Users can unsubscribe per notification type.

- **Sync errors in email**: If a sync partially fails (e.g., products sync throws but customers/deals succeed), the email should still be sent with available results plus error indication.
  → Mitigation: Collect results and errors separately, include both in the email. Already handled by the per-sync-type try/except in `_sync_tenant_hubspot()`.

- **Time tracking tenant grouping**: The current `refresh_all_time_tracking_data()` iterates flat across all mappings without tenant awareness. Need to group by tenant to send per-tenant notifications.
  → Mitigation: Minor refactor — query mappings with `select_related('tenant')` and group results.

- **SMTP not configured**: If SMTP isn't set up, `notify()` catches `SmtpError` and logs. No impact on task execution.
