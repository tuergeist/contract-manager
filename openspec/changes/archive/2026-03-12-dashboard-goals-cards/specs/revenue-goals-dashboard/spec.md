## ADDED Requirements

### Requirement: Revenue Goals section on main dashboard
The main dashboard SHALL display a "Revenue Goals" section showing per-stream goal progress cards.

#### Scenario: Section shows revenue stream cards
- **WHEN** user views the dashboard
- **AND** revenue goals or forecast data exist for the current year
- **THEN** a "Revenue Goals" section SHALL display cards for: Recurring, Advanced Development, Training & Implementation

#### Scenario: Each card shows forecast vs target
- **WHEN** a revenue goal is set for the stream in the current year
- **THEN** the card SHALL show the full-year forecast as primary value, target, difference (color-coded), and a progress bar with percentage

#### Scenario: Card without target
- **WHEN** no target is set for a revenue stream
- **THEN** the card SHALL show only the forecast value with a link to set goals in settings

#### Scenario: Section hidden when no data
- **WHEN** no revenue goals exist AND no forecast data exists for the current year
- **THEN** the Revenue Goals section SHALL NOT be displayed

#### Scenario: Cards navigate to goals tab
- **WHEN** user clicks a revenue goal card
- **THEN** the system SHALL navigate to `/forecasts?tab=goals`
