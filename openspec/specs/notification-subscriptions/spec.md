## ADDED Requirements

### Requirement: User notification preferences storage
The system SHALL store per-user notification preferences as a JSONField `notification_preferences` on the User model, defaulting to `{}` (empty dict). A missing key means the user is subscribed (opt-out model). Only explicit `false` values indicate unsubscribed.

#### Scenario: New user has all notifications enabled by default
- **WHEN** a new user is created with no notification_preferences set
- **THEN** the system treats all notification types as subscribed (default `true`)

#### Scenario: User opts out of a notification type
- **WHEN** a user sets `notification_preferences` to `{"todo_assigned": false}`
- **THEN** the system treats `todo_assigned` as unsubscribed and all other types as subscribed

#### Scenario: User re-subscribes to a notification type
- **WHEN** a user updates `notification_preferences` to `{"todo_assigned": true}`
- **THEN** the system treats `todo_assigned` as subscribed

### Requirement: Notification preferences query
The system SHALL expose a `notificationPreferences` GraphQL query that returns the current user's subscription status for each notification type, defaulting to `true` for any type not explicitly set.

#### Scenario: Query preferences for user with no overrides
- **WHEN** an authenticated user queries `notificationPreferences` and has empty `notification_preferences`
- **THEN** the system returns `todoAssigned: true` and `hubspotNewContract: true`

#### Scenario: Query preferences for user with opt-outs
- **WHEN** an authenticated user queries `notificationPreferences` and has `{"todo_assigned": false}`
- **THEN** the system returns `todoAssigned: false` and `hubspotNewContract: true`

### Requirement: Update notification preferences mutation
The system SHALL provide an `updateNotificationPreferences` mutation that accepts optional boolean fields for each notification type and updates the current user's preferences.

#### Scenario: User disables todo assignment notifications
- **WHEN** an authenticated user calls `updateNotificationPreferences(todoAssigned: false)`
- **THEN** the system stores `{"todo_assigned": false}` in the user's `notification_preferences` and returns success

#### Scenario: User enables a previously disabled notification type
- **WHEN** an authenticated user with `{"todo_assigned": false}` calls `updateNotificationPreferences(todoAssigned: true)`
- **THEN** the system updates to `{"todo_assigned": true}` and returns success

#### Scenario: Partial update preserves other preferences
- **WHEN** an authenticated user with `{"todo_assigned": false}` calls `updateNotificationPreferences(hubspotNewContract: false)`
- **THEN** the system stores `{"todo_assigned": false, "hubspot_new_contract": false}` preserving the existing `todo_assigned` opt-out

### Requirement: No special permissions for own preferences
The `notificationPreferences` query and `updateNotificationPreferences` mutation SHALL require only authentication — any authenticated user can read and write their own notification preferences.

#### Scenario: Any authenticated user can update their preferences
- **WHEN** a non-admin authenticated user calls `updateNotificationPreferences(todoAssigned: false)`
- **THEN** the system updates the user's preferences and returns success

### Requirement: Notification preferences UI in user settings
The system SHALL display a "Notifications" section in the user profile settings page (UserSettings) with toggle switches for each notification type.

#### Scenario: User views notification preferences
- **WHEN** a user navigates to Settings > Profile
- **THEN** the page displays a "Notifications" card with labeled toggles for "Todo assigned to me" and "New contract from HubSpot", reflecting current subscription state

#### Scenario: User toggles a notification preference
- **WHEN** a user toggles the "Todo assigned to me" switch off
- **THEN** the system calls `updateNotificationPreferences(todoAssigned: false)` and updates the toggle to reflect the new state

#### Scenario: Notification preferences load defaults for new user
- **WHEN** a new user with no saved preferences visits the notification settings
- **THEN** all toggles display as enabled (on)
