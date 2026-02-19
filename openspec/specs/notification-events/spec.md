## ADDED Requirements

### Requirement: Notification type registry
The system SHALL maintain a `NOTIFICATION_TYPES` registry in `apps/core/notifications.py` mapping event type strings to metadata (description key for i18n, subject builder, body builder). Initial event types: `todo_assigned`, `hubspot_new_contract`.

#### Scenario: Registry contains all supported event types
- **WHEN** the system starts
- **THEN** `NOTIFICATION_TYPES` contains entries for `todo_assigned` and `hubspot_new_contract` with subject and body builder functions

### Requirement: Notification dispatch function
The system SHALL provide a `notify(tenant, event_type, **kwargs)` function that determines recipients, checks each recipient's subscription preference, builds the email, and calls `send_notification()` from `apps/core/smtp.py`. Notification failures SHALL be logged but SHALL NOT raise exceptions or block the calling operation.

#### Scenario: Notification sent to subscribed user
- **WHEN** `notify` is called for `todo_assigned` and the recipient has not opted out
- **THEN** the system calls `send_notification` with the recipient's email, an appropriate subject, and an HTML body describing the todo

#### Scenario: Notification skipped for unsubscribed user
- **WHEN** `notify` is called for `todo_assigned` and the recipient has `{"todo_assigned": false}`
- **THEN** the system does not call `send_notification` for that recipient

#### Scenario: Notification skipped when SMTP not configured
- **WHEN** `notify` is called but the tenant has no SMTP configuration
- **THEN** the system catches the `SmtpError`, logs a debug message, and returns without error

#### Scenario: SMTP failure does not block the calling operation
- **WHEN** `notify` is called and `send_notification` raises `SmtpError`
- **THEN** the system logs the error and returns without raising an exception

### Requirement: Todo assignment notification
The system SHALL fire a `todo_assigned` notification when a todo is assigned to a user who is not the creator. The notification email SHALL include the todo text, who assigned it, and links are not required for v1.

#### Scenario: Notification on create_todo with different assignee
- **WHEN** user A creates a todo assigned to user B (A != B)
- **THEN** the system fires `todo_assigned` notification to user B with subject containing "Todo assigned" and body containing the todo text and user A's name

#### Scenario: No notification on create_todo assigned to self
- **WHEN** user A creates a todo assigned to themselves (or assigned_to_id is not specified, defaulting to self)
- **THEN** the system does not fire a `todo_assigned` notification

#### Scenario: Notification on update_todo with reassignment
- **WHEN** user A updates a todo changing `assigned_to_id` to user C (A != C)
- **THEN** the system fires `todo_assigned` notification to user C

#### Scenario: No notification on reassign_todo_to_self
- **WHEN** a user calls `reassign_todo_to_self`
- **THEN** the system does not fire a `todo_assigned` notification (user reassigned to themselves)

### Requirement: HubSpot new contract notification
The system SHALL fire a `hubspot_new_contract` notification when `_sync_deal` creates a new contract. The notification SHALL be sent to all active users in the tenant who are subscribed to this event type. The email SHALL include the contract name and customer name.

#### Scenario: Notification sent to all subscribed users on new deal sync
- **WHEN** `_sync_deal` creates a new contract for customer "Acme Corp"
- **THEN** the system fires `hubspot_new_contract` notification to all active tenant users who have not opted out, with subject containing "New contract" and body containing the contract name and "Acme Corp"

#### Scenario: Opted-out users are excluded
- **WHEN** `_sync_deal` creates a new contract and user X has `{"hubspot_new_contract": false}`
- **THEN** user X does not receive the notification email, but other subscribed users do

#### Scenario: No notification for skipped (already existing) deals
- **WHEN** `_sync_deal` returns `"skipped"` because the contract already exists
- **THEN** the system does not fire any notification

### Requirement: Subscription check function
The system SHALL provide an `is_subscribed(user, event_type)` function that returns `True` if the user's `notification_preferences` does not contain an explicit `false` for the given event type.

#### Scenario: User with no preferences is subscribed
- **WHEN** `is_subscribed` is called for a user with `notification_preferences = {}`
- **THEN** it returns `True`

#### Scenario: User with explicit opt-out is not subscribed
- **WHEN** `is_subscribed` is called for a user with `{"todo_assigned": false}` and event_type `"todo_assigned"`
- **THEN** it returns `False`

#### Scenario: User with explicit true is subscribed
- **WHEN** `is_subscribed` is called for a user with `{"todo_assigned": true}` and event_type `"todo_assigned"`
- **THEN** it returns `True`
