## MODIFIED Requirements

### Requirement: Liquidity forecast page accessible from navigation
The system SHALL provide the liquidity forecast as a tab within the unified Forecasts page at `/forecasts?tab=liquidity`. The liquidity forecast SHALL NOT have a dedicated sidebar navigation entry.

#### Scenario: Navigate to liquidity forecast
- **WHEN** user clicks "Forecasts" in sidebar and then selects "Liquidity" tab
- **THEN** the liquidity forecast content is displayed at `/forecasts?tab=liquidity`

#### Scenario: Page requires authentication
- **WHEN** unauthenticated user accesses `/forecasts?tab=liquidity`
- **THEN** user is redirected to login page

## REMOVED Requirements

### Requirement: Liquidity forecast has dedicated sidebar entry
**Reason**: Liquidity forecast is now accessed as a tab on the unified Forecasts page.
**Migration**: Users navigate to Forecasts page and select the Liquidity tab.
