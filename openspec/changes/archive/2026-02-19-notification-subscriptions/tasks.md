## 1. User Model — Notification Preferences Field

- [x] 1.1 Add `notification_preferences` JSONField to User model (default=dict, blank=True)
- [x] 1.2 Create and run migration

## 2. Notification Core Module

- [x] 2.1 Create `apps/core/notifications.py` with `NOTIFICATION_TYPES` registry, `is_subscribed(user, event_type)`, and `notify(tenant, event_type, **kwargs)`
- [x] 2.2 Implement `todo_assigned` email builder (subject + HTML body with todo text and assigner name)
- [x] 2.3 Implement `hubspot_new_contract` email builder (subject + HTML body with contract name and customer name)
- [x] 2.4 Ensure `notify` catches `SmtpError` and logs without raising

## 3. GraphQL API — Preferences Query and Mutation

- [x] 3.1 Add `NotificationPreferencesType` to `tenants/schema.py` with `todo_assigned: bool` and `hubspot_new_contract: bool`
- [x] 3.2 Add `notification_preferences` query on TenantQuery returning current user's preferences (default true)
- [x] 3.3 Add `update_notification_preferences` mutation on TenantMutation accepting optional booleans, updating user's JSONField

## 4. Hook Points — Fire Notifications

- [x] 4.1 In `create_todo`: after successful save, call `notify` for `todo_assigned` if `assigned_to_id != user.id`
- [x] 4.2 In `update_todo`: if `assigned_to_id` changed to a different user (not creator), call `notify` for `todo_assigned`
- [x] 4.3 In `_sync_deal`: after creating a new contract, call `notify` for `hubspot_new_contract` with contract and customer info

## 5. Backend Tests

- [x] 5.1 Test `is_subscribed` — default subscribed, explicit false, explicit true
- [x] 5.2 Test `notify` — sends to subscribed user, skips unsubscribed, catches SmtpError
- [x] 5.3 Test `todo_assigned` — fires on create with different assignee, skips self-assign
- [x] 5.4 Test `hubspot_new_contract` — fires on new contract, skips opted-out users
- [x] 5.5 Test `notification_preferences` query — defaults and opt-outs
- [x] 5.6 Test `update_notification_preferences` mutation — partial update, re-subscribe

## 6. Frontend — Notification Preferences UI

- [x] 6.1 Create `NotificationPreferences.tsx` component with toggle switches for each notification type
- [x] 6.2 Add GQL query and mutation for notification preferences
- [x] 6.3 Add "Notifications" section to `UserSettings.tsx` below PasswordChange
- [x] 6.4 Add translations (en.json, de.json) for notification preference labels and descriptions
