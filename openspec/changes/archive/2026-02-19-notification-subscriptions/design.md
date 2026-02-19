## Context

The SMTP notification service (`apps/core/smtp.py`) is deployed and working — it provides `send_notification(tenant, *, to, subject, body_html)` for sending transactional emails. Nothing in the system triggers it yet. Users need to receive emails when events they care about happen (todos assigned to them, new HubSpot contracts), and they need a way to opt out.

Current state:
- `TodoItem` has `created_by` (FK → User) and `assigned_to` (FK → User, nullable). Mutations: `create_todo`, `update_todo`, `reassign_todo_to_self`.
- `_sync_deal()` in `apps/customers/hubspot.py` creates Contract drafts from HubSpot closed-won deals, returns `"created"` / `"skipped"`.
- User model (`apps/tenants/models.py`) has no notification preferences. No JSONField or settings field on User.
- Frontend profile lives in `UserSettings.tsx` (ProfileEdit + PasswordChange + language toggle). No notification preferences UI exists.

## Goals / Non-Goals

**Goals:**
- Users receive email notifications for: todo assigned to them (when they are not the creator), and new contracts arriving via HubSpot deal sync
- Users can opt out of specific notification types via a preferences UI in their profile settings
- All notification types default to **subscribed** (opt-out model)
- Notifications are only sent when the tenant has SMTP configured
- The system is extensible — adding a new event type should require minimal code

**Non-Goals:**
- In-app notifications (browser, bell icon, notification center) — email only for now
- Real-time / WebSocket push — synchronous dispatch within the request is fine for v1
- Notification history / audit log of sent notifications
- Bulk/digest emails — each event fires one email immediately
- Admin control over which notification types are available — this is per-user only
- Todo reminder notifications (date-based) — only assignment events

## Decisions

### 1. Preference storage: JSONField on User model

Store preferences as a JSONField `notification_preferences` on the User model, defaulting to `{}` (empty dict = all subscribed).

**Structure:** `{"todo_assigned": false, "hubspot_new_contract": false}` — only store explicit opt-outs. Missing key = subscribed (default).

**Alternatives considered:**
- Separate NotificationPreference model with rows per user/event-type: Over-engineered for 2-3 event types. A JSONField is simpler, no migrations when adding new event types, and matches the existing pattern (tenant.settings is also JSONField).
- Tenant-level settings: Wrong granularity — this is per-user, not per-tenant.

### 2. Event dispatch: Simple function calls, no event bus

Call `notify(tenant, event_type, **context)` directly from mutation code. The `notify` function checks preferences and sends email inline.

**Rationale:** The app has 2 event types and ~5 call sites. A pub/sub event bus, signal system, or Celery task queue adds complexity with no benefit at this scale. If we need async dispatch later, we wrap `notify` internals — the call sites don't change.

**Alternatives considered:**
- Django signals: Implicit coupling, hard to trace, and we'd need custom signals. Direct calls are explicit and debuggable.
- Celery tasks: SMTP send is fast (<1s). Async adds failure modes (broker down, task lost) without meaningful UX improvement. Can migrate later if needed.

### 3. Notification module location: `apps/core/notifications.py`

Single module containing:
- `NOTIFICATION_TYPES` registry (dict mapping event type string → metadata: description, subject template, body builder)
- `notify(tenant, event_type, **kwargs)` — looks up recipients, checks preferences, builds email, calls `send_notification`
- `is_subscribed(user, event_type)` → bool — checks user.notification_preferences
- Email body builders per event type (simple HTML functions)

This sits next to `smtp.py` in `apps/core/` since it's a cross-cutting concern used by todos and customers.

### 4. Hook points

**Todo assigned** (`todo_assigned`):
- `create_todo`: After successful save, if `assigned_to_id != user.id` (assigned to someone else), fire notification to assigned user.
- `update_todo`: If `assigned_to_id` changed and new assignee != creator, fire notification to new assignee.
- `reassign_todo_to_self`: No notification needed — user reassigned to themselves.

**HubSpot new contract** (`hubspot_new_contract`):
- `_sync_deal`: After `return "created"`, fire notification to all active users in the tenant (this is a team-wide event — everyone with the preference enabled gets notified). We filter by `is_active=True` and check each user's preferences.

### 5. Frontend: Notification preferences in UserSettings

Add a "Notifications" section to `UserSettings.tsx` (the profile/account page), below PasswordChange and above Language. This is per-user settings, not admin settings — it belongs in the user profile, not in General Settings.

Component: simple card with toggle switches for each notification type. Query to load current preferences, mutation to save them.

### 6. GraphQL API surface

**Query:**
- `notificationPreferences` → `NotificationPreferencesType` with boolean fields per event type (resolved from user's JSONField, defaulting to `true`)

**Mutation:**
- `updateNotificationPreferences(todoAssigned: Boolean, hubspotNewContract: Boolean)` → `{success, error}` — updates user.notification_preferences

No special permissions needed — users can only read/write their own preferences.

## Risks / Trade-offs

**[Synchronous email send in request path]** → Acceptable for v1. SMTP send takes <1s. If it fails, the mutation still succeeds (we catch SmtpError and log it — notification failure should not block the action). Can move to Celery later without changing call sites.

**[HubSpot sync notifies all users]** → Could be noisy if many deals sync at once. Mitigation: each user can opt out. Future improvement: batch into digest. For now, individual emails per deal per user is acceptable since deal sync is infrequent.

**[No SMTP = silent no-op]** → If tenant has no SMTP configured, `notify()` catches `SmtpError` and logs a debug message. No error surfaced to users. This is intentional — notifications are best-effort.

**[Adding new event types requires code changes]** → Need to add to NOTIFICATION_TYPES registry, add the hook call, and add a frontend toggle. No migration needed (JSONField). This is fine for the expected rate of new event types (~1-2 per quarter).
