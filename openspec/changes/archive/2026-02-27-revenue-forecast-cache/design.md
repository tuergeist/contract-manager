## Context

The `revenue_forecast` and `recognition_forecast` queries in `apps/contracts/schema.py` are the most expensive GraphQL queries in the system. Each call fetches all active/paused contracts with prefetched items and prices, all invoice records and imported invoices for the period, then computes billing schedules and matches invoices per contract. The data only changes on discrete events (invoice created/voided/paid, contract modified), yet the forecast is recomputed on every page load.

Django's cache framework is already configured with Redis (`django.core.cache.backends.redis.RedisCache`) in production and `LocMemCache` in tests. The `Tenant.settings` JSONField is the established pattern for per-tenant configuration (used for SMTP, banking, M365, etc.).

## Goals / Non-Goals

**Goals:**
- Cache revenue and recognition forecast results in Redis, keyed by tenant + query params
- Invalidate cache automatically when underlying data changes (signals on relevant models)
- Make cache TTL configurable per tenant via `Tenant.settings["forecast_cache_ttl"]` (default: 60 minutes)
- Expose the TTL setting in the frontend settings UI
- Add a manual refresh button on the forecast page to bypass cache
- Maintain identical query results — pure performance optimization, no behavior changes

**Non-Goals:**
- Caching the liquidity forecast (different data model, separate concern)
- Materialized views or database-level caching (Redis is sufficient and simpler)
- Partial invalidation per contract (full tenant invalidation is simpler and safe given the aggregation)
- Caching at the per-contract level (the forecast is a single aggregated result)

## Decisions

### 1. Cache granularity: full result per query parameter set

Cache the serialized `RevenueForecastResult` per unique combination of `(tenant_id, view, months, quarters, pro_rata, exclude_one_off)`. This is the simplest approach since the result is a single JSON blob.

**Cache key format**: `forecast:{tenant_id}:{query_hash}` where `query_hash` is a hash of the sorted query params. Use a key prefix `forecast:v1:{tenant_id}:` so we can version the cache format.

**Alternative considered**: Cache per-contract rows individually and assemble. Rejected because the forecast includes cross-contract aggregation (period totals, grand total) and invoice matching that depends on the full set.

### 2. Invalidation: wildcard delete on tenant prefix

When any invalidation trigger fires, delete ALL forecast cache keys for that tenant using `cache.delete_pattern(f"forecast:v1:{tenant_id}:*")`. This is safe because:
- There are at most ~10 cached variants per tenant (combinations of view/pro_rata/exclude_one_off)
- Django's Redis backend supports `delete_pattern` (or we use `cache.delete_many` with tracked keys)
- Partial invalidation adds complexity without meaningful benefit

**Note**: Django's built-in `RedisCache` does not support `delete_pattern`. Use `cache.delete_many()` with a tracked key set stored under `forecast:v1:{tenant_id}:_keys`.

### 3. Invalidation triggers via Django signals

Add a `signals.py` in `apps/contracts/` with `@receiver` handlers for:

| Model | Signal | Reason |
|-------|--------|--------|
| `InvoiceRecord` | `post_save`, `post_delete` | Invoice created, status changed, voided, paid |
| `ImportedInvoice` | `post_save` | Extraction status changed to confirmed/sent/paid |
| `Contract` | `post_save` | Status, dates, billing interval changes |
| `ContractItem` | `post_save`, `post_delete` | Item added/removed/modified |
| `ContractItemPrice` | `post_save`, `post_delete` | Price period changes |

Each handler extracts the `tenant_id` from the instance and calls the cache invalidation function. Guards: skip if `created=False` and no relevant fields changed (use `update_fields` when available).

### 4. TTL configuration: Tenant.settings JSON field

Store as `tenant.settings["forecast_cache_ttl"]` (integer, minutes). Default: 60. Read at cache-write time so changes take effect on next cache miss without restart.

Frontend: add a numeric input field in the Settings page (likely under a "Performance" or "General" section in settings).

GraphQL: expose via existing `TenantQuery.settings` pattern; save via a simple mutation or extend existing settings mutations.

### 5. Cache bypass: query parameter + frontend button

Add an optional `refresh: bool = False` parameter to both `revenue_forecast` and `recognition_forecast`. When `True`, skip cache lookup and overwrite the cached value. The frontend "Refresh" button passes `refresh: true`.

### 6. Serialization: JSON via dataclasses_json or manual dict

The `RevenueForecastResult` is a Strawberry type (Python dataclass). Serialize to JSON dict before caching. On cache hit, reconstruct the Strawberry type from the dict. Use a simple `to_dict`/`from_dict` pattern to avoid adding dependencies.

## Risks / Trade-offs

**[Stale data after invalidation miss]** → If a signal handler fails to fire (e.g., bulk update bypassing ORM), users see stale data. Mitigation: the TTL acts as a safety net (max 60 min staleness), and the manual refresh button provides an escape hatch.

**[Cache stampede on invalidation]** → Multiple concurrent requests after cache clear could all compute the forecast simultaneously. Mitigation: acceptable for now — the forecast page typically has 1-2 concurrent users. Could add a lock later if needed.

**[Memory usage]** → A forecast result for ~100 contracts × 13 months is roughly 50-100 KB JSON. With ~10 variants per tenant, that's ~1 MB per tenant. Negligible for Redis.

**[Test complexity]** → Signal-based invalidation needs test coverage. Mitigation: use Django's `LocMemCache` in tests (already configured), write focused signal tests.

## Open Questions

_None — the approach is straightforward given existing infrastructure._
