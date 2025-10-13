"""
Content Planning Routes - Manage AI-driven content generation plans.

These routes handle the content planning workflow where users submit
content ideas that get processed by AI to generate draft content.
"""

from typing import Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.core.database import get_db
from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.templates import templates
from app.features.administration.secrets.services import SecretsManagementService

from ..models import ContentItem
from ..services.content_planning_service import ContentPlanningService
from ..services.content_orchestrator_service import ContentOrchestratorService

logger = get_logger(__name__)

router = APIRouter(prefix="/planning", tags=["Content Planning"])


# ==================== Request Models ====================

class ContentPlanCreate(BaseModel):
    """Request model for creating a content plan."""

    title: str = Field(..., min_length=3, max_length=500, description="Content topic or idea")
    description: Optional[str] = Field(None, description="Additional context or instructions")
    target_channels: Optional[List[str]] = Field(
        default=None,
        description="Target channels (e.g., ['wordpress', 'twitter'])"
    )
    target_audience: Optional[str] = Field(None, description="Target audience description")
    tone: Optional[str] = Field("professional", description="Writing tone")
    seo_keywords: Optional[List[str]] = Field(default=None, description="SEO keywords")
    competitor_urls: Optional[List[str]] = Field(
        default=None,
        description="Competitor URLs to analyze"
    )
    min_seo_score: int = Field(95, ge=80, le=100, description="Target SEO score")
    max_iterations: int = Field(3, ge=1, le=5, description="Max refinement iterations")


class ProcessPlanRequest(BaseModel):
    """Request model for processing a content plan with AI."""

    use_research: bool = Field(
        default=True,
        description="Whether to perform competitor research"
    )


# ==================== Routes ====================

@router.post("/create")
async def create_content_plan(
    request: Request,
    plan_data: ContentPlanCreate,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new content plan.

    A content plan represents a content idea that will be processed by AI
    to generate a draft blog post with SEO optimization.
    """
    try:
        service = ContentPlanningService(db, tenant_id)

        plan = await service.create_plan(
            title=plan_data.title,
            description=plan_data.description,
            target_channels=plan_data.target_channels,
            target_audience=plan_data.target_audience,
            tone=plan_data.tone,
            seo_keywords=plan_data.seo_keywords,
            competitor_urls=plan_data.competitor_urls,
            min_seo_score=plan_data.min_seo_score,
            max_iterations=plan_data.max_iterations,
            created_by=current_user  # Pass user object for better audit trail
        )

        await db.commit()

        logger.info(
            "Content plan created",
            plan_id=plan.id,
            title=plan.title,
            tenant_id=tenant_id,
            user_id=current_user.id
        )

        return {
            "success": True,
            "plan_id": plan.id,
            "title": plan.title,
            "status": plan.status,
            "message": "Content plan created successfully. Use /planning/{plan_id}/process to generate content."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create content plan", tenant_id=tenant_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create content plan")


@router.post("/api/create")
async def create_plan_from_form(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tone: str = Form("professional"),
    target_audience: Optional[str] = Form(None),
    target_channels: List[str] = Form(default=[]),
    seo_keywords: Optional[str] = Form(None),
    competitor_urls: Optional[str] = Form(None),
    min_seo_score: int = Form(95),
    max_iterations: int = Form(3),
    skip_research: Optional[str] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create content plan from HTML form submission.
    """
    try:
        # Parse SEO keywords
        keywords = None
        if seo_keywords:
            keywords = [k.strip() for k in seo_keywords.split(',') if k.strip()]

        # Parse competitor URLs
        urls = None
        if competitor_urls:
            urls = [u.strip() for u in competitor_urls.split('\n') if u.strip()]

        # Parse skip_research checkbox (checkbox sends "true" string or None)
        skip_research_bool = skip_research == "true"

        # Validation: If skipping research, ensure sufficient information is provided
        if skip_research_bool:
            if not description or len(description.strip()) < 20:
                return templates.TemplateResponse(
                    "components/ui/error_message.html",
                    {
                        "request": request,
                        "message": "When skipping research, please provide a detailed description (at least 20 characters) to help AI generate quality content."
                    },
                    status_code=400
                )

            # Recommend keywords for better results
            if not keywords or len(keywords) < 2:
                logger.warning(
                    "Direct generation without keywords",
                    plan_title=title,
                    tenant_id=tenant_id
                )

        service = ContentPlanningService(db, tenant_id)

        plan = await service.create_plan(
            title=title,
            description=description,
            target_channels=target_channels if target_channels else [],
            target_audience=target_audience,
            tone=tone,
            seo_keywords=keywords if keywords else [],
            competitor_urls=urls if urls else [],
            min_seo_score=min_seo_score,
            max_iterations=max_iterations,
            skip_research=skip_research_bool,
            created_by=current_user  # Pass user object for better audit trail
        )

        await db.commit()

        logger.info("Content plan created from form", plan_id=plan.id, tenant_id=tenant_id)

        # Return empty response with HX-Trigger header to trigger client-side events
        # Multiple events in one header trigger in order
        response = Response(status_code=204)  # 204 No Content is standard for successful form submission
        response.headers["HX-Trigger"] = "closeModal, refreshTable, showSuccess"
        return response

    except ValueError as e:
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {
                "request": request,
                "message": str(e)
            },
            status_code=400
        )
    except Exception as e:
        logger.exception("Failed to create plan from form", tenant_id=tenant_id)
        await db.rollback()
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {
                "request": request,
                "message": "Failed to create content plan"
            },
            status_code=500
        )


@router.get("/list")
async def list_content_plans(
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None
):
    """
    List all content plans for the tenant.
    """
    try:
        service = ContentPlanningService(db, tenant_id)

        result = await service.list_plans(
            limit=limit,
            offset=offset,
            search=search
        )

        return result

    except Exception as e:
        logger.exception("Failed to list content plans", tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list content plans")


@router.get("/api/list")
async def get_plans_for_table(
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """
    Get content plans list for Tabulator table.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        result = await service.list_plans(limit=limit, offset=offset)

        # Return simple array for Tabulator
        plans = result.get("data", [])
        return plans  # Already converted to dict by service

    except Exception as e:
        logger.exception("Failed to get plans for table", tenant_id=tenant_id)
        return []


@router.get("/{plan_id}")
async def get_content_plan(
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific content plan.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.get_plan(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        return plan.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get content plan", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to get content plan")


@router.get("/{plan_id}/edit")
async def get_edit_plan_modal(
    request: Request,
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get edit modal for content plan.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.get_plan(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        return templates.TemplateResponse(
            "content_broadcaster/partials/edit_plan_modal.html",
            {
                "request": request,
                "plan": plan
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load edit form", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load edit form")


@router.post("/{plan_id}/edit")
async def update_content_plan(
    request: Request,
    plan_id: str,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tone: Optional[str] = Form("professional"),
    target_audience: Optional[str] = Form(None),
    target_channels: Union[str, List[str], None] = Form(None),
    seo_keywords: Optional[str] = Form(None),
    competitor_urls: Optional[str] = Form(None),
    min_seo_score: int = Form(95),
    max_iterations: int = Form(3),
    skip_research: Optional[str] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update content plan from form submission.
    """
    try:
        # Normalize channel selections (support single checkbox submission)
        if isinstance(target_channels, str):
            target_channel_values = [target_channels]
        elif isinstance(target_channels, list):
            target_channel_values = target_channels
        else:
            target_channel_values = []

        # Parse keywords
        keywords = None
        if seo_keywords:
            keywords = [k.strip() for k in seo_keywords.split(',') if k.strip()]

        # Parse competitor URLs
        urls = None
        if competitor_urls:
            urls = [u.strip() for u in competitor_urls.split('\n') if u.strip()]

        # Parse skip_research checkbox
        skip_research_bool = skip_research == "true"

        # Validation: If skipping research, ensure sufficient information is provided
        if skip_research_bool:
            if not description or len(description.strip()) < 20:
                return templates.TemplateResponse(
                    "components/ui/error_message.html",
                    {
                        "request": request,
                        "message": "When skipping research, please provide a detailed description (at least 20 characters) to help AI generate quality content."
                    },
                    status_code=400
                )

            # Recommend keywords for better results
            if not keywords or len(keywords) < 2:
                logger.warning(
                    "Direct generation without keywords",
                    plan_id=plan_id,
                    tenant_id=tenant_id
                )

        service = ContentPlanningService(db, tenant_id)

        # Update plan
        plan = await service.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        plan.title = title.strip()
        plan.description = description.strip() if description else None
        plan.tone = tone
        plan.target_audience = target_audience
        plan.target_channels = target_channel_values
        plan.seo_keywords = keywords if keywords else []
        plan.competitor_urls = urls if urls else []
        plan.min_seo_score = min_seo_score
        plan.max_iterations = max_iterations
        plan.skip_research = skip_research_bool

        await db.commit()

        logger.info("Content plan updated", plan_id=plan.id, tenant_id=tenant_id)

        # Return success response with HX-Trigger header
        response = Response(status_code=204)
        response.headers["HX-Trigger"] = "closeModal, refreshTable, showSuccess"
        return response

    except ValueError as e:
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {
                "request": request,
                "message": str(e)
            },
            status_code=400
        )
    except Exception as e:
        logger.exception("Failed to update plan", plan_id=plan_id, tenant_id=tenant_id)
        await db.rollback()
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {
                "request": request,
                "message": "Failed to update content plan"
            },
            status_code=500
        )


@router.get("/{plan_id}/view")
async def view_content_plan(
    request: Request,
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Full-page content plan viewer.
    Shows research data, generated content, and metadata in tabbed interface.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.get_plan(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        # Load generated content item if available
        content_item = None
        if plan.generated_content_item_id:
            stmt = select(ContentItem).where(
                ContentItem.id == plan.generated_content_item_id,
                ContentItem.tenant_id == tenant_id
            )
            result = await db.execute(stmt)
            content_item = result.scalar_one_or_none()

        return templates.TemplateResponse(
            "content_broadcaster/view_plan.html",
            {
                "request": request,
                "plan": plan,
                "content": content_item,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load plan view", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load plan view")


@router.get("/{plan_id}/partials/view_draft")
async def get_view_draft_modal(
    request: Request,
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get view draft modal for content plan (DEPRECATED - use /{plan_id}/view instead).
    Shows the generated content item in a modal for preview.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.get_plan(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        if not plan.generated_content_item_id:
            raise HTTPException(status_code=404, detail="No draft available for this plan")

        # Query the generated content item directly (avoid lazy loading in async)
        stmt = select(ContentItem).where(
            ContentItem.id == plan.generated_content_item_id,
            ContentItem.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        content_item = result.scalar_one_or_none()

        if not content_item:
            raise HTTPException(status_code=404, detail="Draft content not found")

        return templates.TemplateResponse(
            "content_broadcaster/partials/view_draft_modal.html",
            {
                "request": request,
                "plan": plan,
                "content": content_item
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load draft view", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load draft")


@router.post("/{plan_id}/process")
async def process_content_plan(
    plan_id: str,
    request: Request,
    use_research: bool = Form(True),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a content plan with AI to generate draft content.

    This endpoint demonstrates the complete AI workflow:
    1. Research competitor content (if use_research=true)
    2. Generate SEO-optimized blog post
    3. Create ContentItem with draft

    **Note:** This is a synchronous demo endpoint. In production, this should
    be handled by a Celery background worker.
    """
    logger.info(
        "🔥 PROCESS CONTENT PLAN ENDPOINT HIT",
        plan_id=plan_id,
        use_research=use_research,
        tenant_id=tenant_id,
        user_id=current_user.id
    )

    try:
        # Get API keys from secrets
        secrets_service = SecretsManagementService(db, tenant_id)

        # Step 1: Get secret metadata by name
        openai_secret = await secrets_service.get_secret_by_name("OpenAI API Key")

        if not openai_secret:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key not configured. Please add 'OpenAI_API_Key' in Secrets Management."
            )

        # Step 2: Get the actual decrypted value
        secret_value = await secrets_service.get_secret_value(
            secret_id=openai_secret.id,
            accessed_by_user=current_user
        )

        if not secret_value:
            raise HTTPException(
                status_code=400,
                detail="Failed to retrieve OpenAI API key value."
            )

        openai_api_key = secret_value.value

        # Process the plan
        # Note: Research phase will fetch scraping API keys internally from Secrets Management
        orchestrator = ContentOrchestratorService(db, tenant_id)

        result = await orchestrator.process_content_plan(
            plan_id=plan_id,
            openai_api_key=openai_api_key
        )

        logger.info(
            "Content plan processed successfully",
            plan_id=plan_id,
            content_item_id=result.get("content_item_id"),
            tenant_id=tenant_id
        )

        # Return 204 with HX-Trigger for HTMX pattern
        return Response(
            status_code=204,
            headers={
                "HX-Trigger": "refreshTable, showSuccess"
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to process content plan", plan_id=plan_id, tenant_id=tenant_id)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process content plan: {str(e)}"
        )


@router.post("/{plan_id}/retry")
async def retry_content_plan(
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry a failed content plan.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.retry_plan(plan_id)

        await db.commit()

        return {
            "success": True,
            "plan_id": plan.id,
            "status": plan.status,
            "retry_count": plan.retry_count,
            "message": "Content plan reset for retry. Use /planning/{plan_id}/process to regenerate."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to retry content plan", plan_id=plan_id, tenant_id=tenant_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retry content plan")


@router.delete("/{plan_id}")
@router.delete("/{plan_id}/delete")
@router.post("/{plan_id}/delete")
async def delete_content_plan(
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (archive) a content plan.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        success = await service.delete_plan(plan_id)

        if not success:
            raise HTTPException(status_code=404, detail="Content plan not found")

        await db.commit()

        logger.info("Content plan deleted", plan_id=plan_id, tenant_id=tenant_id)

        # Return 204 No Content for standard CRUD pattern
        return Response(status_code=204)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to delete content plan", plan_id=plan_id, tenant_id=tenant_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete content plan")
