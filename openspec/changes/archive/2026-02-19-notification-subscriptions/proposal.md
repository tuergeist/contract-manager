## Why

Users have no way to be notified about events that matter to them — a todo assigned to them, or a new contract arriving via HubSpot deal sync. The SMTP notification service is now in place but nothing triggers it. Users need a subscription model where they can opt in/out of specific event types, and the system fires notifications via SMTP when those events occur.

## What Changes

- Add a notification event system that fires when specific things happen (todo assigned, todo created for user, new HubSpot contract)
- Add per-user notification preferences stored in the User model or tenant settings, defaulting to subscribed
- Add a settings UI where users can toggle which notification types they receive
- Hook into existing code paths: `create_todo` mutation (todo assigned), `update_todo`/`reassign_todo_to_self` (reassignment), and `sync_deals` (new contract created)
- Send emails via `send_notification()` from `apps/core/smtp.py` when events fire and the user is subscribed

## Capabilities

### New Capabilities
- `notification-subscriptions`: Per-user notification preferences (subscribe/unsubscribe to event types) with settings UI and GraphQL API
- `notification-events`: Event firing and email dispatch for todo assignment and HubSpot contract arrival

### Modified Capabilities
_(none)_

## Impact

- **Backend**: New `apps/core/notifications.py` — event registry, dispatch logic, preference lookup
- **Backend**: `apps/tenants/models.py` or `apps/tenants/schema.py` — user notification preferences (stored in user profile or tenant settings)
- **Backend**: `apps/todos/schema.py` — fire event on `create_todo`, `update_todo` (reassign), `reassign_todo_to_self`
- **Backend**: `apps/customers/hubspot.py` — fire event in `_sync_deal` when a new contract is created
- **Frontend**: New notification preferences component in user settings (profile section)
- **Frontend**: Translations (en.json, de.json)
- **Dependencies**: None new — uses existing `apps/core/smtp.py`
