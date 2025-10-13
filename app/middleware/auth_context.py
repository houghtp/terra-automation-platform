"""
Authentication context middleware to set user state for audit logging.
"""
import logging
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.jwt_utils import JWTUtils
from app.features.auth.services import AuthService
from app.features.core.database import async_session
from app.deps.tenant import get_current_tenant

logger = logging.getLogger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract authentication context and set it on request.state
    for use by audit logging and other systems.

    This middleware runs early in the request lifecycle to populate:
    - request.state.user_id
    - request.state.user_email
    - request.state.user_role
    - request.state.tenant_id
    """

    # Paths that don't need authentication context
    EXCLUDED_PATHS = {
        "/docs", "/redoc", "/openapi.json", "/favicon.ico",
        "/static/", "/health", "/metrics"
    }

    async def dispatch(self, request: Request, call_next):
        """Extract auth context and set on request state."""

        # Skip excluded paths for performance
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # Initialize state with defaults
        request.state.user_id = None
        request.state.user_email = None
        request.state.user_role = None
        request.state.tenant_id = None

        try:
            # Extract token from request
            token = self._extract_token(request)
            if token:
                # Validate token and get user data
                token_data = JWTUtils.verify_token(token)
                if token_data:
                    # Get user details from database
                    user = await self._get_user_from_token(token_data)
                    if user:
                        # Set user context on request state
                        request.state.user_id = str(user.id)
                        request.state.user_email = user.email
                        request.state.user_role = user.role
                        request.state.tenant_id = user.tenant_id

                        logger.debug(
                            f"Auth context set for user {user.email} "
                            f"(role: {user.role}, tenant: {user.tenant_id})"
                        )

            # Set tenant ID even if no user (for anonymous requests)
            if not request.state.tenant_id:
                try:
                    tenant_id = get_current_tenant() or "default"
                    request.state.tenant_id = tenant_id
                except:
                    request.state.tenant_id = "default"

        except Exception as e:
            # Never break the request due to auth context issues
            logger.warning(f"Failed to extract auth context: {e}")
            # Ensure defaults are set
            request.state.tenant_id = request.state.tenant_id or "default"

        # Continue with request
        return await call_next(request)

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from auth context extraction."""
        return any(excluded in path for excluded in self.EXCLUDED_PATHS)

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header or cookies."""

        # Try Authorization header first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Fall back to cookie
        return request.cookies.get("access_token")

    async def _get_user_from_token(self, token_data) -> Optional[object]:
        """Get user object from token data."""

        try:
            async with async_session() as session:
                auth_service = AuthService(session)
                user = await auth_service.get_user_by_id(
                    token_data.user_id,
                    token_data.tenant_id
                )
                return user if user and user.is_active else None

        except Exception as e:
            logger.warning(f"Failed to get user from token: {e}")
            return None
