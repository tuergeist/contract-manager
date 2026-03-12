## 1. Cache Infrastructure

- [x] 1.1 Create `apps/contracts/forecast_cache.py` with cache key generation (`forecast:v1:{tenant_id}:{query_hash}`), key tracking (store active keys under `forecast:v1:{tenant_id}:_keys`), `get_cached_forecast()`, `set_cached_forecast()`, and `invalidate_tenant_forecast()` functions
- [x] 1.2 Add serialization helpers: `RevenueForecastResult` to dict and dict to `RevenueForecastResult` (including nested `RevenueForecastContract` and `MonthlyTotal` types)
- [x] 1.3 Write tests for cache key generation, serialization round-trip, cache hit/miss, TTL reading from tenant settings, and invalidation

## 2. Wire Cache into Forecast Queries

- [x] 2.1 Modify `revenue_forecast()` in `apps/contracts/schema.py` to check cache before computing, store result after computing, and read TTL from `tenant.settings["forecast_cache_ttl"]` (default 60 min)
- [x] 2.2 Modify `recognition_forecast()` with the same caching pattern using a distinct key prefix (`recognition:v1:`)
- [x] 2.3 Add `refresh: bool = False` parameter to both queries — when true, skip cache lookup and overwrite
- [x] 2.4 Write tests verifying cache hit returns same data, refresh bypasses cache, and different params produce separate entries

## 3. Signal-Based Invalidation

- [x] 3.1 Create `apps/contracts/signals.py` with `@receiver` handlers for `post_save`/`post_delete` on `InvoiceRecord`, `ImportedInvoice`, `Contract`, `ContractItem`, `ContractItemPrice` — each calls `invalidate_tenant_forecast(tenant_id)`
- [x] 3.2 Register signals in `apps/contracts/apps.py` `ready()` method
- [x] 3.3 Write tests verifying that saving/deleting each model type triggers cache invalidation for the correct tenant

## 4. Settings UI — Cache TTL

- [x] 4.1 Add GraphQL query field to expose `forecast_cache_ttl` from tenant settings (with default 60)
- [x] 4.2 Add GraphQL mutation to save `forecast_cache_ttl` to `Tenant.settings`
- [x] 4.3 Add cache TTL input field to the frontend settings page (numeric input, minutes, default 60)
- [x] 4.4 Add translations for the TTL setting label and description (en + de)

## 5. Frontend — Refresh Button

- [x] 5.1 Add `refresh` variable to the `RevenueForecast` GraphQL query
- [x] 5.2 Add a refresh/reload button to the forecast page toolbar that re-fetches with `refresh: true`
- [x] 5.3 Add translations for the refresh button label (en + de)
