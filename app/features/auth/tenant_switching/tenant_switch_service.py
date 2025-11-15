"""
Tenant switching service for global admins.

Allows global admins to switch their session context to view data
from specific tenants without logging out and back in.
"""

from typing import Optional
from fastapi import Request, HTTPException
import structlog

logger = structlog.get_logger(__name__)

# Session key for storing switched tenant
SWITCHED_TENANT_SESSION_KEY = "_switched_tenant_id"


class TenantSwitchService:
    """Service for managing tenant switching for global admins."""

    @staticmethod
    def set_switched_tenant(request: Request, tenant_id: str) -> None:
        """
        Set the switched tenant for the current session.

        Args:
            request: FastAPI request object
            tenant_id: Tenant ID to switch to

        Raises:
            HTTPException: If user is not global admin
        """
        # Verify user is global admin
        user_role = getattr(request.state, 'user_role', None)
        if user_role != 'global_admin':
            raise HTTPException(
                status_code=403,
                detail="Only global admins can switch tenants"
            )

        # Store switched tenant in session
        if not hasattr(request, 'session'):
            raise HTTPException(
                status_code=500,
                detail="Session middleware not configured for global admin tenant switching"
            )

        try:
            session = request.session
        except RuntimeError as exc:
            raise HTTPException(
                status_code=500,
                detail="Session middleware not configured for global admin tenant switching"
            ) from exc

        session[SWITCHED_TENANT_SESSION_KEY] = tenant_id

        logger.info(
            "Global admin switched tenant",
            user_email=getattr(request.state, 'user_email', 'unknown'),
            switched_to_tenant=tenant_id
        )

    @staticmethod
    def get_switched_tenant(request: Request) -> Optional[str]:
        """
        Get the currently switched tenant for the session.

        Args:
            request: FastAPI request object

        Returns:
            Switched tenant ID or None if not switched
        """
        if not hasattr(request, 'session'):
            return None

        try:
            session = request.session
        except RuntimeError:
            return None

        return session.get(SWITCHED_TENANT_SESSION_KEY)

    @staticmethod
    def clear_switched_tenant(request: Request) -> None:
        """
        Clear the switched tenant and return to global admin context.

        Args:
            request: FastAPI request object
        """
        if hasattr(request, 'session') and SWITCHED_TENANT_SESSION_KEY in request.session:
            tenant_id = request.session[SWITCHED_TENANT_SESSION_KEY]
            del request.session[SWITCHED_TENANT_SESSION_KEY]

            logger.info(
                "Global admin cleared tenant switch",
                user_email=getattr(request.state, 'user_email', 'unknown'),
                previous_tenant=tenant_id
            )

    @staticmethod
    def is_tenant_switched(request: Request) -> bool:
        """
        Check if the current session has a switched tenant.

        Args:
            request: FastAPI request object

        Returns:
            True if tenant is switched, False otherwise
        """
        return TenantSwitchService.get_switched_tenant(request) is not None
