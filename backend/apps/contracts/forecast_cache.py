"""Redis caching for revenue and recognition forecast queries."""
import hashlib
import json
import logging
from decimal import Decimal
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL_MINUTES = 60


def _build_cache_key(
    prefix: str,
    tenant_id: int,
    view: str,
    months: Optional[int],
    quarters: Optional[int],
    pro_rata: bool,
    exclude_one_off: bool,
) -> str:
    """Build a deterministic cache key from query parameters."""
    params = json.dumps(
        {
            "view": view,
            "months": months,
            "quarters": quarters,
            "pro_rata": pro_rata,
            "exclude_one_off": exclude_one_off,
        },
        sort_keys=True,
    )
    query_hash = hashlib.md5(params.encode()).hexdigest()[:12]
    return f"{prefix}:v1:{tenant_id}:{query_hash}"


def _keys_tracker_key(prefix: str, tenant_id: int) -> str:
    """Key that tracks all active cache keys for a tenant."""
    return f"{prefix}:v1:{tenant_id}:_keys"


def get_cache_ttl(tenant) -> int:
    """Read cache TTL from tenant settings (in seconds). Default: 60 minutes."""
    minutes = (tenant.settings or {}).get(
        "forecast_cache_ttl", DEFAULT_CACHE_TTL_MINUTES
    )
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        minutes = DEFAULT_CACHE_TTL_MINUTES
    return max(minutes, 1) * 60  # Convert to seconds


def get_cached_forecast(
    prefix: str,
    tenant_id: int,
    **params,
) -> Optional[dict]:
    """Retrieve a cached forecast result. Returns None on miss."""
    key = _build_cache_key(prefix, tenant_id, **params)
    data = cache.get(key)
    if data is not None:
        logger.debug("Forecast cache hit: %s", key)
    return data


def set_cached_forecast(
    prefix: str,
    tenant,
    result_dict: dict,
    **params,
) -> None:
    """Store a forecast result in cache with tenant-specific TTL."""
    key = _build_cache_key(prefix, tenant.id, **params)
    ttl = get_cache_ttl(tenant)

    cache.set(key, result_dict, ttl)

    # Track this key so we can invalidate all keys for a tenant
    tracker_key = _keys_tracker_key(prefix, tenant.id)
    tracked = cache.get(tracker_key) or []
    if key not in tracked:
        tracked.append(key)
        # Store tracker with a long TTL (longer than any individual entry)
        cache.set(tracker_key, tracked, ttl + 3600)

    logger.debug("Forecast cached: %s (TTL=%ds)", key, ttl)


def invalidate_tenant_forecast(tenant_id: int) -> None:
    """Delete all cached forecast entries for a tenant."""
    deleted = 0
    for prefix in ("forecast", "recognition"):
        tracker_key = _keys_tracker_key(prefix, tenant_id)
        tracked = cache.get(tracker_key) or []
        if tracked:
            cache.delete_many(tracked)
            deleted += len(tracked)
        cache.delete(tracker_key)

    if deleted:
        logger.info(
            "Invalidated %d cached forecast entries for tenant %s",
            deleted,
            tenant_id,
        )


# ----------------------------------------------------------------
# Serialization helpers
# ----------------------------------------------------------------


def forecast_result_to_dict(result) -> dict:
    """Serialize a RevenueForecastResult to a JSON-safe dict."""
    return {
        "month_columns": result.month_columns,
        "monthly_totals": [
            {
                "month": mt.month,
                "amount": str(mt.amount),
                "invoice_status": mt.invoice_status,
            }
            for mt in result.monthly_totals
        ],
        "contracts": [
            {
                "contract_id": c.contract_id,
                "contract_name": c.contract_name,
                "customer_id": c.customer_id,
                "customer_name": c.customer_name,
                "months": [
                    {
                        "month": m.month,
                        "amount": str(m.amount),
                        "invoice_status": m.invoice_status,
                    }
                    for m in c.months
                ],
                "total": str(c.total),
            }
            for c in result.contracts
        ],
        "grand_total": str(result.grand_total),
        "error": result.error,
    }


def dict_to_forecast_result(data: dict):
    """Deserialize a dict back to a RevenueForecastResult."""
    from apps.contracts.schema import (
        ContractRevenueRow,
        RevenueMonthData,
        RevenueForecastResult,
    )

    return RevenueForecastResult(
        month_columns=data["month_columns"],
        monthly_totals=[
            RevenueMonthData(
                month=mt["month"],
                amount=Decimal(mt["amount"]),
                invoice_status=mt.get("invoice_status"),
            )
            for mt in data["monthly_totals"]
        ],
        contracts=[
            ContractRevenueRow(
                contract_id=c["contract_id"],
                contract_name=c["contract_name"],
                customer_id=c["customer_id"],
                customer_name=c["customer_name"],
                months=[
                    RevenueMonthData(
                        month=m["month"],
                        amount=Decimal(m["amount"]),
                        invoice_status=m.get("invoice_status"),
                    )
                    for m in c["months"]
                ],
                total=Decimal(c["total"]),
            )
            for c in data["contracts"]
        ],
        grand_total=Decimal(data["grand_total"]),
        error=data.get("error"),
    )
