## MODIFIED Requirements

### Requirement: Notification preferences query
The system SHALL expose a `notificationPreferences` GraphQL query that returns the current user's subscription status for each notification type, defaulting to `true` for any type not explicitly set.

#### Scenario: Query preferences for user with no overrides
- **WHEN** an authenticated user queries `notificationPreferences` and has empty `notification_preferences`
- **THEN** the system returns `todoAssigned: true`, `hubspotNewContract: true`, `hubspotSyncCompleted: true`, and `timeTrackingSyncCompleted: true`

#### Scenario: Query preferences for user with opt-outs
- **WHEN** an authenticated user queries `notificationPreferences` and has `{"hubspot_sync_completed": false}`
- **THEN** the system returns `hubspotSyncCompleted: false` and all other types as `true`

### Requirement: Update notification preferences mutation
The system SHALL provide an `updateNotificationPreferences` mutation that accepts optional boolean fields for each notification type and updates the current user's preferences.

#### Scenario: User disables HubSpot sync notifications
- **WHEN** an authenticated user calls `updateNotificationPreferences(hubspotSyncCompleted: false)`
- **THEN** the system stores `{"hubspot_sync_completed": false}` in the user's `notification_preferences` and returns success

#### Scenario: User disables time tracking sync notifications
- **WHEN** an authenticated user calls `updateNotificationPreferences(timeTrackingSyncCompleted: false)`
- **THEN** the system stores `{"time_tracking_sync_completed": false}` in the user's `notification_preferences` and returns success

#### Scenario: Partial update preserves other preferences
- **WHEN** an authenticated user with `{"todo_assigned": false}` calls `updateNotificationPreferences(hubspotSyncCompleted: false)`
- **THEN** the system stores `{"todo_assigned": false, "hubspot_sync_completed": false}` preserving the existing `todo_assigned` opt-out

### Requirement: Notification preferences UI in user settings
The system SHALL display a "Notifications" section in the user profile settings page (UserSettings) with toggle switches for each notification type.

#### Scenario: User views notification preferences
- **WHEN** a user navigates to Settings > Profile
- **THEN** the page displays a "Notifications" card with labeled toggles for "Todo assigned to me", "New contract from HubSpot", "HubSpot sync summary", and "Time tracking sync summary", reflecting current subscription state

#### Scenario: User toggles a background task notification preference
- **WHEN** a user toggles the "HubSpot sync summary" switch off
- **THEN** the system calls `updateNotificationPreferences(hubspotSyncCompleted: false)` and updates the toggle to reflect the new state
