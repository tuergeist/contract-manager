"""Tests for the GitHub latest-version check used by the update banner."""
from unittest.mock import Mock, patch

import httpx
import pytest
from django.core.cache import cache

from apps.core.version_check import (
    CACHE_KEY,
    get_latest_version,
    parse_version,
)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.delete(CACHE_KEY)
    yield
    cache.delete(CACHE_KEY)


class TestParseVersion:
    def test_plain_semver(self):
        assert parse_version("2.34.12") == (2, 34, 12)

    def test_strips_v_prefix(self):
        assert parse_version("v1.0.0") == (1, 0, 0)

    def test_rejects_non_semver(self):
        assert parse_version("dev") is None
        assert parse_version("2.1") is None
        assert parse_version("2.1.0-rc1") is None
        assert parse_version("") is None
        assert parse_version(None) is None


def _tags_response(names):
    response = Mock()
    response.is_success = True
    response.status_code = 200
    response.json.return_value = [{"name": n} for n in names]
    return response


@pytest.mark.django_db
class TestGetLatestVersion:
    @patch("apps.core.version_check.httpx.get")
    def test_returns_highest_semver_tag(self, mock_get):
        # Deliberately out of order + noise to prove we pick the max semver.
        mock_get.return_value = _tags_response(
            ["2.34.9", "2.34.12", "2.9.0", "not-a-tag", "2.34.11"]
        )
        assert get_latest_version() == "2.34.12"

    @patch("apps.core.version_check.httpx.get")
    def test_caches_result(self, mock_get):
        mock_get.return_value = _tags_response(["1.0.0"])
        assert get_latest_version() == "1.0.0"
        # Second call must hit the cache, not GitHub.
        assert get_latest_version() == "1.0.0"
        mock_get.assert_called_once()

    @patch("apps.core.version_check.httpx.get")
    def test_network_error_returns_none(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("boom")
        assert get_latest_version() is None

    @patch("apps.core.version_check.httpx.get")
    def test_http_error_returns_none(self, mock_get):
        response = Mock()
        response.is_success = False
        response.status_code = 403
        mock_get.return_value = response
        assert get_latest_version() is None

    @patch("apps.core.version_check.httpx.get")
    def test_failed_lookup_is_cached_as_none(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("boom")
        assert get_latest_version() is None
        # Cached empty marker → no second request.
        assert get_latest_version() is None
        mock_get.assert_called_once()

    @patch("apps.core.version_check.httpx.get")
    def test_token_added_when_configured(self, mock_get, settings):
        settings.GITHUB_RELEASE_TOKEN = "secret"
        mock_get.return_value = _tags_response(["1.0.0"])
        get_latest_version()
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer secret"
