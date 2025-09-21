"""
Structured logging configuration for FastAPI applications.
Provides JSON logging, request IDs, security event tracking, and log aggregation support.
"""
import logging
import json
import sys
import os
import traceback
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager

import structlog
from structlog.stdlib import LoggerFactory


class AsyncDatabaseLogHandler(logging.Handler):
    """
    Async database handler for critical logs with tenant isolation.

    Only stores WARNING level and above to avoid overwhelming database.
    Provides real-time queryable logs for tenant-specific log viewing.
    """

    def __init__(self, level=logging.WARNING):
        super().__init__(level)
        self._loop = None
        self._session_factory = None

    def _get_or_create_loop(self):
        """Get current event loop or create new one if needed."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def emit(self, record):
        """Emit log record to database asynchronously."""
        if not self._should_log_to_db(record):
            return

        try:
            loop = self._get_or_create_loop()
            if loop.is_running():
                # If we're in an async context, schedule the write
                asyncio.create_task(self._async_emit(record))
            else:
                # If we're not in an async context, run it
                loop.run_until_complete(self._async_emit(record))
        except Exception:
            # Failsafe - don't let logging errors break the application
            pass

    def _should_log_to_db(self, record) -> bool:
        """Determine if this log should be stored in database."""
        # Only store WARNING level and above
        if record.levelno < logging.WARNING:
            return False

        # Skip certain noisy loggers
        skip_loggers = ["uvicorn", "sqlalchemy", "httpx"]
        if any(record.name.startswith(skip) for skip in skip_loggers):
            return False

        return True

    async def _async_emit(self, record):
        """Actually write the log to database."""
        from ..administration.logs.models import ApplicationLog
        from .database import get_db

        try:
            async for session in get_db():
                # Extract context from record
                tenant_id = getattr(record, 'tenant_id', 'global')
                request_id = getattr(record, 'request_id', None)
                user_id = getattr(record, 'user_id', None)
                endpoint = getattr(record, 'endpoint', None)
                method = getattr(record, 'method', None)
                ip_address = getattr(record, 'ip_address', None)
                user_agent = getattr(record, 'user_agent', None)

                # Handle exception details
                exception_type = None
                exception_message = None
                stack_trace = None

                if record.exc_info:
                    exc_type, exc_value, exc_traceback = record.exc_info
                    exception_type = exc_type.__name__ if exc_type else None
                    exception_message = str(exc_value) if exc_value else None
                    stack_trace = ''.join(traceback.format_exception(
                        exc_type, exc_value, exc_traceback
                    )) if exc_traceback else None

                # Create log entry
                log_entry = ApplicationLog(
                    tenant_id=tenant_id,
                    request_id=request_id,
                    level=record.levelname,
                    logger_name=record.name,
                    timestamp=datetime.fromtimestamp(record.created),
                    message=record.getMessage(),
                    exception_type=exception_type,
                    exception_message=exception_message,
                    stack_trace=stack_trace,
                    user_id=user_id,
                    endpoint=endpoint,
                    method=method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    extra_data=getattr(record, 'extra_data', None)
                )

                session.add(log_entry)
                await session.commit()
                break  # Exit the async generator loop

        except Exception:
            # Silently fail - logging errors shouldn't break the app
            pass


def configure_logging(
    level: str = "INFO",
    format_type: str = "console",  # "console" or "json"
    enable_json: bool = False,
    enable_request_id: bool = True,
    enable_database_logging: bool = True
):
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ('json', 'console', 'plain')
        enable_json: Force enable/disable JSON logging
        enable_request_id: Whether to include request IDs in logs
    """

    # Get configuration from environment
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    if format_type is None:
        format_type = os.getenv("LOG_FORMAT", "auto")

    if enable_json is None:
        # Auto-detect: use JSON in production, console in development
        environment = os.getenv("ENVIRONMENT", "development").lower()
        enable_json = environment == "production"

    # Override format_type based on enable_json if format is auto
    if format_type == "auto":
        format_type = "json" if enable_json else "console"

    # Configure processors chain
    processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add request ID processor if enabled
    if enable_request_id:
        processors.append(add_request_id)

    # Add tenant context processor
    processors.append(add_tenant_context)

    # Configure final formatting
    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
        wrapper_processor = structlog.stdlib.ProcessorFormatter.wrap_for_formatter
    else:
        # Console or plain formatting
        if format_type == "console":
            processors.append(
                structlog.dev.ConsoleRenderer(colors=True)
            )
        else:
            processors.append(
                structlog.processors.JSONRenderer()
            )
        wrapper_processor = structlog.stdlib.ProcessorFormatter.wrap_for_formatter

    # Configure structlog
    structlog.configure(
        processors=processors[:-1] + [wrapper_processor],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging with both console and file handlers
    console_handler = logging.StreamHandler(sys.stdout)

    # Add file handler for persistence
    from .config import get_settings
    settings = get_settings()
    file_handler = logging.FileHandler(settings.LOG_FILE)

    # Add database handler for critical logs (if enabled)
    db_handler = None
    if enable_database_logging:
        db_handler = AsyncDatabaseLogHandler(level=logging.WARNING)

    # Create processor formatter for stdlib integration
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=processors[-1],  # Use the final renderer
        foreign_pre_chain=processors[:-1],  # All processors except the final renderer
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Set up root logger with handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    if db_handler:
        root_logger.addHandler(db_handler)
    root_logger.setLevel(getattr(logging, level))

    # Configure specific loggers
    _configure_application_loggers(level)

    # Log the configuration
    logger = structlog.get_logger(__name__)
    logger.info(
        "Structured logging initialized",
        log_level=level,
        format_type=format_type,
        json_enabled=enable_json,
        request_id_enabled=enable_request_id
    )


def _configure_application_loggers(level: str):
    """Configure specific application and third-party loggers."""

    # Application loggers
    app_loggers = [
        "app",
        "app.auth",
        "app.core",
        "app.middleware",
        "app.monitoring",
    ]

    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level))

    # Third-party loggers (usually more verbose)
    third_party_loggers = {
        "uvicorn": "INFO",
        "uvicorn.access": "INFO",
        "sqlalchemy.engine": "WARNING",
        "sqlalchemy.pool": "WARNING",
        "httpx": "WARNING",
        "azure": "WARNING",
        "boto3": "WARNING",
        "botocore": "WARNING",
    }

    for logger_name, logger_level in third_party_loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, logger_level))


def add_request_id(logger, method_name, event_dict):
    """Processor to add request ID to log records."""
    try:
        from app.middleware.request_id import request_id_ctx_var
        request_id = request_id_ctx_var.get(None)
        if request_id:
            event_dict["request_id"] = request_id
    except Exception:
        # Fail silently if request ID middleware is not available
        pass

    return event_dict


def add_tenant_context(logger, method_name, event_dict):
    """Processor to add tenant context to log records."""
    try:
        from app.middleware.tenant import tenant_ctx_var
        tenant_id = tenant_ctx_var.get(None)
        if tenant_id:
            event_dict["tenant_id"] = tenant_id
    except Exception:
        # Fail silently if tenant middleware is not available
        pass

    return event_dict


class SecurityLogger:
    """
    Specialized logger for security events.
    Provides structured security event logging with severity levels.
    """

    def __init__(self):
        self.logger = structlog.get_logger("security")

    def log_auth_attempt(self, username: str, success: bool, ip_address: str,
                        user_agent: str = None, tenant_id: str = None, **kwargs):
        """Log authentication attempt."""
        event_data = {
            "event_type": "auth_attempt",
            "username": username,
            "success": success,
            "ip_address": ip_address,
            "severity": "info" if success else "warning",
            **kwargs
        }

        if user_agent:
            event_data["user_agent"] = user_agent
        if tenant_id:
            event_data["tenant_id"] = tenant_id

        if success:
            self.logger.info("Authentication successful", **event_data)
        else:
            self.logger.warning("Authentication failed", **event_data)

    def log_rate_limit_exceeded(self, rule_scope: str, limit: int, window: int,
                               ip_address: str, tenant_id: str = None, **kwargs):
        """Log rate limit exceeded event."""
        self.logger.warning(
            "Rate limit exceeded",
            event_type="rate_limit_exceeded",
            rule_scope=rule_scope,
            limit=limit,
            window_seconds=window,
            ip_address=ip_address,
            tenant_id=tenant_id,
            severity="warning",
            **kwargs
        )

    def log_suspicious_activity(self, activity_type: str, description: str,
                               ip_address: str, severity: str = "medium",
                               tenant_id: str = None, **kwargs):
        """Log suspicious activity."""
        self.logger.warning(
            "Suspicious activity detected",
            event_type="suspicious_activity",
            activity_type=activity_type,
            description=description,
            ip_address=ip_address,
            severity=severity,
            tenant_id=tenant_id,
            **kwargs
        )

    def log_access_violation(self, resource: str, action: str, user_id: str = None,
                           ip_address: str = None, tenant_id: str = None, **kwargs):
        """Log access violation attempt."""
        self.logger.error(
            "Access violation attempted",
            event_type="access_violation",
            resource=resource,
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            tenant_id=tenant_id,
            severity="high",
            **kwargs
        )

    def log_data_breach_attempt(self, data_type: str, user_id: str = None,
                               ip_address: str = None, tenant_id: str = None, **kwargs):
        """Log potential data breach attempt."""
        self.logger.critical(
            "Potential data breach attempt",
            event_type="data_breach_attempt",
            data_type=data_type,
            user_id=user_id,
            ip_address=ip_address,
            tenant_id=tenant_id,
            severity="critical",
            **kwargs
        )


class AuditLogger:
    """
    Audit logger for tracking user actions and system changes.
    """

    def __init__(self):
        self.logger = structlog.get_logger("audit")

    def log_user_action(self, action: str, user_id: str, resource: str = None,
                       details: Dict[str, Any] = None, tenant_id: str = None, **kwargs):
        """Log user action for audit trail."""
        event_data = {
            "event_type": "user_action",
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        if resource:
            event_data["resource"] = resource
        if details:
            event_data["details"] = details
        if tenant_id:
            event_data["tenant_id"] = tenant_id

        self.logger.info("User action performed", **event_data)

    def log_system_change(self, change_type: str, component: str, old_value: Any = None,
                         new_value: Any = None, user_id: str = None, **kwargs):
        """Log system configuration changes."""
        event_data = {
            "event_type": "system_change",
            "change_type": change_type,
            "component": component,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        if old_value is not None:
            event_data["old_value"] = str(old_value)  # Convert to string for JSON serialization
        if new_value is not None:
            event_data["new_value"] = str(new_value)
        if user_id:
            event_data["user_id"] = user_id

        self.logger.info("System change recorded", **event_data)

    def log_admin_action(self, action: str, admin_user_id: str, target_user_id: str = None,
                        details: Dict[str, Any] = None, tenant_id: str = None, **kwargs):
        """Log administrative actions."""
        event_data = {
            "event_type": "admin_action",
            "action": action,
            "admin_user_id": admin_user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        if target_user_id:
            event_data["target_user_id"] = target_user_id
        if details:
            event_data["details"] = details
        if tenant_id:
            event_data["tenant_id"] = tenant_id

        self.logger.info("Admin action performed", **event_data)


# Global logger instances
security_logger = SecurityLogger()
audit_logger = AuditLogger()


@contextmanager
def log_performance(operation_name: str, logger: Optional[structlog.BoundLogger] = None,
                   **context):
    """
    Context manager to log operation performance.

    Usage:
        with log_performance("database_query", query_type="select"):
            result = await database.fetch_all(query)
    """
    if logger is None:
        logger = structlog.get_logger("performance")

    start_time = datetime.utcnow()

    try:
        yield
        success = True
    except Exception as e:
        success = False
        logger.error(
            f"Operation {operation_name} failed",
            operation=operation_name,
            error=str(e),
            success=success,
            **context
        )
        raise
    finally:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            f"Operation {operation_name} completed",
            operation=operation_name,
            duration_seconds=duration,
            success=success,
            **context
        )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Convenience functions for common logging patterns
def log_request_start(method: str, path: str, **kwargs):
    """Log the start of a request."""
    logger = structlog.get_logger("request")
    logger.info(
        "Request started",
        http_method=method,
        http_path=path,
        event_type="request_start",
        **kwargs
    )


def log_request_end(method: str, path: str, status_code: int, duration: float, **kwargs):
    """Log the end of a request."""
    logger = structlog.get_logger("request")
    level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"

    getattr(logger, level)(
        "Request completed",
        http_method=method,
        http_path=path,
        http_status_code=status_code,
        duration_seconds=duration,
        event_type="request_end",
        **kwargs
    )
