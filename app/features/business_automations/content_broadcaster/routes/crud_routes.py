"""
Content Broadcaster CRUD routes for Tabulator operations.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import get_db
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from .models import ContentUpdateRequest
from .api_routes import get_content_service
from ..models import ContentState, ApprovalStatus
from ..services import ContentBroadcasterService
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["content-broadcaster-crud"])

# --- TABULATOR CRUD ROUTES ---

@router.get("/api/list")
async def get_content_list(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    approval_status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to get paginated content list with filtering."""
    try:
        # Parse enum values
        state_enum = None
        if state:
            try:
                state_enum = ContentState(state)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid state: {state}")

        approval_enum = None
        if approval_status:
            try:
                approval_enum = ApprovalStatus(approval_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid approval status: {approval_status}")

        result = await service.get_content_list(
            limit=limit,
            offset=offset,
            search=search,
            state=state_enum,
            created_by=created_by,
            approval_status=approval_enum
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get content list")
        raise HTTPException(status_code=500, detail="Failed to retrieve content")

@router.get("/api/{content_id}")
async def get_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to get content by ID."""
    try:
        content = await service.get_content_by_id(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return content.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve content")

@router.put("/api/{content_id}")
async def update_content(
    content_id: str,
    request: ContentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to update content."""
    try:
        content = await service.update_content(
            content_id=content_id,
            title=request.title,
            body=request.body,
            updated_by=current_user.id,
            metadata=request.metadata,
            tags=request.tags
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return content.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to update content")

@router.delete("/api/{content_id}")
async def delete_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to delete content."""
    try:
        success = await service.delete_content(content_id)
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")

        return {"success": True, "message": "Content deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to delete content")
