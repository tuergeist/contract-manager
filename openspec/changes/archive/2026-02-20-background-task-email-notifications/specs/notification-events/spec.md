## MODIFIED Requirements

### Requirement: Notification type registry
The system SHALL maintain a `NOTIFICATION_TYPES` registry in `apps/core/notifications.py` mapping event type strings to metadata (description key for i18n, subject builder, body builder). Event types: `todo_assigned`, `hubspot_new_contract`, `hubspot_sync_completed`, `time_tracking_sync_completed`.

#### Scenario: Registry contains all supported event types
- **WHEN** the system starts
- **THEN** `NOTIFICATION_TYPES` contains entries for `todo_assigned`, `hubspot_new_contract`, `hubspot_sync_completed`, and `time_tracking_sync_completed` with subject and body builder functions
