"""Test health check endpoints."""

import pytest
from httpx import AsyncClient
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_health():
    """Test basic health endpoint."""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_detailed_health():
    """Test detailed health endpoint."""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test Prometheus metrics endpoint."""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/metrics")
        assert response.status_code == 200

        # Should be Prometheus format
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
