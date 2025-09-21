import os
import logging

def setup_logging():
    """
    Configure logging for the application.
    Uses structured logging with JSON format in production.
    """
    # Import structured logging setup
    try:
        from .structured_logging import configure_logging
        # Use structured logging if available with database logging enabled
        configure_logging(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            enable_database_logging=True
        )
        return
    except ImportError:
        # Fallback to basic logging if structlog is not available
        pass

    # Fallback basic logging setup
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[logging.StreamHandler()]
    )
