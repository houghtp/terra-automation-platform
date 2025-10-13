"""
Content Broadcaster CRUD routes for Tabulator operations.
"""
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
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
        # Return simple array for Tabulator (matches planning_routes.py pattern)
        return result.get("data", [])

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get content list")
        raise HTTPException(status_code=500, detail="Failed to retrieve content")

@router.get("/api/{content_id}")
async def get_content(
    content_id: str,
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

@router.patch("/{content_id}/field")
async def update_content_field(
    content_id: str,
    field_update: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """Update single content field for inline editing (standard pattern)."""
    try:
        field = field_update.get("field")
        value = field_update.get("value")

        # Field type coercion for specific fields
        if field == "priority" and value:
            value = value.lower()  # Ensure lowercase for enum

        if field == "state" and value:
            value = value.lower()  # Ensure lowercase for enum

        content = await service.update_content_field(content_id, field, value)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Commit the transaction
        await db.commit()

        return {"success": True}

    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to update content field {content_id}")
        raise HTTPException(status_code=500, detail="Failed to update content field")

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

# Delete content (accept both DELETE and POST for compatibility) - STANDARD PATTERN
@router.delete("/{content_id}/delete")
@router.post("/{content_id}/delete")
async def delete_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """Delete content using standard pattern (matches users slice)."""
    try:
        success = await service.delete_content(content_id)
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to delete content")


# --- HTMX/Modal Routes ---

@router.get("/{content_id}/view")
async def view_content_item(
    request: Request,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """Full-page content item viewer."""
    from app.features.core.templates import templates

    try:
        content = await service.get_content_by_id(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return templates.TemplateResponse(
            "content_broadcaster/view_content.html",
            {
                "request": request,
                "content": content,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to load content view for {content_id}")
        raise HTTPException(status_code=500, detail="Failed to load content")
