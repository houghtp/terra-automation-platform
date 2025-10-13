"""
API Key Management Administration Routes.

Provides admin interface for managing customer/tenant API keys.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.api_security import APIKeyScope
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.administration.api_keys.services import APIKeyCrudService
from app.deps.tenant import tenant_dependency
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)

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
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get API key usage statistics (admin only)."""
    # Check admin permissions
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
    if not is_global_admin and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        service = APIKeyCrudService(db, tenant_id)
        stats = await service.get_api_key_stats()
        return APIKeyStatsResponse(**stats)

    except Exception as e:
        logger.error("Failed to get API key stats", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key statistics"
        )


@router.post("/create", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new API key for tenant (admin only)."""
    # Check admin permissions
    if current_user.role != "admin" and current_user.role != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        # Global admin can create keys for any tenant
        # Regular admin can only create for their own tenant
        if current_user.role == "admin" and request.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create API key for different tenant"
            )

        service = APIKeyCrudService(db, current_user.tenant_id)

        api_key, secret = await service.create_api_key(
            name=request.name,
            target_tenant_id=request.tenant_id,
            scopes=request.scopes,
            created_by_user_id=current_user.id,
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

        await db.commit()

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
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create API key", error=str(e), name=request.name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/list", response_model=List[APIKeyListResponse])
async def list_api_keys(
    filter_tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    include_inactive: bool = Query(False, description="Include inactive keys"),
    limit: int = Query(50, ge=1, le=100, description="Number of keys to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """List API keys with optional filtering (admin only)."""
    # Check admin permissions
    if current_user.role != "admin" and current_user.role != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        service = APIKeyCrudService(db, tenant_id)
        api_keys = await service.list_api_keys(
            filter_tenant_id=filter_tenant_id,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset
        )

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
        logger.error("Failed to list API keys", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get API key details (admin only, secret not included)."""
    # Check admin permissions
    if current_user.role != "admin" and current_user.role != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        service = APIKeyCrudService(db, tenant_id)
        api_key = await service.get_api_key(key_id)

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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to get API key", key_id=key_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key"
        )


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Revoke API key (admin only)."""
    # Check admin permissions
    if current_user.role != "admin" and current_user.role != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        service = APIKeyCrudService(db, tenant_id)
        success = await service.revoke_api_key(key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key"
            )

        await db.commit()

        return {"message": "API key revoked successfully", "key_id": key_id}

    except HTTPException:
        raise
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        logger.error("Failed to revoke API key", key_id=key_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.get("/scopes/available")
async def get_available_scopes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of available API key scopes."""
    # Check admin permissions
    if current_user.role != "admin" and current_user.role != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    service = APIKeyCrudService(db, current_user.tenant_id)
    scopes = await service.get_available_scopes()

    return {"scopes": scopes}
