"""Tests for Clockodo provider rate-limit handling and bulk fetches."""
from datetime import date
from unittest.mock import patch

import pytest

from apps.contracts.services.clockodo_provider import ClockodoProvider


@pytest.fixture
def provider():
    return ClockodoProvider({"api_email": "x@example.com", "api_key": "key"})


class TestGetTimeSummaryBulk:
    """Verify the bulk-call optimization: 2 calls per chunk, not 2 per project."""

    def test_single_chunk_one_call_pair(self, provider):
        """50 projects fit into 2 chunks of 25 — 4 entrygroups calls total (not 100)."""
        project_ids = [str(i) for i in range(1, 51)]

        calls = []

        def mock_get(endpoint, params=None):
            calls.append((endpoint, dict(params or {})))
            if endpoint == "entrygroups":
                return {"groups": []}
            return {}

        def mock_get_all_pages(endpoint, key, params=None):
            return []

        with patch.object(provider, "_get", side_effect=mock_get), \
             patch.object(provider, "_get_all_pages", side_effect=mock_get_all_pages), \
             patch("apps.contracts.services.clockodo_provider.time.sleep"):
            provider.get_time_summary(project_ids)

        entrygroup_calls = [c for c in calls if c[0] == "entrygroups"]
        # 2 chunks × 2 groupings (services + month) = 4 calls
        assert len(entrygroup_calls) == 4

    def test_uses_comma_separated_filter(self, provider):
        project_ids = ["100", "200", "300"]

        captured = []

        def mock_get(endpoint, params=None):
            if endpoint == "entrygroups":
                captured.append(params)
            return {"groups": []}

        with patch.object(provider, "_get", side_effect=mock_get), \
             patch.object(provider, "_get_all_pages", return_value=[]), \
             patch("apps.contracts.services.clockodo_provider.time.sleep"):
            provider.get_time_summary(project_ids)

        # All entrygroups calls should use a comma-separated projects_id filter
        assert len(captured) == 2  # 1 chunk × 2 groupings
        for params in captured:
            assert params["filter[projects_id]"] == "100,200,300"

    def test_chunk_boundaries(self, provider):
        # 60 projects → 3 chunks of 25, 25, 10
        project_ids = [str(i) for i in range(1, 61)]

        captured = []

        def mock_get(endpoint, params=None):
            if endpoint == "entrygroups":
                captured.append(params["filter[projects_id]"])
            return {"groups": []}

        with patch.object(provider, "_get", side_effect=mock_get), \
             patch.object(provider, "_get_all_pages", return_value=[]), \
             patch("apps.contracts.services.clockodo_provider.time.sleep"):
            provider.get_time_summary(project_ids)

        # 3 chunks × 2 calls = 6 total
        assert len(captured) == 6
        # Each filter string appears twice (services + month grouping)
        sizes = sorted(f.count(",") + 1 for f in captured)
        assert sizes == [10, 10, 25, 25, 25, 25]

    def test_empty_project_ids_short_circuits(self, provider):
        result = provider.get_time_summary([])
        assert result.total_hours == 0
        assert result.total_revenue == 0

    def test_aggregates_groups_across_chunks(self, provider):
        project_ids = [str(i) for i in range(1, 31)]  # 2 chunks

        # Order of calls per chunk: services, month. Two chunks → 4 calls.
        responses = iter([
            # Chunk 1 services
            {"groups": [{"group": "1", "duration": 3600, "revenue": 100, "name": "Dev"}]},
            # Chunk 1 month
            {"groups": [{"group": "2026-04", "duration": 3600, "revenue": 100}]},
            # Chunk 2 services
            {"groups": [{"group": "1", "duration": 7200, "revenue": 250, "name": "Dev"}]},
            # Chunk 2 month
            {"groups": [{"group": "2026-04", "duration": 7200, "revenue": 250}]},
        ])

        def mock_get(endpoint, params=None):
            return next(responses) if endpoint == "entrygroups" else {}

        with patch.object(provider, "_get", side_effect=mock_get), \
             patch.object(provider, "_get_all_pages", return_value=[{"id": 1, "name": "Dev"}]), \
             patch("apps.contracts.services.clockodo_provider.time.sleep"):
            summary = provider.get_time_summary(project_ids)

        # Totals derived from month_data sum across both chunks: 1h + 2h = 3h
        assert summary.total_hours == 3.0
        assert summary.total_revenue == 350.0


class TestRequestBackoff:
    def test_429_uses_retry_after_header_when_present(self, provider):
        sleep_calls = []
        responses = [
            type("R", (), {
                "status_code": 429,
                "headers": {"Retry-After": "5"},
                "json": lambda self: {"error": "rate limited"},
                "request": None,
                "text": "",
            })(),
            type("R", (), {
                "status_code": 200,
                "headers": {},
                "json": lambda self: {"ok": True},
            })(),
        ]
        response_iter = iter(responses)

        def mock_request(*a, **kw):
            return next(response_iter)

        with patch("apps.contracts.services.clockodo_provider.httpx.request",
                   side_effect=mock_request), \
             patch("apps.contracts.services.clockodo_provider.time.sleep",
                   side_effect=sleep_calls.append):
            provider._request("GET", "users")

        # First retry should respect Retry-After: 5 (not the 30s default)
        assert sleep_calls == [5]

    def test_429_uses_30s_initial_backoff_without_retry_after(self, provider):
        sleep_calls = []

        def make_response(status):
            return type("R", (), {
                "status_code": status,
                "headers": {},
                "json": lambda self: {} if status < 400 else {"error": "x"},
                "request": None,
                "text": "",
            })()

        responses = iter([make_response(429), make_response(429), make_response(200)])

        with patch("apps.contracts.services.clockodo_provider.httpx.request",
                   side_effect=lambda *a, **kw: next(responses)), \
             patch("apps.contracts.services.clockodo_provider.time.sleep",
                   side_effect=sleep_calls.append):
            provider._request("GET", "users")

        # 30s initial, then doubled to 60s on second retry
        assert sleep_calls == [30, 60]
