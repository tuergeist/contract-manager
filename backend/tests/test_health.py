"""Basic health check tests."""
import pytest


def test_health_endpoint(client):
    """Test the health endpoint returns ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
