"""
API Key Management Administration Routes.

Provides admin interface for managing customer/tenant API keys.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.api_security import APIKeyScope
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.administration.api_keys.schemas import (
    APIKeyCreateRequest,
    APIKeyListResponse,
    APIKeyResponse,
    APIKeyStatsResponse,
)
from app.features.administration.api_keys.services import APIKeyCrudService
from app.deps.tenant import tenant_dependency
from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.route_imports import is_global_admin, JSONResponse, handle_route_error

logger = get_logger(__name__)

router = APIRouter(tags=["admin-api-keys"])


# Admin API Key Management
@router.get("/stats", response_model=APIKeyStatsResponse)
async def get_api_key_stats(
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get API key usage statistics (admin only)."""
    # Check admin permissions
    if not is_global_admin(current_user) and current_user.role != "admin":
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


@router.get("/api/list", response_class=JSONResponse)
async def list_api_keys_api(
    filter_tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    include_inactive: bool = Query(False, description="Include inactive keys"),
    limit: int = Query(50, ge=1, le=100, description="Number of keys to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """List API keys for Tabulator (standardized pattern)."""
    # Check admin permissions
    if not is_global_admin(current_user) and current_user.role != "admin":
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

        # Standardized response format - simple array with dict conversion
        result = []
        for key in api_keys:
            result.append({
                "id": key.id,
                "key_id": key.key_id,
                "name": key.name,
                "description": key.description,
                "tenant_id": key.tenant_id,
                "scopes": key.scopes,
                "status": key.status,
                "is_active": key.is_active,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "usage_count": key.usage_count,
                "success_rate": key.success_rate,
                "created_at": key.created_at.isoformat()
            })

        return result

    except Exception as e:
        handle_route_error("list_api_keys_api", e, tenant_id=tenant_id)
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
