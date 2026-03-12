## ADDED Requirements

### Requirement: Revenue and recognition forecast results are cached in Redis
The system SHALL cache the results of `revenue_forecast` and `recognition_forecast` GraphQL queries in Redis, keyed by tenant ID and query parameters. On subsequent requests with the same parameters, the system SHALL return the cached result without recomputing.

#### Scenario: First request computes and caches
- **WHEN** a user queries `revenue_forecast` with parameters (view=monthly, months=13, pro_rata=false, exclude_one_off=false)
- **AND** no cached result exists for this tenant and parameter combination
- **THEN** the system SHALL compute the forecast, store the result in Redis, and return it

#### Scenario: Subsequent request returns cached result
- **WHEN** a user queries `revenue_forecast` with the same parameters as a previously cached request
- **AND** the cache entry has not expired or been invalidated
- **THEN** the system SHALL return the cached result without recomputing

#### Scenario: Different parameters produce separate cache entries
- **WHEN** a user queries `revenue_forecast` with view=quarterly
- **AND** a cached result exists for view=monthly
- **THEN** the system SHALL compute and cache a separate result for the quarterly view

#### Scenario: Recognition forecast is cached independently
- **WHEN** a user queries `recognition_forecast`
- **THEN** the system SHALL cache its result separately from `revenue_forecast` using a distinct cache key prefix

### Requirement: Cache TTL is configurable per tenant
The system SHALL read the cache TTL from `Tenant.settings["forecast_cache_ttl"]` as an integer representing minutes. If not set, the system SHALL use a default of 60 minutes.

#### Scenario: Default TTL when not configured
- **WHEN** `Tenant.settings` does not contain `forecast_cache_ttl`
- **THEN** cached forecast entries SHALL expire after 60 minutes

#### Scenario: Custom TTL is respected
- **WHEN** `Tenant.settings["forecast_cache_ttl"]` is set to 30
- **THEN** cached forecast entries SHALL expire after 30 minutes

#### Scenario: TTL change takes effect on next cache write
- **WHEN** an admin changes the forecast cache TTL from 60 to 15
- **AND** the existing cache entry was written with a 60-minute TTL
- **THEN** the existing entry SHALL remain until it expires or is invalidated
- **AND** the next cache write SHALL use the new 15-minute TTL

### Requirement: Cache is invalidated when underlying data changes
The system SHALL automatically invalidate all cached forecast entries for a tenant when any of the following models are saved or deleted within that tenant.

#### Scenario: Invoice record created
- **WHEN** a new `InvoiceRecord` is saved for a tenant
- **THEN** all cached forecast entries for that tenant SHALL be invalidated

#### Scenario: Invoice record status changed
- **WHEN** an `InvoiceRecord` status changes (e.g., finalized to paid, or voided)
- **THEN** all cached forecast entries for that tenant SHALL be invalidated

#### Scenario: Invoice record deleted
- **WHEN** an `InvoiceRecord` is deleted
- **THEN** all cached forecast entries for that tenant SHALL be invalidated

#### Scenario: Imported invoice status changed
- **WHEN** an `ImportedInvoice` is saved with a changed `extraction_status`
- **THEN** all cached forecast entries for that tenant SHALL be invalidated

#### Scenario: Contract modified
- **WHEN** a `Contract` is saved (status, dates, or billing interval changed)
- **THEN** all cached forecast entries for that tenant SHALL be invalidated

#### Scenario: Contract item added or removed
- **WHEN** a `ContractItem` is saved or deleted
- **THEN** all cached forecast entries for that tenant's contract SHALL be invalidated

#### Scenario: Contract item price changed
- **WHEN** a `ContractItemPrice` is saved or deleted
- **THEN** all cached forecast entries for the associated tenant SHALL be invalidated

### Requirement: Users can manually bypass the cache
The `revenue_forecast` and `recognition_forecast` queries SHALL accept an optional `refresh` boolean parameter. When `refresh` is true, the system SHALL skip the cache lookup, recompute the result, and overwrite the cached entry.

#### Scenario: Refresh parameter forces recomputation
- **WHEN** a user queries `revenue_forecast` with `refresh=true`
- **AND** a cached result exists
- **THEN** the system SHALL ignore the cache, recompute the forecast, store the new result, and return it

#### Scenario: Refresh parameter defaults to false
- **WHEN** a user queries `revenue_forecast` without the `refresh` parameter
- **THEN** the system SHALL use the cached result if available

### Requirement: Forecast page displays a refresh button
The revenue forecast page SHALL display a refresh button that re-fetches the forecast with cache bypass enabled.

#### Scenario: User clicks refresh
- **WHEN** a user clicks the refresh button on the forecast page
- **THEN** the frontend SHALL send the forecast query with `refresh=true`
- **AND** the table SHALL update with the freshly computed result

### Requirement: Forecast cache TTL is configurable in settings UI
The settings page SHALL include a field for configuring the forecast cache TTL in minutes.

#### Scenario: Admin sets cache TTL
- **WHEN** an admin navigates to the settings page
- **AND** enters a value of 30 in the forecast cache TTL field
- **AND** saves the settings
- **THEN** `Tenant.settings["forecast_cache_ttl"]` SHALL be updated to 30

#### Scenario: Default value displayed when not configured
- **WHEN** an admin navigates to the settings page
- **AND** no custom forecast cache TTL is configured
- **THEN** the field SHALL display 60 as the default value
