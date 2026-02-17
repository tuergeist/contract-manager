## ADDED Requirements

### Requirement: Tenant admin can configure help video links per screen
The system SHALL allow tenant admins with `settings.write` permission to configure help video links for each screen. Configuration is stored in the tenant's `settings` JSON field under the key `help_video_links`. Each entry maps a route key to one or more links, where each link has a `url` and an optional `label`.

#### Scenario: Admin adds a help video link for a screen
- **WHEN** admin selects a screen from the predefined route list, enters a URL and optional label, and saves
- **THEN** the system stores the link under `settings.help_video_links[routeKey]` for the tenant

#### Scenario: Admin adds multiple links for one screen
- **WHEN** admin adds two or more links for the same route key and saves
- **THEN** all links are stored as an array under that route key

#### Scenario: Admin removes all links for a screen
- **WHEN** admin removes the last link entry for a route key and saves
- **THEN** the route key entry is removed from the configuration

#### Scenario: Admin without settings.write permission
- **WHEN** a user without `settings.write` permission attempts to update help video links
- **THEN** the system SHALL reject the mutation with a permission error

### Requirement: Settings UI for managing help video links
The system SHALL provide a management UI within the General settings tab. The UI shows a table of configured screens with their links and allows adding, editing, and removing entries.

#### Scenario: Settings UI displays configured links
- **WHEN** admin navigates to General settings
- **THEN** the help video links section displays all configured route-key-to-links mappings in a table with columns for Screen name and Links

#### Scenario: Admin selects a screen from predefined list
- **WHEN** admin clicks to add a new screen entry
- **THEN** a select dropdown shows all available route keys with human-readable labels (e.g., "Customers", "Contract Detail")

#### Scenario: Admin adds a link with URL only
- **WHEN** admin enters a URL but no label for a link
- **THEN** the system accepts it and uses the URL as the display text in the dropdown (or a default label)

### Requirement: GraphQL query returns help video links
The system SHALL expose a `helpVideoLinks` query that returns all configured help video links for the current tenant.

#### Scenario: Query returns configured links
- **WHEN** an authenticated user queries `helpVideoLinks`
- **THEN** the system returns a list of entries, each with `routeKey` (String) and `links` (array of `{ url, label }`)

#### Scenario: No links configured
- **WHEN** no help video links are configured for the tenant
- **THEN** the query returns an empty list

### Requirement: GraphQL mutation updates help video links
The system SHALL expose an `updateHelpVideoLinks` mutation that replaces the entire help video link configuration for the tenant.

#### Scenario: Mutation replaces all links
- **WHEN** admin sends `updateHelpVideoLinks` with a new set of route-key/links entries
- **THEN** the system replaces `settings.help_video_links` with the provided data and returns the updated configuration

#### Scenario: Mutation with empty input clears all links
- **WHEN** admin sends `updateHelpVideoLinks` with an empty array
- **THEN** the system removes the `help_video_links` key from settings

### Requirement: Help video button displays on pages with configured links
The system SHALL render a green "Kurze Anleitung" button in the top-right area of the main content on any page that has one or more help video links configured.

#### Scenario: Page with one configured link
- **WHEN** user navigates to a page that has exactly one help video link configured
- **THEN** a green button labeled "Kurze Anleitung" appears in the top-right of the content area

#### Scenario: Page with no configured links
- **WHEN** user navigates to a page with no help video links configured
- **THEN** no help video button is displayed

#### Scenario: Page with parameterized route matches config
- **WHEN** user navigates to `/customers/42` and a link is configured for route key `/customers/:id`
- **THEN** the button appears, matching the parameterized route pattern

### Requirement: Help video button opens link in new tab
The system SHALL open the configured video URL in a new browser tab when the user clicks the help video button.

#### Scenario: Single link button click
- **WHEN** user clicks the "Kurze Anleitung" button on a page with one configured link
- **THEN** the configured URL opens in a new browser tab

#### Scenario: Multiple links show dropdown
- **WHEN** user clicks the "Kurze Anleitung" button on a page with multiple configured links
- **THEN** a dropdown menu appears showing each link's label

#### Scenario: Dropdown link click
- **WHEN** user clicks a link label in the dropdown menu
- **THEN** that URL opens in a new browser tab and the dropdown closes
