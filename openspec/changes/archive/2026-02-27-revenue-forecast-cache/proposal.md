## Why

The revenue forecast (`/forecasts`) is fully recomputed on every page load — fetching all active contracts, invoice records, imported invoices, computing billing schedules, and matching invoices to periods. This is expensive and grows linearly with the number of contracts. The underlying data only changes when invoices are created/voided/paid or contracts are modified, which happens infrequently compared to how often the forecast is viewed.

## What Changes

- Add Redis-based caching for the `revenue_forecast` and `recognition_forecast` GraphQL queries
- Cache key includes tenant ID + all query parameters (months, quarters, view, pro_rata, exclude_one_off)
- Cache TTL is configurable per tenant via `Tenant.settings["forecast_cache_ttl"]` (default: 60 minutes)
- Automatic cache invalidation via Django signals when relevant models change:
  - `InvoiceRecord`: post_save, post_delete (covers create, void, pay, status changes)
  - `ImportedInvoice`: post_save (extraction_status changes)
  - `Contract`: post_save (status, dates, billing interval changes)
  - `ContractItem` / `ContractItemPrice`: post_save, post_delete (item/price changes)
- Invalidation clears all cached forecast keys for the affected tenant
- Add a settings UI field for forecast cache TTL under an appropriate settings tab
- Add a manual "Refresh" button on the forecast page to force cache bypass

## Capabilities

### New Capabilities
- `revenue-forecast-cache`: Redis caching layer for revenue/recognition forecast queries with signal-based invalidation and per-tenant configurable TTL

### Modified Capabilities
_None — this is a pure performance optimization with no changes to forecast requirements or behavior._

## Impact

- **Backend**: `apps/contracts/schema.py` (revenue_forecast, recognition_forecast queries), new cache module, Django signals in `apps/invoices/`, `apps/contracts/`
- **Frontend**: Forecast page (refresh button), settings page (cache TTL field)
- **Infrastructure**: Requires Redis (already available in both local and production Docker setups)
- **API**: No GraphQL schema changes to existing fields; forecast queries return identical data, just faster on cache hits
- **Settings**: New `forecast_cache_ttl` key in `Tenant.settings` JSONField (existing pattern)
