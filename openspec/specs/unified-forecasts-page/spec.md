## Requirements

### Requirement: Unified forecasts page accessible from navigation
The system SHALL provide a single "Forecasts" menu item in the main sidebar navigation that opens a tabbed page at `/forecasts`.

#### Scenario: Navigate to forecasts page
- **WHEN** user clicks "Forecasts" in sidebar
- **THEN** browser navigates to `/forecasts` and displays the forecasts page with the Revenue tab active by default

#### Scenario: Page requires authentication
- **WHEN** unauthenticated user accesses `/forecasts`
- **THEN** user is redirected to login page

### Requirement: Forecasts page has Revenue and Liquidity tabs
The system SHALL display tabs for "Revenue" and "Liquidity" on the forecasts page. The active tab SHALL be reflected in the URL via a `tab` search parameter.

#### Scenario: Switch to liquidity tab
- **WHEN** user clicks "Liquidity" tab
- **THEN** URL updates to `/forecasts?tab=liquidity`
- **AND** the liquidity forecast content is displayed

#### Scenario: Switch to revenue tab
- **WHEN** user clicks "Revenue" tab
- **THEN** URL updates to `/forecasts?tab=revenue`
- **AND** the revenue forecast content is displayed

#### Scenario: Direct link to liquidity tab
- **WHEN** user navigates to `/forecasts?tab=liquidity`
- **THEN** page opens with Liquidity tab active

#### Scenario: Default tab when no param
- **WHEN** user navigates to `/forecasts` without a tab parameter
- **THEN** Revenue tab is active by default

### Requirement: Liquidity tab requires banking permission
The system SHALL only display the Liquidity tab to users with `banking.read` permission. Users without this permission SHALL see only the Revenue tab with no tab switcher.

#### Scenario: User without banking permission
- **WHEN** user without `banking.read` permission navigates to `/forecasts`
- **THEN** only the Revenue forecast is shown
- **AND** no tab switcher is displayed

#### Scenario: User with banking permission
- **WHEN** user with `banking.read` permission navigates to `/forecasts`
- **THEN** both Revenue and Liquidity tabs are visible and switchable

### Requirement: Only active tab content is rendered
The system SHALL only mount and render the component for the currently active tab. Inactive tab content SHALL NOT be mounted to avoid unnecessary GraphQL queries.

#### Scenario: Revenue tab active
- **WHEN** Revenue tab is active
- **THEN** only the RevenueForecast component is mounted
- **AND** no liquidity forecast queries are executed

#### Scenario: Liquidity tab active
- **WHEN** Liquidity tab is active
- **THEN** only the LiquidityForecast component is mounted
- **AND** no revenue forecast queries are executed
