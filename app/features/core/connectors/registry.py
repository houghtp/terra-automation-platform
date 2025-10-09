"""
Connector registry for managing and instantiating connectors.
"""

from typing import Dict, Type, Optional, List, Any
from .base import BaseConnector, ConnectorConfig, ConnectorType
import structlog

logger = structlog.get_logger(__name__)


class ConnectorRegistry:
    """
    Registry for managing available connectors.

    This provides a central place to register and instantiate connectors,
    making it easy to add new connectors and manage their lifecycle.
    """

    def __init__(self):
        self._connectors: Dict[str, Type[BaseConnector]] = {}
        self._configs: Dict[str, ConnectorConfig] = {}

    def register(
        self,
        name: str,
        connector_class: Type[BaseConnector],
        config: ConnectorConfig
    ) -> None:
        """
        Register a new connector.

        Args:
            name: Connector name (unique identifier)
            connector_class: Connector class to instantiate
            config: Default configuration for the connector
        """
        if name in self._connectors:
            logger.warning(f"Overriding existing connector: {name}")

        self._connectors[name] = connector_class
        self._configs[name] = config

        logger.info(f"Registered connector: {name} ({connector_class.__name__})")

    def unregister(self, name: str) -> None:
        """
        Unregister a connector.

        Args:
            name: Connector name to remove
        """
        if name in self._connectors:
            del self._connectors[name]
            del self._configs[name]
            logger.info(f"Unregistered connector: {name}")
        else:
            logger.warning(f"Connector not found for unregistration: {name}")

    def get_connector_names(self) -> List[str]:
        """Get list of all registered connector names."""
        return list(self._connectors.keys())

    def get_connectors_by_type(self, connector_type: ConnectorType) -> List[str]:
        """
        Get connector names by type.

        Args:
            connector_type: Type of connectors to filter by

        Returns:
            List of connector names matching the type
        """
        return [
            name for name, config in self._configs.items()
            if config.connector_type == connector_type
        ]

    def get_connector_config(self, name: str) -> Optional[ConnectorConfig]:
        """
        Get configuration for a connector.

        Args:
            name: Connector name

        Returns:
            Connector configuration or None if not found
        """
        return self._configs.get(name)

    def create_connector(
        self,
        name: str,
        credentials: Dict[str, Any],
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> BaseConnector:
        """
        Create a connector instance.

        Args:
            name: Connector name
            credentials: Authentication credentials
            config_overrides: Configuration overrides

        Returns:
            Configured connector instance

        Raises:
            ValueError: If connector is not registered
        """
        if name not in self._connectors:
            raise ValueError(f"Connector not registered: {name}")

        connector_class = self._connectors[name]
        config = self._configs[name].copy()

        # Apply configuration overrides
        if config_overrides:
            for key, value in config_overrides.items():
                setattr(config, key, value)

        return connector_class(config=config, credentials=credentials)

    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get information about all registered connectors.

        Returns:
            Dictionary with connector registry information
        """
        connectors_info = {}

        for name, config in self._configs.items():
            connector_class = self._connectors[name]

            connectors_info[name] = {
                "name": config.name,
                "display_name": getattr(config, 'display_name', name),
                "description": getattr(config, 'description', ''),
                "type": config.connector_type.value,
                "version": config.version,
                "class": f"{connector_class.__module__}.{connector_class.__name__}",
                "supports_streaming": getattr(config, 'supports_streaming', False),
                "supports_batch": getattr(config, 'supports_batch', False),
                "rate_limit_per_minute": config.rate_limit_per_minute,
                "api_base_url": getattr(config, 'api_base_url', None)
            }

        return {
            "total_connectors": len(connectors_info),
            "connectors": connectors_info,
            "types": {
                connector_type.value: len(self.get_connectors_by_type(connector_type))
                for connector_type in ConnectorType
            }
        }


# Global registry instance
_registry = ConnectorRegistry()


def register_connector(
    name: str,
    connector_class: Type[BaseConnector],
    config: ConnectorConfig
) -> None:
    """
    Register a connector in the global registry.

    Args:
        name: Connector name
        connector_class: Connector class
        config: Connector configuration
    """
    _registry.register(name, connector_class, config)


def get_connector(
    name: str,
    credentials: Dict[str, Any],
    config_overrides: Optional[Dict[str, Any]] = None
) -> BaseConnector:
    """
    Create a connector instance from the global registry.

    Args:
        name: Connector name
        credentials: Authentication credentials
        config_overrides: Configuration overrides

    Returns:
        Configured connector instance
    """
    return _registry.create_connector(name, credentials, config_overrides)


def get_available_connectors() -> List[str]:
    """Get list of all available connector names."""
    return _registry.get_connector_names()


def get_connectors_by_type(connector_type: ConnectorType) -> List[str]:
    """Get connector names by type."""
    return _registry.get_connectors_by_type(connector_type)


def get_connector_config(name: str) -> Optional[ConnectorConfig]:
    """Get configuration for a connector."""
    return _registry.get_connector_config(name)


def get_registry_info() -> Dict[str, Any]:
    """Get information about the connector registry."""
    return _registry.get_registry_info()


# Auto-register standard connectors
def _register_standard_connectors():
    """Register all standard connectors."""
    from .openai_connector import OpenAIConnector, create_openai_connector
    from .anthropic_connector import AnthropicConnector, create_anthropic_connector
    from .firecrawl_connector import FirecrawlConnector, create_firecrawl_connector
    from .serpapi_connector import SerpAPIConnector, create_serpapi_connector
    from .scrapingdog_connector import ScrapingDogConnector, create_scrapingdog_connector
    from .scrapingbee_connector import ScrapingBeeConnector, create_scrapingbee_connector

    # Register connectors with factory functions
    connectors_to_register = [
        ("openai", OpenAIConnector, ConnectorConfig(
            name="openai",
            display_name="OpenAI",
            description="OpenAI GPT models for text generation and embeddings",
            connector_type=ConnectorType.AI,
            version="1.0.0",
            rate_limit_per_minute=60
        )),
        ("anthropic", AnthropicConnector, ConnectorConfig(
            name="anthropic",
            display_name="Anthropic Claude",
            description="Anthropic Claude models for advanced text generation",
            connector_type=ConnectorType.AI,
            version="1.0.0",
            rate_limit_per_minute=60
        )),
        ("firecrawl", FirecrawlConnector, ConnectorConfig(
            name="firecrawl",
            display_name="Firecrawl",
            description="Web scraping and crawling service",
            connector_type=ConnectorType.DATA,
            version="1.0.0",
            rate_limit_per_minute=120
        )),
        ("serpapi", SerpAPIConnector, ConnectorConfig(
            name="serpapi",
            display_name="SerpAPI",
            description="Google search results via SerpAPI",
            connector_type=ConnectorType.DATA,
            version="1.0.0",
            rate_limit_per_minute=100
        )),
        ("scrapingdog", ScrapingDogConnector, ConnectorConfig(
            name="scrapingdog",
            display_name="ScrapingDog",
            description="Web scraping and Google search via ScrapingDog",
            connector_type=ConnectorType.DATA,
            version="1.0.0",
            rate_limit_per_minute=100
        )),
        ("scrapingbee", ScrapingBeeConnector, ConnectorConfig(
            name="scrapingbee",
            display_name="ScrapingBee",
            description="Web scraping and Google search via ScrapingBee",
            connector_type=ConnectorType.DATA,
            version="1.0.0",
            rate_limit_per_minute=100
        ))
    ]

    for name, connector_class, config in connectors_to_register:
        register_connector(name, connector_class, config)

# Auto-register on import
_register_standard_connectors()
