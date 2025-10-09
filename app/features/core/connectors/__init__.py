"""
Shared connector infrastructure for SDK-based integrations.
"""

from .base import BaseConnector, ConnectorResult, ConnectorError, ConnectorType
from .registry import ConnectorRegistry, get_connector
from .utils import ConnectorAuth, RateLimiter, ConnectorConfig

# Import SDK connectors to register them
from . import sdk_connectors

__all__ = [
    "BaseConnector",
    "ConnectorResult",
    "ConnectorError",
    "ConnectorType",
    "ConnectorRegistry",
    "get_connector",
    "ConnectorAuth",
    "RateLimiter",
    "ConnectorConfig"
]
