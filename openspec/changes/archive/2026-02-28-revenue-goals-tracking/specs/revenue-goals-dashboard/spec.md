## ADDED Requirements

### Requirement: Goals tab on Forecasts page
The Forecasts page SHALL include a "Goals" tab alongside the existing Revenue and Liquidity tabs.

#### Scenario: Goals tab visible
- **WHEN** user navigates to /forecasts
- **THEN** a "Goals" tab SHALL be available in the tab bar

#### Scenario: Goals tab URL
- **WHEN** user clicks the Goals tab
- **THEN** the URL SHALL update to `/forecasts?tab=goals`

#### Scenario: Direct link to Goals tab
- **WHEN** user navigates to `/forecasts?tab=goals`
- **THEN** the Goals tab SHALL be active and its content displayed

### Requirement: Goals progress shows per-stream breakdown
The Goals tab SHALL display progress against yearly targets for each revenue stream.

#### Scenario: Three stream rows displayed
- **WHEN** user views the Goals tab
- **THEN** the view SHALL show one row each for: Advanced Development, Training + Implementation, Recurring Revenue

#### Scenario: Each stream shows target, YTD, and forecast
- **WHEN** goals are defined for the selected year
- **THEN** each stream row SHALL display: target amount, YTD actuals, full-year forecast, and progress percentage

#### Scenario: Progress percentage calculation
- **WHEN** a stream has target=€500,000 and full-year forecast=€400,000
- **THEN** the progress SHALL display as 80%

#### Scenario: Year selector
- **WHEN** user views the Goals tab
- **THEN** a year selector SHALL allow switching between years, defaulting to the current year

### Requirement: YTD actuals are calculated from recognized revenue
The YTD actuals per stream SHALL be the sum of recognized revenue from Jan 1 to today, classified by effective revenue type.

#### Scenario: YTD groups by effective revenue type
- **WHEN** calculating YTD for a stream
- **THEN** the system SHALL sum recognized revenue from all contract items whose effective_revenue_type matches the stream

#### Scenario: Items without classification appear as unclassified
- **WHEN** a contract item has no effective revenue type (no product, no explicit type)
- **THEN** its revenue SHALL be grouped under an "Unclassified" category with a visual warning

#### Scenario: YTD uses recognition schedule
- **WHEN** calculating YTD actuals
- **THEN** the system SHALL use the contract recognition schedule (not billing schedule)

### Requirement: Full-year forecast includes future months
The full-year forecast per stream SHALL combine YTD actuals with projected revenue for the remaining months.

#### Scenario: Forecast covers Jan 1 to Dec 31
- **WHEN** calculating the full-year forecast for a stream
- **THEN** the system SHALL sum recognized revenue from Jan 1 to Dec 31 of the selected year

#### Scenario: Forecast respects contract end dates
- **WHEN** a contract ends mid-year
- **THEN** the forecast SHALL only include revenue from that contract up to its end date

### Requirement: Progress visualization
Each revenue stream SHALL display a visual progress indicator.

#### Scenario: Progress bar shows forecast vs target
- **WHEN** a stream has a defined target
- **THEN** a progress bar SHALL fill proportionally to (forecast / target)

#### Scenario: Over-target indication
- **WHEN** the forecast exceeds the target (>100%)
- **THEN** the progress bar SHALL visually indicate the overshoot (e.g., different color or overflow indicator)

#### Scenario: No target defined
- **WHEN** a stream has no revenue goal for the selected year
- **THEN** the row SHALL show actuals and forecast but no progress bar, with a prompt to set a goal

### Requirement: Total row across all streams
The Goals view SHALL display a total row summing all three streams.

#### Scenario: Total row sums all streams
- **WHEN** viewing the Goals tab
- **THEN** a total row SHALL display the sum of targets, YTD actuals, and forecasts across all streams

#### Scenario: Total progress percentage
- **WHEN** all three streams have targets
- **THEN** the total progress SHALL be calculated as (total forecast / total target)

### Requirement: GraphQL query for revenue by stream
The backend SHALL expose a query that returns revenue data broken down by revenue stream.

#### Scenario: Query returns per-stream data
- **WHEN** client executes `revenueByStream(year: 2026)`
- **THEN** the response SHALL include for each stream: ytdActual, fullYearForecast

#### Scenario: Query includes unclassified bucket
- **WHEN** items exist without an effective revenue type
- **THEN** the response SHALL include an "unclassified" entry with those amounts

#### Scenario: Query is tenant-scoped
- **WHEN** querying revenue by stream
- **THEN** results SHALL be filtered to the authenticated user's tenant
