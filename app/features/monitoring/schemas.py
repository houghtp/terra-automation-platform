"""
Pydantic schemas for monitoring endpoints.
"""
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    version: str
    environment: str
    checks: Dict[str, Any]


class MetricsInfo(BaseModel):
    """Metrics endpoint information."""

    endpoint: str
    format: str
    description: str
    content_type: str


__all__ = ["HealthStatus", "MetricsInfo"]
