"""
Content Broadcaster form routes for UI and HTMX endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.features.core.database import get_db
from app.features.core.templates import templates
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from .api_routes import get_content_service
from ..models import ContentState
from ..services import ContentBroadcasterService
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["content-broadcaster-forms"])

# --- PLANNING PAGE ROUTES ---

@router.get("/planning", response_class=HTMLResponse)
async def content_planning_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
):
    """Content planning page with AI generation."""
    return templates.TemplateResponse(
        "content_broadcaster/planning.html",
        {
            "request": request,
            "title": "Content Planning - AI Generator",
            "user": current_user,
            "page_title": "Content Ideas",
            "page_description": "AI-Powered Content Generation",
            "page_icon": "bulb",
            "add_url": "/features/content-broadcaster/planning/partials/create_plan_modal",
            "entity_name": "content-plans"
        }
    )

@router.get("/planning/partials/create_plan_modal", response_class=HTMLResponse)
async def get_create_plan_modal(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Get the create content plan modal."""
    return templates.TemplateResponse(
        "content_broadcaster/partials/create_plan_modal.html",
        {"request": request, "user": current_user}
    )

# --- UI ROUTES (Jinja + HTMX) ---

# --- PRIMARY ENTRY POINTS ---

@router.get("/", response_class=HTMLResponse)
async def content_broadcaster_page(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
):
    """
    Primary entry point for Content Broadcaster.

    Redirects to the Content Ideas planning view so the first tab is always visible.
    """
    return RedirectResponse(
        url="/features/content-broadcaster/planning",
        status_code=302
    )


@router.get("/library", response_class=HTMLResponse)
async def content_broadcaster_library_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """Content library page showing generated content and publishing workflow."""
    try:
        stats = await service.get_dashboard_stats()

        return templates.TemplateResponse(
            "content_broadcaster/content_broadcaster.html",
            {
                "request": request,
                "title": "Content Broadcaster",
                "stats": stats,
                "user": current_user
            }
        )
    except Exception:
        logger.exception("Failed to load content broadcaster library page")
        raise HTTPException(status_code=500, detail="Failed to load page")

@router.get("/content", response_class=HTMLResponse)
async def content_table(
    request: Request,
    search: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for content table partial."""
    try:
        # Parse state enum
        state_enum = None
        if state and state != "all":
            try:
                state_enum = ContentState(state)
            except ValueError:
                pass  # Ignore invalid states for web interface

        result = await service.get_content_list(
            limit=50,  # Reasonable limit for web interface
            offset=0,
            search=search,
            state=state_enum
        )

        return templates.TemplateResponse(
            "content_broadcaster/partials/list_content.html",
            {
                "request": request,
                "content_items": result["data"],
                "total": result["total"]
            }
        )

    except Exception as e:
        logger.exception("Failed to load content table")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to load content"}
        )

@router.get("/partials/form", response_class=HTMLResponse)
async def content_form_modal(
    request: Request,
    content_id: str = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Standard partials/form endpoint for table_actions component."""
    # For now, redirect to create modal since that's what exists
    return templates.TemplateResponse(
        "content_broadcaster/partials/create_modal.html",
        {"request": request, "content_id": content_id}
    )

@router.get("/create-modal", response_class=HTMLResponse)
async def create_content_modal(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """HTMX endpoint for AI content generation modal."""
    return templates.TemplateResponse(
        "content_broadcaster/partials/enhanced_create_modal.html",
        {"request": request}
    )

@router.post("/create", response_class=HTMLResponse)
async def create_content_form(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    tags: Optional[str] = Form(default=""),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for creating content via manual form (for editing AI-generated content)."""
    try:
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

        content = await service.create_content(
            title=title,
            body=body,
            created_by_user=current_user,
            tags=tag_list
        )

        # Return updated content table
        result = await service.get_content_list(limit=50, offset=0)

        return templates.TemplateResponse(
            "content_broadcaster/partials/list_content.html",
            {
                "request": request,
                "content_items": result["data"],
                "total": result["total"],
                "show_success": True,
                "success_message": f"Content '{content.title}' created successfully"
            }
        )

    except Exception as e:
        logger.exception("Failed to create content")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to create content"}
        )

@router.get("/approve-modal/{content_id}", response_class=HTMLResponse)
async def approve_content_modal(
    request: Request,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for approve content modal."""
    try:
        content = await service.get_content_by_id(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return templates.TemplateResponse(
            "content_broadcaster/partials/approve_modal.html",
            {"request": request, "content": content.to_dict()}
        )

    except Exception as e:
        logger.exception(f"Failed to load approve modal for content {content_id}")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to load approval form"}
        )

@router.get("/reject-modal/{content_id}", response_class=HTMLResponse)
async def reject_content_modal(
    request: Request,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for reject content modal."""
    try:
        content = await service.get_content_by_id(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return templates.TemplateResponse(
            "content_broadcaster/partials/reject_modal.html",
            {"request": request, "content": content.to_dict()}
        )

    except Exception as e:
        logger.exception(f"Failed to load reject modal for content {content_id}")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to load rejection form"}
        )

@router.post("/reject/{content_id}", response_class=HTMLResponse)
async def reject_content_form(
    request: Request,
    content_id: str,
    comment: str = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for rejecting content via form."""
    try:
        content = await service.reject_content(
            content_id=content_id,
            rejected_by=current_user,
            comment=comment
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Return updated content table
        result = await service.get_content_list(limit=50, offset=0)

        return templates.TemplateResponse(
            "content_broadcaster/partials/list_content.html",
            {
                "request": request,
                "content_items": result["data"],
                "total": result["total"],
                "show_success": True,
                "success_message": f"Content '{content.title}' rejected successfully"
            }
        )

    except Exception as e:
        logger.exception(f"Failed to reject content {content_id}")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to reject content"}
        )

@router.get("/schedule-modal/{content_id}", response_class=HTMLResponse)
async def schedule_content_modal(
    request: Request,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for schedule content modal."""
    try:
        content = await service.get_content_by_id(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return templates.TemplateResponse(
            "content_broadcaster/partials/schedule_modal.html",
            {"request": request, "content": content.to_dict()}
        )

    except Exception as e:
        logger.exception(f"Failed to load schedule modal for content {content_id}")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to load scheduling form"}
        )

@router.post("/schedule/{content_id}", response_class=HTMLResponse)
async def schedule_content_form(
    request: Request,
    content_id: str,
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    connector_ids: List[str] = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for scheduling content via form."""
    try:
        # Parse datetime
        scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
        scheduled_at = datetime.strptime(scheduled_datetime_str, "%Y-%m-%d %H:%M")

        content = await service.schedule_content(
            content_id=content_id,
            scheduled_at=scheduled_at,
            connector_ids=connector_ids,
            updated_by=current_user.id
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Return updated content table
        result = await service.get_content_list(limit=50, offset=0)

        return templates.TemplateResponse(
            "content_broadcaster/partials/list_content.html",
            {
                "request": request,
                "content_items": result["data"],
                "total": result["total"],
                "show_success": True,
                "success_message": f"Content '{content.title}' scheduled for {scheduled_at.strftime('%Y-%m-%d %H:%M')}"
            }
        )

    except ValueError as e:
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": str(e)}
        )
    except Exception as e:
        logger.exception(f"Failed to schedule content {content_id}")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to schedule content"}
        )

@router.post("/approve/{content_id}", response_class=HTMLResponse)
async def approve_content_form(
    request: Request,
    content_id: str,
    comment: Optional[str] = Form(default=None),
    auto_schedule: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """HTMX endpoint for approving content via form."""
    try:
        content = await service.approve_content(
            content_id=content_id,
            approved_by=current_user,
            comment=comment,
            auto_schedule=auto_schedule
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Return updated content table
        result = await service.get_content_list(limit=50, offset=0)

        return templates.TemplateResponse(
            "content_broadcaster/partials/list_content.html",
            {
                "request": request,
                "content_items": result["data"],
                "total": result["total"],
                "show_success": True,
                "success_message": f"Content '{content.title}' approved successfully"
            }
        )

    except ValueError as e:
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": str(e)}
        )
    except Exception as e:
        logger.exception(f"Failed to approve content {content_id}")
        return templates.TemplateResponse(
            "components/errors/error_message.html",
            {"request": request, "message": "Failed to approve content"}
        )
