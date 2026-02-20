## Why

Background tasks like HubSpot sync and time tracking refresh run periodically but produce no visible feedback. Admins have no way to know whether a sync completed, what it did (e.g., 16 created, 1349 updated), or if it failed — unless they check server logs. A summary email after each configurable task run gives Admins immediate visibility into background operations without requiring log access.

## What Changes

- Add a new notification event type `background_task_completed` to the notification system
- After periodic background tasks complete (HubSpot sync, time tracking refresh), send a summary email to subscribed Admin users
- The email includes: task name, timestamp, result summary (created/updated/skipped counts), and error info if applicable
- Each background task type is independently subscribable (Admin users can opt out per task type)
- Background task notifications default to enabled for Admin users only (not Manager/Viewer roles)

## Capabilities

### New Capabilities
- `background-task-notifications`: Email notifications sent to Admin users after periodic background tasks complete, with per-task-type subscription control and result summaries

### Modified Capabilities
- `notification-events`: Add new `hubspot_sync_completed` and `time_tracking_sync_completed` event types to the notification registry
- `notification-subscriptions`: Add subscription toggles for the new background task notification types in the preferences UI

## Impact

- **Backend notifications**: `apps/core/notifications.py` — new event types, email builders for task summaries
- **Backend HubSpot sync**: `apps/customers/tasks.py` — collect sync results and fire notification after completion
- **Backend time tracking sync**: `apps/contracts/tasks.py` — collect sync results and fire notification after completion
- **Backend notification preferences**: `apps/tenants/schema.py` — new preference fields for background task notifications
- **Frontend settings**: User profile notification preferences — new toggles for background task notifications
- **Translations**: New i18n keys for notification preference labels and email content
