"""Tests for version and license endpoints."""
import json
from unittest.mock import patch, mock_open

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestVersionEndpoint:
    def test_returns_dev_when_no_file(self, client):
        with patch("apps.core.version_views.BUILD_INFO_PATH", "/nonexistent/path.json"):
            response = client.get("/api/version/")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "dev"
        assert data["buildDate"] == ""

    def test_returns_build_info(self, client):
        build_info = json.dumps({"version": "1.2.3", "buildDate": "2026-02-16T10:00:00Z"})
        with patch("builtins.open", mock_open(read_data=build_info)):
            with patch("apps.core.version_views.BUILD_INFO_PATH", "/app/build-info.json"):
                response = client.get("/api/version/")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.2.3"
        assert data["buildDate"] == "2026-02-16T10:00:00Z"

    def test_no_auth_required(self, client):
        """Version endpoint should be accessible without authentication."""
        response = client.get("/api/version/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestBackendLicensesEndpoint:
    def test_returns_empty_array_when_no_file(self, client):
        with patch("apps.core.version_views.LICENSES_BACKEND_PATH", "/nonexistent/path.json"):
            response = client.get("/api/version/licenses/")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_license_data(self, client):
        licenses = json.dumps([
            {"Name": "Django", "Version": "5.0", "License": "BSD-3-Clause"},
            {"Name": "strawberry-graphql", "Version": "0.220.0", "License": "MIT"},
        ])
        with patch("builtins.open", mock_open(read_data=licenses)):
            with patch("apps.core.version_views.LICENSES_BACKEND_PATH", "/app/licenses-backend.json"):
                response = client.get("/api/version/licenses/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["Name"] == "Django"

    def test_no_auth_required(self, client):
        """Licenses endpoint should be accessible without authentication."""
        response = client.get("/api/version/licenses/")
        assert response.status_code == 200
