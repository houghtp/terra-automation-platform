"""
Content Planning Routes - Manage AI-driven content generation plans.

These routes handle the content planning workflow where users submit
content ideas that get processed by AI to generate draft content.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Union, Dict, Any, Tuple
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import Response, HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.core.database import get_db
from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.templates import templates
from app.features.core.config import get_settings
from app.features.administration.secrets.services import SecretsManagementService
from app.features.administration.ai_prompts.services import AIPromptService
from app.features.core.route_imports import is_global_admin
from app.features.core.audit_mixin import AuditContext
from app.features.core.task_manager import process_content_plan_async as enqueue_content_plan_task

from ..models import ContentItem, ContentPlanStatus
from ..schemas import ContentPlanCreate, ProcessPlanRequest
from ..services.content_planning_service import ContentPlanningService
from ..services.content_orchestrator_service import ContentOrchestratorService
from ..services.prompt_templates import PROMPT_DEFAULTS
from ..tasks import run_plan_generation

logger = get_logger(__name__)
settings = get_settings()
USE_CELERY_FOR_PLANS = bool(getattr(settings, "CONTENT_BROADCASTER_USE_CELERY", False))

router = APIRouter(prefix="/planning", tags=["Content Planning"])

CONTENT_PROMPT_DEFINITIONS: List[Dict[str, Any]] = [
    {"key": "seo_blog_generation", "label": "SEO Blog Draft Generation"},
    {"key": "seo_competitor_analysis", "label": "Competitor Analysis"},
    {"key": "seo_content_validation", "label": "SEO Content Validation"},
    {"key": "channel_variant_linkedin", "label": "LinkedIn Variant"},
    {"key": "channel_variant_twitter", "label": "Twitter/X Variant"},
    {"key": "channel_variant_wordpress", "label": "WordPress Variant"},
    {"key": "channel_variant_medium", "label": "Medium Variant"},
    {"key": "channel_variant_facebook", "label": "Facebook Variant"},
]


async def _get_prompt_entries(db: AsyncSession, tenant_id: str) -> List[Dict[str, Any]]:
    prompt_service = AIPromptService(db)
    for definition in CONTENT_PROMPT_DEFINITIONS:
        defaults = PROMPT_DEFAULTS.get(definition["key"])
        if defaults:
            await prompt_service.ensure_system_prompt(definition["key"], defaults)
    available_prompts = await prompt_service.list_prompts(
        tenant_id=tenant_id,
        include_system=True
    )

    prompt_entries: List[Dict[str, Any]] = []
    for prompt_def in CONTENT_PROMPT_DEFINITIONS:
        key = prompt_def["key"]
        tenant_prompt = next(
            (p for p in available_prompts if p.prompt_key == key and p.tenant_id == tenant_id),
            None
        )
        system_prompt = next(
            (p for p in available_prompts if p.prompt_key == key and (p.tenant_id is None or p.is_system)),
            None
        )
        active_prompt = tenant_prompt or system_prompt

        prompt_entries.append({
            "definition": prompt_def,
            "active_prompt": active_prompt,
            "tenant_prompt": tenant_prompt,
            "system_prompt": system_prompt
        })

    return prompt_entries


async def _run_plan_generation_in_app(plan_id: str, tenant_id: str, triggered_by: Dict[str, Any]):
    """
    Fallback path to process a content plan within the FastAPI app process.
    Avoids the need for Celery in development environments.
    """
    try:
        await run_plan_generation(plan_id=plan_id, tenant_id=tenant_id, triggered_by=triggered_by)
    except Exception:
        logger.exception(
            "In-process content plan generation failed",
            plan_id=plan_id,
            tenant_id=tenant_id
        )


async def _build_run_history_context(plan, db: AsyncSession, tenant_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, ContentItem]]:
    generation_meta = plan.generation_metadata or {}
    raw_history = generation_meta.get("run_history") or []
    current_run_id = generation_meta.get("current_run_id")
    published_run_id = generation_meta.get("published_run_id")
    run_history: List[Dict[str, Any]] = []

    for entry in sorted(raw_history, key=lambda e: e.get("created_at", ""), reverse=True):
        entry_copy = dict(entry)
        entry_copy.setdefault("run_id", entry_copy.get("content_item_id"))
        params = entry_copy.get("parameters") or {}
        if not params:
            params = {
                "tone": plan.tone,
                "skip_research": plan.skip_research,
                "target_channels": plan.target_channels or [],
                "prompt_settings": plan.prompt_settings or {}
            }
        entry_copy["parameters"] = params
        sub_scores = entry_copy.get("sub_scores") or {}
        for key in ["keyword_coverage", "structure", "readability", "engagement", "technical"]:
            sub_scores.setdefault(key, 0)
        entry_copy["sub_scores"] = sub_scores
        sub_score_details = entry_copy.get("sub_score_details") or {}
        for key in ["keyword_coverage", "structure", "readability", "engagement", "technical"]:
            sub_score_details.setdefault(key, "")
        entry_copy["sub_score_details"] = sub_score_details
        if entry_copy.get("validation_metadata") is None and entry_copy.get("metadata"):
            entry_copy["validation_metadata"] = entry_copy["metadata"]
        if entry_copy.get("validation_metadata") is None:
            entry_copy["validation_metadata"] = {}
        if not entry_copy.get("refinement_history") and entry_copy.get("refinement_history_snapshot"):
            entry_copy["refinement_history"] = entry_copy["refinement_history_snapshot"]

        identifier = entry_copy.get("run_id")
        status = entry_copy.get("status")
        if published_run_id and identifier == published_run_id:
            status = "published"
        elif current_run_id and identifier == current_run_id:
            status = "current"
        elif not status:
            status = "archived"
        entry_copy["status"] = status
        entry_copy["human_edited"] = bool(entry_copy.get("human_edited"))

        run_history.append(entry_copy)

    run_ids = [entry.get("content_item_id") for entry in run_history if entry.get("content_item_id")]
    run_content_map: Dict[str, ContentItem] = {}
    if run_ids:
        stmt = select(ContentItem).where(
            ContentItem.id.in_(run_ids),
            ContentItem.tenant_id == tenant_id
        )
        run_result = await db.execute(stmt)
        run_content_map = {item.id: item for item in run_result.scalars().all()}

    return run_history, run_content_map


def _resolve_selected_run(
    plan,
    run_history: List[Dict[str, Any]],
    run_content_map: Dict[str, ContentItem],
    preferred_run_id: Optional[str],
    fallback_content: Optional[ContentItem]
) -> Tuple[Optional[Dict[str, Any]], Optional[ContentItem], Optional[str]]:
    selected = None
    normalized_id = preferred_run_id
    if normalized_id:
        selected = next(
            (
                entry for entry in run_history
                if entry.get("run_id") == normalized_id or entry.get("content_item_id") == normalized_id
            ),
            None
        )
    if not selected:
        selected = next((entry for entry in run_history if entry.get("status") == "published"), None)
    if not selected:
        selected = next((entry for entry in run_history if entry.get("status") == "current"), None)
    if not selected and run_history:
        selected = run_history[0]

    selected_content = None
    selected_run_id = None
    if selected:
        selected_run_id = selected.get("run_id") or selected.get("content_item_id")
        if selected.get("content_item_id"):
            selected_content = run_content_map.get(selected["content_item_id"])

    if not selected_content:
        selected_content = fallback_content

    return selected, selected_content, selected_run_id


async def _get_openai_api_key(
    db: AsyncSession,
    tenant_id: str,
    current_user
) -> str:
    """Fetch OpenAI API key from Secrets Management."""
    secrets_service = SecretsManagementService(db, tenant_id)
    openai_secret = await secrets_service.get_secret_by_name("OpenAI API Key")

    if not openai_secret:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key not configured. Please add 'OpenAI_API_Key' in Secrets Management."
        )

    secret_value = await secrets_service.get_secret_value(
        secret_id=openai_secret.id,
        accessed_by_user=current_user
    )

    if not secret_value:
        raise HTTPException(
            status_code=400,
            detail="Failed to retrieve OpenAI API key value."
        )

    return secret_value.value

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
            prompt_settings=plan_data.prompt_settings,
            created_by_user=current_user  # Pass user object for better audit trail
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
            "message": "Content plan created successfully. Use /planning/{plan_id}/process-async to generate content."
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
    professionalism_level: int = Form(4),
    creativity_level: int = Form(3),
    humor_level: int = Form(1),
    analysis_depth: int = Form(4),
    strictness_level: int = Form(4),
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

        if skip_research_bool:
            sufficient_description = description and len(description.strip()) >= 20
            sufficient_keywords = keywords and len(keywords) >= 2
            sufficient_competitors = urls and len(urls) > 0

            if not (sufficient_description or sufficient_keywords or sufficient_competitors):
                logger.warning(
                    "Skip research enabled without additional guidance",
                    plan_title=title,
                    tenant_id=tenant_id
                )
            elif not sufficient_keywords:
                logger.warning(
                    "Direct generation without keywords",
                    plan_title=title,
                    tenant_id=tenant_id
                )

        service = ContentPlanningService(db, tenant_id)

        prompt_settings = {
            "professionalism_level": professionalism_level,
            "creativity_level": creativity_level,
            "humor_level": humor_level,
            "analysis_depth": analysis_depth,
            "strictness_level": strictness_level,
        }

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
            prompt_settings=prompt_settings,
            created_by_user=current_user  # Pass user object for better audit trail
        )

        await db.commit()

        logger.info("Content plan created from form", plan_id=plan.id, tenant_id=tenant_id)

        # Return empty response with HX-Trigger header to trigger client-side events
        # Multiple events in one header trigger in order
        response = Response(status_code=204)  # 204 No Content is standard for successful form submission
        response.headers["HX-Trigger"] = "closeModal, refreshTable, showSuccess"
        return response

    except ValueError as e:
        logger.warning(
            "Validation error updating content plan",
            plan_id=plan_id,
            tenant_id=tenant_id,
            error=str(e)
        )
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
async def list_plans_api(
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """
    Get content plans list for Tabulator table (standardized pattern).
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        result = await service.list_plans(limit=limit, offset=offset)

        # Return simple array for Tabulator
        plans = result.get("data", [])
        return plans  # Already converted to dict by service

    except Exception as e:
        logger.exception("Failed to get plans for table", tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load content plans")


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
        try:
            plan = await service.get_plan(plan_id)
        except ValueError:
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
        try:
            plan = await service.get_plan(plan_id)
        except ValueError:
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
    professionalism_level: int = Form(4),
    creativity_level: int = Form(3),
    humor_level: int = Form(1),
    analysis_depth: int = Form(4),
    strictness_level: int = Form(4),
    skip_research: Optional[str] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update content plan from form submission.
    """
    try:
        service = ContentPlanningService(db, tenant_id)
        existing_plan = await service.get_plan(plan_id)

        if not existing_plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

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

        # Use existing values when fields are not supplied
        combined_description = description.strip() if description else (existing_plan.description or "")
        combined_keywords = keywords if keywords is not None else (existing_plan.seo_keywords or [])
        combined_urls = urls if urls is not None else (existing_plan.competitor_urls or [])

        # Guidance if skipping research
        if skip_research_bool:
            has_sufficient_description = len(combined_description.strip()) >= 20
            has_keyword_guidance = combined_keywords and len(combined_keywords) >= 2
            has_competitor_context = combined_urls and len(combined_urls) > 0

            if not (has_sufficient_description or has_keyword_guidance or has_competitor_context):
                logger.warning(
                    "Skip research enabled without additional guidance",
                    plan_id=plan_id,
                    tenant_id=tenant_id
                )
            elif not has_keyword_guidance:
                logger.warning(
                    "Direct generation without keywords",
                    plan_id=plan_id,
                    tenant_id=tenant_id
                )

        plan = existing_plan
        plan.title = title.strip()
        plan.description = combined_description or None
        plan.tone = tone
        plan.target_audience = target_audience
        plan.target_channels = target_channel_values
        plan.seo_keywords = combined_keywords
        plan.competitor_urls = combined_urls
        plan.min_seo_score = min_seo_score
        plan.max_iterations = max_iterations
        plan.skip_research = skip_research_bool
        plan.prompt_settings = service._normalise_prompt_settings({
            "professionalism_level": professionalism_level,
            "creativity_level": creativity_level,
            "humor_level": humor_level,
            "analysis_depth": analysis_depth,
            "strictness_level": strictness_level,
        })

        if current_user:
            audit_ctx = AuditContext.from_user(current_user)
            plan.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
        plan.updated_at = datetime.now()

        await db.flush()

        service.log_operation("content_plan_updated", {
            "plan_id": plan.id,
            "updates": [
                "title", "description", "tone", "target_audience",
                "target_channels", "seo_keywords", "competitor_urls",
                "min_seo_score", "max_iterations", "skip_research", "prompt_settings"
            ]
        })

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

        # Aggregate generation run history
        run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
        preferred_run_id = request.query_params.get("run_id")
        selected_run, selected_content_item, selected_run_id = _resolve_selected_run(
            plan,
            run_history,
            run_content_map,
            preferred_run_id,
            content_item
        )

        # Gather AI prompts relevant to Content Broadcaster
        prompt_entries = await _get_prompt_entries(db, tenant_id)

        return templates.TemplateResponse(
            "content_broadcaster/view_plan.html",
            {
                "request": request,
                "plan": plan,
                "content": selected_content_item,
                "selected_run": selected_run,
                "selected_run_id": selected_run_id,
                "current_user": current_user,
                "prompt_entries": prompt_entries,
                "has_tenant_prompt_access": is_global_admin(current_user) or plan.tenant_id == tenant_id,
                "is_global_admin_user": is_global_admin(current_user),
                "tenant_id": tenant_id,
                "run_history": run_history,
                "run_content_map": run_content_map
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load plan view", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load plan view")


@router.get("/{plan_id}/partials/prompts", response_class=HTMLResponse)
async def get_plan_prompts_partial(
    request: Request,
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return AI prompts panel partial for a content plan."""
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.get_plan(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        prompt_entries = await _get_prompt_entries(db, tenant_id)

        return templates.TemplateResponse(
            "content_broadcaster/partials/ai_prompts_tab.html",
            {
                "request": request,
                "plan": plan,
                "prompt_entries": prompt_entries,
                "has_tenant_prompt_access": is_global_admin(current_user) or plan.tenant_id == tenant_id,
                "is_global_admin_user": is_global_admin(current_user),
                "tenant_id": tenant_id
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load prompts partial", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load prompts") from exc


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


@router.get("/{plan_id}/runs/{content_id}/view", response_class=HTMLResponse)
async def view_generation_run(
    request: Request,
    plan_id: str,
    content_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return modal content for a specific generation run."""
    try:
        service = ContentPlanningService(db, tenant_id)
        plan = await service.get_plan(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Content plan not found")

        stmt = select(ContentItem).where(
            ContentItem.id == content_id,
            ContentItem.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        content_item = result.scalar_one_or_none()

        if not content_item:
            raise HTTPException(status_code=404, detail="Content run not found")

        metadata = content_item.content_metadata or {}
        if metadata.get("generated_from_plan") != plan_id:
            raise HTTPException(status_code=403, detail="Content run does not belong to this plan")

        return templates.TemplateResponse(
            "content_broadcaster/partials/view_content_modal.html",
            {
                "request": request,
                "content": content_item,
                "plan": plan,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load run content", plan_id=plan_id, tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load run") from exc


@router.post("/{plan_id}/runs/{run_id}/status", response_class=HTMLResponse)
async def update_run_status(
    request: Request,
    plan_id: str,
    run_id: str,
    status: str = Form(...),
    selected_run_id: Optional[str] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a generation run's status (current/published) and refresh the run table."""
    status_normalized = (status or "").lower()
    service = ContentPlanningService(db, tenant_id)

    try:
        await service.set_run_status(plan_id, run_id, status_normalized)
    except ValueError as exc:
        await db.rollback()
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {
                "request": request,
                "message": str(exc)
            },
            status_code=400
        )

    await db.commit()
    plan = await service.get_plan(plan_id)
    content_item = None
    if plan.generated_content_item_id:
        stmt = select(ContentItem).where(
            ContentItem.id == plan.generated_content_item_id,
            ContentItem.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        content_item = result.scalar_one_or_none()

    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    preferred = selected_run_id or run_id
    selected_run, selected_content_item, resolved_selected_run_id = _resolve_selected_run(
        plan,
        run_history,
        run_content_map,
        preferred,
        content_item
    )

    response = templates.TemplateResponse(
        "content_broadcaster/partials/plan_run_detail_block.html",
        {
            "request": request,
            "plan": plan,
            "run_history": run_history,
            "selected_run": selected_run,
            "selected_run_id": resolved_selected_run_id,
            "content": selected_content_item
        }
    )
    response.headers["HX-Trigger"] = "showSuccess"
    return response


@router.get("/{plan_id}/runs/{run_id}/edit", response_class=HTMLResponse)
async def edit_run_content_form(
    request: Request,
    plan_id: str,
    run_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Render modal form to edit run content."""
    service = ContentPlanningService(db, tenant_id)
    plan = await service.get_plan(plan_id)

    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    run_entry = next(
        (
            entry for entry in run_history
            if entry.get("run_id") == run_id or entry.get("content_item_id") == run_id
        ),
        None
    )

    if not run_entry:
        raise HTTPException(status_code=404, detail="Run not found")

    content_item = None
    content_item_id = run_entry.get("content_item_id")
    if content_item_id:
        content_item = run_content_map.get(content_item_id)
    if not content_item and plan.generated_content_item_id:
        content_item = run_content_map.get(plan.generated_content_item_id)

    if not content_item:
        raise HTTPException(status_code=404, detail="Content item not found for this run")

    return templates.TemplateResponse(
        "content_broadcaster/partials/run_content_edit_form.html",
        {
            "request": request,
            "plan": plan,
            "run": run_entry,
            "run_id": run_id,
            "content_item": content_item
        }
    )


@router.post("/{plan_id}/runs/{run_id}/edit", response_class=HTMLResponse)
async def update_run_content(
    request: Request,
    plan_id: str,
    run_id: str,
    title: str = Form(...),
    body: str = Form(...),
    edit_notes: Optional[str] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Persist manual edits to run content."""
    service = ContentPlanningService(db, tenant_id)
    try:
        await service.update_run_content(
            plan_id=plan_id,
            run_id=run_id,
            title=title,
            body=body,
            edited_by_user=current_user,
            edit_notes=edit_notes
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {"request": request, "message": str(exc)},
            status_code=400
        )

    plan = await service.get_plan(plan_id)
    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    fallback_content = None
    if plan.generated_content_item_id:
        fallback_content = run_content_map.get(plan.generated_content_item_id)

    selected_run, selected_content_item, resolved_selected_run_id = _resolve_selected_run(
        plan,
        run_history,
        run_content_map,
        run_id,
        fallback_content
    )

    response = templates.TemplateResponse(
        "content_broadcaster/partials/plan_run_detail_block.html",
        {
            "request": request,
            "plan": plan,
            "run_history": run_history,
            "selected_run": selected_run,
            "selected_run_id": resolved_selected_run_id,
            "content": selected_content_item
        }
    )
    response.headers["HX-Trigger"] = "closeModal, showSuccess"
    return response


@router.post("/{plan_id}/runs/{run_id}/validate", response_class=HTMLResponse)
async def rerun_seo_validation(
    request: Request,
    plan_id: str,
    run_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Re-run SEO validation for manually edited content."""
    openai_api_key = await _get_openai_api_key(db, tenant_id, current_user)
    service = ContentPlanningService(db, tenant_id)
    try:
        await service.rerun_seo_validation(plan_id, run_id, openai_api_key)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {"request": request, "message": str(exc)},
            status_code=400
        )

    plan = await service.get_plan(plan_id)
    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    fallback_content = None
    if plan.generated_content_item_id:
        fallback_content = run_content_map.get(plan.generated_content_item_id)

    selected_run, selected_content_item, resolved_selected_run_id = _resolve_selected_run(
        plan,
        run_history,
        run_content_map,
        run_id,
        fallback_content
    )

    response = templates.TemplateResponse(
        "content_broadcaster/partials/plan_run_detail_block.html",
        {
            "request": request,
            "plan": plan,
            "run_history": run_history,
            "selected_run": selected_run,
            "selected_run_id": resolved_selected_run_id,
            "content": selected_content_item
        }
    )
    response.headers["HX-Trigger"] = "showSuccess"
    return response


@router.get("/{plan_id}/runs/{run_id}/edit", response_class=HTMLResponse)
async def edit_run_content_form(
    request: Request,
    plan_id: str,
    run_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Render modal form for editing run content."""
    service = ContentPlanningService(db, tenant_id)
    plan = await service.get_plan(plan_id)

    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    run_entry = next(
        (
            entry for entry in run_history
            if entry.get("run_id") == run_id or entry.get("content_item_id") == run_id
        ),
        None
    )

    if not run_entry:
        raise HTTPException(status_code=404, detail="Run not found")

    content_item = None
    content_item_id = run_entry.get("content_item_id")
    if content_item_id:
        content_item = run_content_map.get(content_item_id)
    if not content_item and plan.generated_content_item_id:
        content_item = run_content_map.get(plan.generated_content_item_id)

    if not content_item:
        raise HTTPException(status_code=404, detail="Content item not found for this run")

    return templates.TemplateResponse(
        "content_broadcaster/partials/run_content_edit_form.html",
        {
            "request": request,
            "plan": plan,
            "run": run_entry,
            "content_item": content_item,
            "run_id": run_id
        }
    )


@router.post("/{plan_id}/runs/{run_id}/edit", response_class=HTMLResponse)
async def update_run_content(
    request: Request,
    plan_id: str,
    run_id: str,
    title: str = Form(...),
    body: str = Form(...),
    edit_notes: Optional[str] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save human edits to run content."""
    service = ContentPlanningService(db, tenant_id)
    try:
        await service.update_run_content(
            plan_id=plan_id,
            run_id=run_id,
            title=title,
            body=body,
            edited_by_user=current_user,
            edit_notes=edit_notes
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {"request": request, "message": str(exc)},
            status_code=400
        )

    plan = await service.get_plan(plan_id)
    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    fallback_content = None
    if plan.generated_content_item_id:
        fallback_content = run_content_map.get(plan.generated_content_item_id)

    selected_run, selected_content_item, resolved_selected_run_id = _resolve_selected_run(
        plan,
        run_history,
        run_content_map,
        run_id,
        fallback_content
    )

    response = templates.TemplateResponse(
        "content_broadcaster/partials/plan_run_detail_block.html",
        {
            "request": request,
            "plan": plan,
            "run_history": run_history,
            "selected_run": selected_run,
            "selected_run_id": resolved_selected_run_id,
            "content": selected_content_item
        }
    )
    response.headers["HX-Trigger"] = "closeModal, showSuccess"
    return response


@router.delete("/{plan_id}/prompts/{prompt_id}")
async def delete_prompt_override(
    plan_id: str,
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a tenant-specific prompt override for the Content Broadcaster prompts."""
    plan_service = ContentPlanningService(db, tenant_id)
    try:
        plan = await plan_service.get_plan(plan_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Content plan not found")

    prompt_service = AIPromptService(db)
    prompt = await prompt_service.get_prompt_by_id(prompt_id)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if prompt.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot modify prompt for another tenant")

    if prompt.is_system:
        raise HTTPException(status_code=400, detail="System prompts cannot be removed from this view")

    success = await prompt_service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to deactivate prompt")

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "refreshPromptTable"
    return response


@router.post("/{plan_id}/process-async")
async def enqueue_content_plan_processing(
    plan_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Queue content plan processing via Celery so the UI remains responsive.
    """
    service = ContentPlanningService(db, tenant_id)

    try:
        plan = await service.get_plan(plan_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Content plan not found")

    in_progress_statuses = {
        ContentPlanStatus.RESEARCHING.value,
        ContentPlanStatus.GENERATING.value,
        ContentPlanStatus.REFINING.value,
    }

    if plan.status in in_progress_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Plan is already being processed (current status: {plan.status})"
        )

    # Optimistically move to researching so the table reflects background work.
    await service.update_plan_status(
        plan_id,
        ContentPlanStatus.RESEARCHING.value,
        {"error_log": None}
    )
    await db.commit()

    triggered_by = {
        "id": getattr(current_user, "id", None),
        "email": getattr(current_user, "email", None),
        "name": getattr(current_user, "name", None),
    }

    task_id = None

    async def enqueue_locally():
        await _run_plan_generation_in_app(plan_id, tenant_id, triggered_by)

    if USE_CELERY_FOR_PLANS:
        try:
            task_id = enqueue_content_plan_task(
                plan_id=plan_id,
                tenant_id=tenant_id,
                triggered_by=triggered_by
            )
        except Exception:
            logger.exception(
                "Failed to enqueue plan via Celery, falling back to local execution",
                plan_id=plan_id,
                tenant_id=tenant_id
            )
            task_id = f"inproc-{plan_id}-{uuid4().hex}"
            asyncio.create_task(enqueue_locally())
    else:
        task_id = f"inproc-{plan_id}-{uuid4().hex}"
        asyncio.create_task(enqueue_locally())

    headers = {"HX-Trigger": "showSuccess"}
    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "plan_id": plan_id,
            "task_id": task_id,
            "message": "Content plan queued for AI processing.",
        },
        headers=headers
    )


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
        openai_api_key = await _get_openai_api_key(db, tenant_id, current_user)

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
            "message": "Content plan reset for retry. Use /planning/{plan_id}/process-async to regenerate."
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
@router.get("/{plan_id}/runs/{run_id}/select", response_class=HTMLResponse)
async def select_generation_run(
    request: Request,
    plan_id: str,
    run_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ContentPlanningService(db, tenant_id)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Content plan not found")

    content_item = None
    if plan.generated_content_item_id:
        stmt = select(ContentItem).where(
            ContentItem.id == plan.generated_content_item_id,
            ContentItem.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        content_item = result.scalar_one_or_none()

    run_history, run_content_map = await _build_run_history_context(plan, db, tenant_id)
    selected_run, selected_content_item, selected_run_id = _resolve_selected_run(
        plan,
        run_history,
        run_content_map,
        run_id,
        content_item
    )

    return templates.TemplateResponse(
        "content_broadcaster/partials/plan_run_detail_block.html",
        {
            "request": request,
            "plan": plan,
            "run_history": run_history,
            "selected_run": selected_run,
            "selected_run_id": selected_run_id,
            "content": selected_content_item
        }
    )
