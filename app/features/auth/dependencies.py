"""
Authentication dependencies for FastAPI dependency injection.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import get_db
from app.deps.tenant import tenant_dependency
from app.features.auth.services import AuthService
from app.features.auth.jwt_utils import JWTUtils, TokenData
from app.features.auth.models import User

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """Extract and validate JWT token from Authorization header or cookies."""
    token = None

    # Try Authorization header first
    if credentials:
        token = credentials.credentials
    # Fall back to cookie if no Authorization header
    elif request.cookies.get("access_token"):
        token = request.cookies.get("access_token")

    if not token:
        return None

    token_data = JWTUtils.verify_token(token)
    return token_data


async def get_current_user(
    token_data: Optional[TokenData] = Depends(get_current_user_token),
    tenant_id: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user with tenant validation."""
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate tenant matches token
    if token_data.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch in token"
        )

    # Get user from database
    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(
        token_data.user_id,
        token_data.tenant_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current authenticated and active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current user with admin role validation."""
    if current_user.role not in ["admin", "global_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_global_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current user with global admin role validation."""
    if current_user.role != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global admin privileges required"
        )
    return current_user


async def get_tenant_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current user with tenant admin role validation (excludes global admin)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin privileges required"
        )
    return current_user


# Optional authentication (doesn't raise exception if no token)
async def get_optional_current_user(
    token_data: Optional[TokenData] = Depends(get_current_user_token),
    tenant_id: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not token_data:
        return None

    # Validate tenant matches token
    if token_data.tenant_id != tenant_id:
        return None

    # Get user from database
    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(
        token_data.user_id,
        token_data.tenant_id
    )

    return user if user and user.is_active else None
