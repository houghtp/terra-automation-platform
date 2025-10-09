"""
Initialize and register all available SDK-based connectors.
"""

from .registry import register_connector
from .openai_connector import OpenAIConnector, OPENAI_CONFIG
from .firecrawl_connector import FirecrawlConnector, FIRECRAWL_CONFIG
from .anthropic_connector import AnthropicConnector, ANTHROPIC_CONFIG
import structlog

logger = structlog.get_logger(__name__)


def initialize_connectors():
    """Initialize and register all available connectors."""
    try:
        # Register OpenAI connector
        register_connector("openai", OpenAIConnector, OPENAI_CONFIG)
        logger.info("Registered OpenAI connector")

        # Register Firecrawl connector
        register_connector("firecrawl", FirecrawlConnector, FIRECRAWL_CONFIG)
        logger.info("Registered Firecrawl connector")

        # Register Anthropic connector
        register_connector("anthropic", AnthropicConnector, ANTHROPIC_CONFIG)
        logger.info("Registered Anthropic connector")

        logger.info("All SDK-based connectors initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing connectors: {e}")
        raise


# Initialize connectors when module is imported
initialize_connectors()
