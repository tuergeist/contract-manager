"""Tests for forecast caching infrastructure."""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.contracts.forecast_cache import (
    _build_cache_key,
    dict_to_forecast_result,
    forecast_result_to_dict,
    get_cache_ttl,
    get_cached_forecast,
    invalidate_tenant_forecast,
    set_cached_forecast,
)
from apps.contracts.schema import (
    ContractRevenueRow,
    RevenueMonthData,
    RevenueForecastResult,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


def _make_result() -> RevenueForecastResult:
    """Build a sample RevenueForecastResult for testing."""
    return RevenueForecastResult(
        month_columns=["2026-01", "2026-02"],
        monthly_totals=[
            RevenueMonthData(month="2026-01", amount=Decimal("1000.00"), invoice_status="paid"),
            RevenueMonthData(month="2026-02", amount=Decimal("2000.50"), invoice_status=None),
        ],
        contracts=[
            ContractRevenueRow(
                contract_id=1,
                contract_name="Contract A",
                customer_id=10,
                customer_name="Customer X",
                months=[
                    RevenueMonthData(month="2026-01", amount=Decimal("500.00"), invoice_status="sent"),
                    RevenueMonthData(month="2026-02", amount=Decimal("750.25"), invoice_status=None),
                ],
                total=Decimal("1250.25"),
            ),
        ],
        grand_total=Decimal("3000.50"),
        error=None,
    )


class TestCacheKeyGeneration:
    def test_deterministic_key(self):
        key1 = _build_cache_key("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        key2 = _build_cache_key("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        assert key1 == key2

    def test_different_params_produce_different_keys(self):
        key1 = _build_cache_key("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        key2 = _build_cache_key("forecast", 1, view="quarterly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        assert key1 != key2

    def test_different_tenants_produce_different_keys(self):
        key1 = _build_cache_key("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        key2 = _build_cache_key("forecast", 2, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        assert key1 != key2

    def test_different_prefixes_produce_different_keys(self):
        key1 = _build_cache_key("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        key2 = _build_cache_key("recognition", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        assert key1 != key2

    def test_key_format(self):
        key = _build_cache_key("forecast", 42, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False)
        assert key.startswith("forecast:v1:42:")


class TestSerialization:
    def test_round_trip(self):
        original = _make_result()
        data = forecast_result_to_dict(original)
        restored = dict_to_forecast_result(data)

        assert restored.month_columns == original.month_columns
        assert restored.grand_total == original.grand_total
        assert restored.error == original.error
        assert len(restored.monthly_totals) == len(original.monthly_totals)
        assert len(restored.contracts) == len(original.contracts)

        # Check monthly totals
        assert restored.monthly_totals[0].month == "2026-01"
        assert restored.monthly_totals[0].amount == Decimal("1000.00")
        assert restored.monthly_totals[0].invoice_status == "paid"
        assert restored.monthly_totals[1].invoice_status is None

        # Check contract data
        c = restored.contracts[0]
        assert c.contract_id == 1
        assert c.contract_name == "Contract A"
        assert c.total == Decimal("1250.25")
        assert c.months[0].invoice_status == "sent"

    def test_serialization_produces_json_safe_dict(self):
        result = _make_result()
        data = forecast_result_to_dict(result)
        # All Decimals should be strings
        assert isinstance(data["grand_total"], str)
        assert isinstance(data["monthly_totals"][0]["amount"], str)
        assert isinstance(data["contracts"][0]["total"], str)

    def test_error_field_preserved(self):
        result = RevenueForecastResult(
            month_columns=[], monthly_totals=[], contracts=[],
            grand_total=Decimal("0"), error="Something went wrong",
        )
        data = forecast_result_to_dict(result)
        restored = dict_to_forecast_result(data)
        assert restored.error == "Something went wrong"


class TestCacheTTL:
    def test_default_ttl(self):
        class FakeTenant:
            settings = {}
        assert get_cache_ttl(FakeTenant()) == 60 * 60  # 60 minutes in seconds

    def test_custom_ttl(self):
        class FakeTenant:
            settings = {"forecast_cache_ttl": 30}
        assert get_cache_ttl(FakeTenant()) == 30 * 60

    def test_minimum_ttl(self):
        class FakeTenant:
            settings = {"forecast_cache_ttl": 0}
        assert get_cache_ttl(FakeTenant()) == 1 * 60  # Minimum 1 minute

    def test_none_settings(self):
        class FakeTenant:
            settings = None
        assert get_cache_ttl(FakeTenant()) == 60 * 60

    def test_invalid_ttl_value(self):
        class FakeTenant:
            settings = {"forecast_cache_ttl": "invalid"}
        assert get_cache_ttl(FakeTenant()) == 60 * 60


class TestCacheHitMiss:
    def test_miss_returns_none(self):
        result = get_cached_forecast(
            "forecast", 1,
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )
        assert result is None

    def test_set_then_get(self):
        class FakeTenant:
            id = 1
            settings = {"forecast_cache_ttl": 60}

        data = {"month_columns": ["2026-01"], "grand_total": "100"}
        set_cached_forecast(
            "forecast", FakeTenant(), data,
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )

        result = get_cached_forecast(
            "forecast", 1,
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )
        assert result == data

    def test_different_params_are_separate(self):
        class FakeTenant:
            id = 1
            settings = {}

        data_monthly = {"view": "monthly"}
        data_quarterly = {"view": "quarterly"}

        set_cached_forecast(
            "forecast", FakeTenant(), data_monthly,
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )
        set_cached_forecast(
            "forecast", FakeTenant(), data_quarterly,
            view="quarterly", months=None, quarters=6, pro_rata=False, exclude_one_off=False,
        )

        result = get_cached_forecast(
            "forecast", 1,
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )
        assert result == data_monthly


class TestInvalidation:
    def test_invalidate_clears_all_entries(self):
        class FakeTenant:
            id = 1
            settings = {}

        set_cached_forecast(
            "forecast", FakeTenant(), {"a": 1},
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )
        set_cached_forecast(
            "forecast", FakeTenant(), {"b": 2},
            view="quarterly", months=None, quarters=6, pro_rata=False, exclude_one_off=False,
        )
        set_cached_forecast(
            "recognition", FakeTenant(), {"c": 3},
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )

        invalidate_tenant_forecast(1)

        assert get_cached_forecast("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False) is None
        assert get_cached_forecast("forecast", 1, view="quarterly", months=None, quarters=6, pro_rata=False, exclude_one_off=False) is None
        assert get_cached_forecast("recognition", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False) is None

    def test_invalidate_does_not_affect_other_tenants(self):
        class FakeTenant1:
            id = 1
            settings = {}

        class FakeTenant2:
            id = 2
            settings = {}

        set_cached_forecast(
            "forecast", FakeTenant1(), {"tenant": 1},
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )
        set_cached_forecast(
            "forecast", FakeTenant2(), {"tenant": 2},
            view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False,
        )

        invalidate_tenant_forecast(1)

        assert get_cached_forecast("forecast", 1, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False) is None
        assert get_cached_forecast("forecast", 2, view="monthly", months=13, quarters=None, pro_rata=False, exclude_one_off=False) == {"tenant": 2}
