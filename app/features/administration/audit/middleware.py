"""Audit logging middleware for automatic event capture."""

import json
import os
import time
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import structlog

from app.features.core.database import engine
from app.deps.tenant import get_current_tenant
from .models import AuditLog

logger = structlog.get_logger(__name__)

# Create a separate session maker for audit middleware to avoid conflicts
audit_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Check if audit logging should be disabled (e.g., in test environment)
AUDIT_ENABLED = os.getenv("ENVIRONMENT", "development") != "test"


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically capture audit events for all HTTP requests.

    Captures:
    - Authentication events
    - Data modification events
    - Administrative actions
    - API access events
    - Error events
    """

    # Endpoints to exclude from audit logging (health checks, static files, etc.)
    EXCLUDED_PATHS = {
        "/docs", "/redoc", "/openapi.json", "/favicon.ico",
        "/static/", "/health", "/metrics"
    }

    # Endpoints that should always be audited regardless of method
    CRITICAL_ENDPOINTS = {
        "/auth/login", "/auth/logout", "/auth/register", "/auth/token",
        "/administration/secrets", "/administration/users", "/administration/tenants",
        "/administration/audit", "/dashboard", "/"
    }

    # HTTP methods that indicate data changes
    MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Sensitive fields to redact from audit logs
    SENSITIVE_FIELDS = {
        "password", "secret", "token", "key", "credential", "private_key",
        "access_token", "refresh_token", "api_key", "session_id"
    }

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request and capture audit events."""

        # Skip audit logging if disabled (e.g., in test environment)
        if not AUDIT_ENABLED:
            return await call_next(request)

        # Skip excluded paths
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Capture request start time
        start_time = time.time()

        # Extract request context
        context = await self._extract_request_context(request)

        # Process the request
        response = None
        error = None

        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            logger.exception("Request processing failed", request_id=request_id)
            raise
        finally:
            # Calculate processing time
            processing_time = time.time() - start_time

            # Create audit log entry
            await self._create_audit_log(
                request=request,
                response=response,
                context=context,
                error=error,
                processing_time=processing_time
            )

        return response

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from audit logging."""
        return any(excluded in path for excluded in self.EXCLUDED_PATHS)

    async def _extract_request_context(self, request: Request) -> Dict[str, Any]:
        """Extract relevant context from the request."""

        # Get user info from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        user_email = getattr(request.state, 'user_email', None)
        user_role = getattr(request.state, 'user_role', None)

        # Get tenant ID from request state (set by auth context middleware)
        tenant_id = getattr(request.state, 'tenant_id', None)

        # Fallback if not set by auth middleware
        if not tenant_id:
            try:
                tenant_id = get_current_tenant() or "default"
            except Exception:
                tenant_id = "default"  # Fallback for non-tenant requests

        # Extract client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Get session info
        session_id = None
        if hasattr(request.state, 'session_id'):
            session_id = request.state.session_id
        elif 'session_id' in request.cookies:
            session_id = request.cookies.get('session_id')

        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "ip_address": client_ip,
            "user_agent": user_agent,
            "session_id": session_id,
            "request_id": getattr(request.state, 'request_id', None)
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        # Check for forwarded headers first (for reverse proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    async def _create_audit_log(
        self,
        request: Request,
        response: Optional[Response],
        context: Dict[str, Any],
        error: Optional[Exception],
        processing_time: float
    ):
        """Create audit log entry for the request."""

        try:
            # Skip if we can't determine what happened
            if not self._should_audit_request(request, response, error):
                return

            # Determine audit event details
            action, category, severity = self._classify_request(request, response, error)

            # PERFORMANCE FIX: Run audit logging in background task
            # Don't block the response - log asynchronously
            import asyncio
            asyncio.create_task(self._save_audit_log_async(
                request=request,
                response=response,
                context=context,
                action=action,
                category=category,
                severity=severity,
                error=error,
                processing_time=processing_time
            ))

        except Exception as audit_error:
            # Never let audit logging break the application
            logger.exception(
                "Failed to create audit log",
                request_id=context.get('request_id'),
                error=str(audit_error)
            )

    def _should_audit_request(
        self,
        request: Request,
        response: Optional[Response],
        error: Optional[Exception]
    ) -> bool:
        """Determine if this request should be audited."""

        path = request.url.path
        method = request.method

        # Always audit critical endpoints
        if any(critical in path for critical in self.CRITICAL_ENDPOINTS):
            return True

        # Always audit mutations
        if method in self.MUTATION_METHODS:
            return True

        # Always audit errors
        if error or (response and response.status_code >= 400):
            return True

        # Audit successful authentication-related requests
        if "/auth/" in path and response and response.status_code < 400:
            return True

        # Skip routine GET requests unless they're for sensitive areas
        if method == "GET":
            sensitive_paths = ["/administration/", "/auth/", "/api/", "/dashboard"]
            return any(sensitive in path for sensitive in sensitive_paths)

        return False

    def _classify_request(
        self,
        request: Request,
        response: Optional[Response],
        error: Optional[Exception]
    ) -> tuple[str, str, str]:
        """Classify the request into action, category, and severity."""

        path = request.url.path
        method = request.method
        status_code = response.status_code if response else 500

        # Determine severity based on status code and error
        if error or status_code >= 500:
            severity = "ERROR"
        elif status_code >= 400:
            severity = "WARNING"
        else:
            severity = "INFO"

        # Classify by path patterns
        if "/auth/" in path:
            category = "AUTH"
            if "login" in path:
                action = "USER_LOGIN_ATTEMPT" if status_code >= 400 else "USER_LOGIN"
            elif "logout" in path:
                action = "USER_LOGOUT"
            elif "register" in path:
                action = "USER_REGISTRATION_ATTEMPT" if status_code >= 400 else "USER_REGISTRATION"
            else:
                action = f"AUTH_{method}"

        elif "/administration/" in path:
            category = "ADMIN"
            if "/secrets/" in path:
                action = self._get_crud_action("SECRET", method, path)
            elif "/users/" in path:
                action = self._get_crud_action("USER", method, path)
            elif "/tenants/" in path:
                action = self._get_crud_action("TENANT", method, path)
            elif "/audit/" in path:
                action = self._get_crud_action("AUDIT", method, path)
            elif "/tasks/" in path:
                action = self._get_crud_action("TASK", method, path)
            else:
                action = f"ADMIN_{method}"

        elif "/api/" in path or method in self.MUTATION_METHODS:
            category = "DATA"
            action = self._get_crud_action("DATA", method, path)

        else:
            category = "SYSTEM"
            action = f"SYSTEM_{method}"

        # Override severity for critical security events
        if action in ["USER_LOGIN_ATTEMPT", "USER_REGISTRATION_ATTEMPT"] and status_code >= 400:
            severity = "WARNING"
        elif "DELETE" in action:
            severity = "WARNING"

        return action, category, severity

    def _get_crud_action(self, resource_type: str, method: str, path: str) -> str:
        """Generate CRUD action name based on method and path."""

        if method == "GET":
            if "/api/" in path or "list" in path:
                return f"{resource_type}_LIST"
            else:
                return f"{resource_type}_VIEW"
        elif method == "POST":
            return f"{resource_type}_CREATE"
        elif method == "PUT":
            return f"{resource_type}_UPDATE"
        elif method == "PATCH":
            return f"{resource_type}_MODIFY"
        elif method == "DELETE":
            return f"{resource_type}_DELETE"
        else:
            return f"{resource_type}_{method}"

    async def _save_audit_log(
        self,
        db: AsyncSession,
        request: Request,
        response: Optional[Response],
        context: Dict[str, Any],
        action: str,
        category: str,
        severity: str,
        error: Optional[Exception],
        processing_time: float
    ):
        """Save the audit log entry to database."""

        # Prepare description
        description = f"{request.method} {request.url.path}"
        if error:
            description += f" - Error: {str(error)[:200]}"
        elif response:
            description += f" - Status: {response.status_code}"

        # Extract resource info from path
        resource_type, resource_id = self._extract_resource_info(request.url.path)

        # Prepare extra data (non-sensitive)
        extra_data = {
            "processing_time_ms": round(processing_time * 1000, 2),
            "response_status": response.status_code if response else None,
            "query_params": dict(request.query_params) if request.query_params else None,
        }

        # Capture request body for data changes (for compliance)
        old_values, new_values = await self._extract_data_changes(request, response, action)

        # Add error details if present
        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)[:500]  # Limit error message length

        # Create audit log entry
        audit_log = AuditLog(
            tenant_id=context["tenant_id"],
            timestamp=datetime.now(timezone.utc),
            action=action,
            category=category,
            severity=severity,
            user_id=context["user_id"],
            user_email=context["user_email"],
            user_role=context["user_role"],
            ip_address=context["ip_address"],
            user_agent=context["user_agent"],
            session_id=context["session_id"],
            request_id=context["request_id"],
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            description=description,
            extra_data=extra_data,
            source_module="audit_middleware",
            endpoint=str(request.url.path),
            method=request.method
        )

        # Save to database
        db.add(audit_log)
        await db.commit()

        logger.debug(
            "Audit log created",
            action=action,
            category=category,
            severity=severity,
            user_email=context["user_email"],
            request_id=context["request_id"]
        )

    async def _save_audit_log_async(
        self,
        request: Request,
        response: Optional[Response],
        context: Dict[str, Any],
        action: str,
        category: str,
        severity: str,
        error: Optional[Exception],
        processing_time: float
    ):
        """Save audit log in background task - doesn't block response."""
        try:
            # Use independent session for audit logging to avoid conflicts
            async with audit_session() as db:
                await self._save_audit_log(
                    db=db,
                    request=request,
                    response=response,
                    context=context,
                    action=action,
                    category=category,
                    severity=severity,
                    error=error,
                    processing_time=processing_time
                )
        except Exception as bg_error:
            # Log but don't raise - this is background task
            logger.exception(
                "Background audit logging failed",
                request_id=context.get('request_id'),
                error=str(bg_error)
            )

    def _extract_resource_info(self, path: str) -> tuple[Optional[str], Optional[str]]:
        """Extract resource type and ID from URL path."""

        # Common patterns for resource extraction
        resource_patterns = {
            "/administration/secrets/": ("secret", r"/(\d+)"),
            "/administration/users/": ("user", r"/(\d+)"),
            "/auth/users/": ("user", r"/(\d+)"),
            "/business-automations/demo/items/": ("demo_item", r"/(\d+)"),
        }

        for pattern, (resource_type, id_regex) in resource_patterns.items():
            if pattern in path:
                # Try to extract ID using regex
                import re
                match = re.search(id_regex, path.replace(pattern, "/"))
                resource_id = match.group(1) if match else None
                return resource_type, resource_id

        return None, None

    async def _extract_data_changes(self, request: Request, response: Optional[Response], action: str) -> tuple[Optional[dict], Optional[dict]]:
        """Extract old and new values for data changes."""

        old_values = None
        new_values = None

        try:
            # Only capture data changes for mutation operations
            if request.method in self.MUTATION_METHODS:
                # Capture request body (new values for CREATE/UPDATE)
                if hasattr(request, '_body'):
                    body = request._body
                elif hasattr(request.state, 'body'):
                    body = request.state.body
                else:
                    # Try to read body if still available
                    try:
                        body = await request.body()
                    except:
                        body = None

                if body:
                    try:
                        import json
                        body_data = json.loads(body.decode())
                        # Redact sensitive data
                        new_values = self._redact_sensitive_data(body_data)

                        # Limit size to prevent database bloat
                        if new_values and len(str(new_values)) > 5000:
                            new_values = {"_truncated": True, "_size": len(str(new_values))}

                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Non-JSON body, store metadata only
                        new_values = {"_content_type": request.headers.get("content-type", "unknown")}

                # For UPDATE/DELETE operations, we would ideally capture old values
                # This would require database queries which we skip here for performance
                # In production, consider implementing this via database triggers or ORM events

        except Exception as e:
            # Never let data extraction break audit logging
            logger.debug(f"Failed to extract data changes: {e}")

        return old_values, new_values

    def _redact_sensitive_data(self, data: Any) -> Any:
        """Recursively redact sensitive fields from data."""

        if isinstance(data, dict):
            return {
                key: "[REDACTED]" if key.lower() in self.SENSITIVE_FIELDS
                else self._redact_sensitive_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        else:
            return data
