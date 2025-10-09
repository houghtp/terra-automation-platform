"""
Content Broadcaster external API routes.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import get_db, get_async_session
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from .models import (
    ContentCreateRequest, ContentScheduleRequest, ApprovalRequest,
    RejectRequest, SEOContentGenerationRequest
)
from ..models import JobStatus
from ..services import ContentBroadcasterService


async def get_content_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
) -> ContentBroadcasterService:
    """Get Content Broadcaster service with tenant context."""
    return ContentBroadcasterService(session, tenant_id)
from ..services import ContentBroadcasterService
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["content-broadcaster-api"])

# --- EXTERNAL API ROUTES ---

@router.post("/api/create")
async def create_content(
    request: ContentCreateRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to create new content."""
    try:
        content = await service.create_content(
            title=request.title,
            body=request.body,
            created_by_user=current_user,
            metadata=request.metadata,
            tags=request.tags
        )
        return content.to_dict()

    except Exception as e:
        logger.exception("Failed to create content")
        raise HTTPException(status_code=500, detail="Failed to create content")

@router.post("/api/{content_id}/submit")
async def submit_for_review(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to submit content for review."""
    try:
        content = await service.submit_for_review(content_id, current_user.id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return content.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to submit content {content_id} for review")
        raise HTTPException(status_code=500, detail="Failed to submit content")

@router.post("/api/{content_id}/approve")
async def approve_content(
    content_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to approve content."""
    try:
        content = await service.approve_content(
            content_id=content_id,
            approved_by=current_user,
            comment=request.comment,
            auto_schedule=request.auto_schedule
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return content.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to approve content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to approve content")

@router.post("/api/{content_id}/reject")
async def reject_content(
    content_id: str,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to reject content."""
    try:
        content = await service.reject_content(
            content_id=content_id,
            rejected_by=current_user,
            comment=request.comment
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return content.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to reject content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to reject content")

@router.post("/api/{content_id}/schedule")
async def schedule_content(
    content_id: str,
    request: ContentScheduleRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to schedule content for publishing."""
    try:
        content = await service.schedule_content(
            content_id=content_id,
            scheduled_at=request.scheduled_at,
            connector_ids=request.connector_ids,
            updated_by=current_user.id
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return content.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to schedule content {content_id}")
        raise HTTPException(status_code=500, detail="Failed to schedule content")

@router.post("/api/generate-seo-content")
async def generate_seo_content(
    request: SEOContentGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to generate SEO-optimized content using AI."""
    try:
        # Import here to avoid circular imports
        from app.features.core.connectors.seo_content_generator import create_seo_content_generator

        # Create content generator
        generator = await create_seo_content_generator(
            tenant_id=tenant_id,
            min_seo_score=request.min_seo_score,
            max_iterations=request.max_iterations
        )

        # Start content generation in background
        background_tasks.add_task(
            _generate_content_background,
            generator,
            request.title,
            current_user.id,
            request.ai_provider,
            request.fallback_ai,
            request.search_provider,
            request.scraping_provider,
            request.auto_approve
        )

        return {
            "message": f"SEO content generation started for '{request.title}'",
            "title": request.title,
            "status": "generating",
            "estimated_time": "3-5 minutes"
        }

    except Exception as e:
        logger.exception(f"Failed to start SEO content generation for '{request.title}'")
        raise HTTPException(status_code=500, detail=f"Failed to start content generation: {str(e)}")

@router.get("/api/jobs")
async def get_jobs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to get background jobs."""
    try:
        # Parse status enum
        status_enum = None
        if status:
            try:
                status_enum = JobStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        jobs = await service.get_jobs(
            limit=limit,
            offset=offset,
            status=status_enum
        )
        return {"data": [job.to_dict() for job in jobs]}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get jobs")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")

@router.post("/api/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to retry a failed job."""
    try:
        job = await service.retry_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to retry job {job_id}")
        raise HTTPException(status_code=500, detail="Failed to retry job")

@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to cancel a running job."""
    try:
        job = await service.cancel_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to cancel job {job_id}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")

# --- Background Tasks ---

async def _generate_content_background(
    generator,
    title: str,
    created_by: str,
    ai_provider: str,
    fallback_ai: Optional[str],
    search_provider: str,
    scraping_provider: str,
    auto_approve: bool
):
    """Background task for SEO content generation."""
    try:
        logger.info(f"Starting background SEO content generation for: '{title}'")

        # Generate content
        content_item = await generator.generate_content_from_title(
            title=title,
            created_by=created_by,
            ai_provider=ai_provider,
            fallback_ai=fallback_ai,
            search_provider=search_provider,
            scraping_provider=scraping_provider
        )

        # Auto-approve if requested and score is high enough
        if auto_approve and content_item.content_metadata:
            seo_score = content_item.content_metadata.get("seo_score", 0)
            if seo_score >= generator.min_seo_score:
                async with get_async_session() as session:
                    content_service = ContentBroadcasterService(session, generator.tenant_id)
                    await content_service.approve_content(
                        content_id=content_item.id,
                        approved_by=created_by,
                        comment=f"Auto-approved: SEO score {seo_score}/100",
                        auto_schedule=False
                    )

        logger.info(f"Successfully generated SEO content for '{title}': {content_item.id}")

    except Exception as e:
        logger.error(f"Background SEO content generation failed for '{title}': {str(e)}")
        # TODO: Consider saving error state to content item or notification system
