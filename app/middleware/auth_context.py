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
        """Process the request and set auth context."""
        # Initialize request state attributes
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
                    # Set basic info from token immediately (fallback)
                    request.state.user_id = str(token_data.user_id)
                    request.state.user_email = token_data.email
                    request.state.user_role = token_data.role
                    request.state.tenant_id = token_data.tenant_id

                    # Try to get full user details from database
                    try:
                        user = await self._get_user_from_token(token_data)
                        if user:
                            # Update with fresh user data from DB
                            request.state.user_id = str(user.id)
                            request.state.user_email = user.email
                            request.state.user_role = user.role
                            request.state.tenant_id = user.tenant_id

                            # Check if global admin has switched tenants
                            if user.role == "global_admin":
                                try:
                                    from app.features.auth.tenant_switching.tenant_switch_service import TenantSwitchService
                                    switched_tenant = TenantSwitchService.get_switched_tenant(request)
                                    if switched_tenant:
                                        request.state.tenant_id = switched_tenant
                                        logger.debug(
                                            f"Global admin {user.email} using switched tenant: {switched_tenant}"
                                        )
                                except Exception as session_error:
                                    # Session access might fail if SessionMiddleware hasn't run yet
                                    # This is expected and can be safely ignored - tenant switching only works
                                    # when SessionMiddleware is properly initialized
                                    logger.debug(f"Tenant switching unavailable (session not initialized): {session_error}")

                            logger.debug(
                                f"Auth context set for user {user.email} "
                                f"(role: {user.role}, tenant: {user.tenant_id})"
                            )
                    except Exception as db_error:
                        # Database lookup failed, but we have token data as fallback
                        logger.warning(f"Database lookup failed for user {token_data.email}, using token data: {db_error}")

            # Set tenant ID even if no user (for anonymous requests)
            if not request.state.tenant_id:
                try:
                    tenant_id = get_current_tenant() or "global"
                    request.state.tenant_id = tenant_id
                except:
                    request.state.tenant_id = "global"

        except Exception as e:
            # Never break the request due to auth context issues
            logger.warning(f"Failed to extract auth context: {e}")
            # Ensure defaults are set
            request.state.tenant_id = request.state.tenant_id or "default"

        # Override tenant_ctx_var with authenticated user's tenant_id
        # This ensures logging uses the correct tenant for authenticated users
        try:
            from app.middleware.tenant import tenant_ctx_var
            tenant_ctx_var.set(request.state.tenant_id)
        except Exception:
            pass  # Fail silently if tenant middleware not available

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
