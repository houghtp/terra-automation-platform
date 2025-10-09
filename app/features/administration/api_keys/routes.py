"""
API Key Management Administration Routes.

Provides admin interface for managing customer/tenant API keys.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.api_security import APIKeyManager, APIKeyScope, APIKey
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.deps.tenant import tenant_dependency
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["admin-api-keys"])


# Request/Response Models
class APIKeyCreateRequest(BaseModel):
    """Request to create new API key."""
    name: str = Field(..., min_length=1, max_length=255, description="API key name")
    description: Optional[str] = Field(None, max_length=1000, description="API key description")
    tenant_id: str = Field(..., description="Tenant ID for the API key")
    scopes: List[str] = Field(..., min_items=1, description="List of permission scopes")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiration")
    rate_limit_per_hour: int = Field(1000, ge=1, le=10000, description="Requests per hour limit")
    rate_limit_per_day: int = Field(10000, ge=1, le=100000, description="Requests per day limit")


class APIKeyResponse(BaseModel):
    """API key information response."""
    id: int
    key_id: str
    name: str
    description: Optional[str]
    tenant_id: str
    scopes: List[str]
    status: str
    is_active: bool
    rate_limit_per_hour: int
    rate_limit_per_day: int
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    usage_count: int

    # Only include secret on creation
    secret: Optional[str] = None


class APIKeyListResponse(BaseModel):
    """API key list item (without secret)."""
    id: int
    key_id: str
    name: str
    description: Optional[str]
    tenant_id: str
    scopes: List[str]
    status: str
    is_active: bool
    last_used_at: Optional[str]
    usage_count: int
    success_rate: float
    created_at: str


class APIKeyStatsResponse(BaseModel):
    """API key usage statistics."""
    total_keys: int
    active_keys: int
    revoked_keys: int
    expired_keys: int
    total_requests_today: int
    top_tenants: List[dict]


# Admin API Key Management
@router.get("/stats", response_model=APIKeyStatsResponse)
async def get_api_key_stats(
    current_user: User = Depends(get_current_user),
    tenant: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db)
):
    """Get API key usage statistics (admin only)."""
    # Check admin permissions and tenant isolation
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
    if not is_global_admin and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        from sqlalchemy import select, func
        from app.features.core.api_security import APIKeyStatus

        # Get total counts
        total_stmt = select(func.count(APIKey.id))
        total_result = await session.execute(total_stmt)
        total_keys = total_result.scalar() or 0

        # Get active keys
        active_stmt = select(func.count(APIKey.id)).where(
            APIKey.status == APIKeyStatus.ACTIVE.value,
            APIKey.is_active == True
        )
        active_result = await session.execute(active_stmt)
        active_keys = active_result.scalar() or 0

        # Get revoked keys
        revoked_stmt = select(func.count(APIKey.id)).where(
            APIKey.status == APIKeyStatus.REVOKED.value
        )
        revoked_result = await session.execute(revoked_stmt)
        revoked_keys = revoked_result.scalar() or 0

        # Get expired keys
        from datetime import datetime
        expired_stmt = select(func.count(APIKey.id)).where(
            APIKey.expires_at < datetime.now(timezone.utc)
        )
        expired_result = await session.execute(expired_stmt)
        expired_keys = expired_result.scalar() or 0

        # Get top tenants by usage
        top_tenants_stmt = select(
            APIKey.tenant_id,
            func.sum(APIKey.usage_count).label('total_usage')
        ).group_by(APIKey.tenant_id).order_by(
            func.sum(APIKey.usage_count).desc()
        ).limit(5)

        top_tenants_result = await session.execute(top_tenants_stmt)
        top_tenants = [
            {"tenant_id": row.tenant_id, "usage_count": row.total_usage}
            for row in top_tenants_result
        ]

        return APIKeyStatsResponse(
            total_keys=total_keys,
            active_keys=active_keys,
            revoked_keys=revoked_keys,
            expired_keys=expired_keys,
            total_requests_today=0,  # Would need daily tracking
            top_tenants=top_tenants
        )

    except Exception as e:
        logger.error(f"Failed to get API key stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key statistics"
        )


@router.post("/create", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create new API key for tenant (admin only)."""
    # Check admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        # Validate scopes
        valid_scopes = [scope.value for scope in APIKeyScope]
        invalid_scopes = [s for s in request.scopes if s not in valid_scopes]
        if invalid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scopes: {invalid_scopes}"
            )

        # Create API key
        api_key, secret = await APIKeyManager.create_api_key(
            session=session,
            name=request.name,
            tenant_id=request.tenant_id,
            scopes=request.scopes,
            created_by=current_user.id,
            description=request.description,
            expires_in_days=request.expires_in_days,
            rate_limit_per_hour=request.rate_limit_per_hour,
            rate_limit_per_day=request.rate_limit_per_day
        )

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )

        return APIKeyResponse(
            id=api_key.id,
            key_id=api_key.key_id,
            name=api_key.name,
            description=api_key.description,
            tenant_id=api_key.tenant_id,
            scopes=api_key.scopes,
            status=api_key.status,
            is_active=api_key.is_active,
            rate_limit_per_hour=api_key.rate_limit_per_hour,
            rate_limit_per_day=api_key.rate_limit_per_day,
            created_at=api_key.created_at.isoformat(),
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            usage_count=api_key.usage_count,
            secret=secret  # Only returned on creation
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/list", response_model=List[APIKeyListResponse])
async def list_api_keys(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    include_inactive: bool = Query(False, description="Include inactive keys"),
    limit: int = Query(50, ge=1, le=100, description="Number of keys to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """List API keys with optional filtering (admin only)."""
    # Check admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        from sqlalchemy import select

        stmt = select(APIKey)

        # Apply filters
        if tenant_id:
            stmt = stmt.where(APIKey.tenant_id == tenant_id)

        if not include_inactive:
            stmt = stmt.where(APIKey.is_active == True)

        # Apply pagination
        stmt = stmt.order_by(APIKey.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(stmt)
        api_keys = result.scalars().all()

        return [
            APIKeyListResponse(
                id=key.id,
                key_id=key.key_id,
                name=key.name,
                description=key.description,
                tenant_id=key.tenant_id,
                scopes=key.scopes,
                status=key.status,
                is_active=key.is_active,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                usage_count=key.usage_count,
                success_rate=key.success_rate,
                created_at=key.created_at.isoformat()
            )
            for key in api_keys
        ]

    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get API key details (admin only, secret not included)."""
    # Check admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        from sqlalchemy import select

        stmt = select(APIKey).where(APIKey.key_id == key_id)
        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return APIKeyResponse(
            id=api_key.id,
            key_id=api_key.key_id,
            name=api_key.name,
            description=api_key.description,
            tenant_id=api_key.tenant_id,
            scopes=api_key.scopes,
            status=api_key.status,
            is_active=api_key.is_active,
            rate_limit_per_hour=api_key.rate_limit_per_hour,
            rate_limit_per_day=api_key.rate_limit_per_day,
            created_at=api_key.created_at.isoformat(),
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            usage_count=api_key.usage_count
            # Note: secret not included for security
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key"
        )


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Revoke API key (admin only)."""
    # Check admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        # Find the API key first to get tenant_id
        from sqlalchemy import select
        stmt = select(APIKey).where(APIKey.key_id == key_id)
        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Revoke the key
        success = await APIKeyManager.revoke_api_key(
            session=session,
            key_id=key_id,
            tenant_id=api_key.tenant_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key"
            )

        return {"message": "API key revoked successfully", "key_id": key_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.get("/scopes/available")
async def get_available_scopes(
    current_user: User = Depends(get_current_user)
):
    """Get list of available API key scopes."""
    # Check admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    scopes = {
        scope.value: {
            "name": scope.name,
            "description": {
                "read": "Read-only access to resources",
                "write": "Create and update resources",
                "admin": "Full administrative access",
                "webhook": "Webhook and event access",
                "monitoring": "System monitoring and metrics"
            }.get(scope.value, f"Access scope: {scope.value}")
        }
        for scope in APIKeyScope
    }

    return {"scopes": scopes}
