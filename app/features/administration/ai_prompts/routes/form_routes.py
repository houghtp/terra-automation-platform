"""
HTMX form routes for AI prompt management.

Implements Phase 3 editing features including tenant overrides, template
validation, and variable detection helpers.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, Optional, List

from fastapi import status
from sqlalchemy import select

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    Request,
    HTTPException,
    HTMLResponse,
    Response,
    AsyncSession,
    templates,
    FormHandler,
    tenant_dependency,
    get_db,
    get_current_user,
    is_global_admin,
    get_logger,
    User,
)
from app.features.administration.ai_prompts.services import AIPromptService
from app.features.administration.ai_prompts.models import AIPrompt
from app.features.administration.tenants.db_models import Tenant

from .crud_routes import _prepare_prompt_payload

router = APIRouter(tags=["ai-prompts-forms"])
logger = get_logger(__name__)


async def get_prompt_service(
    db: AsyncSession = Depends(get_db),
) -> AIPromptService:
    """Provide prompt service dependency."""
    return AIPromptService(db)


async def _tenant_options(db: AsyncSession) -> List[Dict[str, Any]]:
    """Fetch active tenants for global admin dropdowns."""
    result = await db.execute(
        select(Tenant.id, Tenant.name).where(Tenant.status == "active").order_by(Tenant.name)
    )
    return [{"id": str(row.id), "name": row.name} for row in result.fetchall()]


def _serialize_prompt(prompt: Optional[AIPrompt]) -> Optional[SimpleNamespace]:
    """Convert SQLAlchemy prompt to SimpleNamespace for easy template binding."""
    if not prompt:
        return None

    data = prompt.to_dict()
    data["required_variables_json"] = json.dumps(prompt.required_variables or {}, indent=2)
    data["optional_variables_json"] = json.dumps(prompt.optional_variables or {}, indent=2)
    return SimpleNamespace(**data)


@router.get("/", response_class=HTMLResponse)
async def prompts_dashboard(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
    db: AsyncSession = Depends(get_db),
):
    """Render the AI prompt management dashboard."""
    try:
        prompts = await service.list_prompts(tenant_id=tenant_id, include_system=True)
        categories = await service.get_categories(tenant_id)
        global_admin = is_global_admin(current_user)

        available_tenants: List[Dict[str, Any]] = []
        if global_admin:
            available_tenants = await _tenant_options(db)

        context = {
            "request": request,
            "page_title": "AI Prompt Management",
            "page_description": "Create, edit, and override AI prompt templates",
            "prompts": prompts,
            "categories": categories,
            "current_tenant": tenant_id,
            "is_global_admin": global_admin,
            "available_tenants": available_tenants,
        }
        return templates.TemplateResponse("ai_prompts/ai_prompts_dashboard.html", context)
    except Exception as exc:
        logger.error("Failed to load AI prompts dashboard", error=str(exc))
        raise HTTPException(status_code=500, detail="Unable to load AI prompt management") from exc


@router.get("/partials/table", response_class=HTMLResponse)
async def prompt_table_partial(
    request: Request,
    category: Optional[str] = None,
    include_system: bool = True,
    include_inactive: bool = False,
    scope_tenant_id: Optional[str] = None,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Render prompt table partial for HTMX refresh."""
    target_tenant = tenant_id
    if scope_tenant_id and is_global_admin(current_user):
        target_tenant = scope_tenant_id

    prompts = await service.list_prompts(
        tenant_id=target_tenant,
        category=category,
        is_active=None if include_inactive else True,
        include_system=include_system,
    )

    context = {
        "request": request,
        "prompts": prompts,
        "current_tenant": target_tenant,
        "include_inactive": include_inactive,
        "is_global_admin": is_global_admin(current_user),
    }
    return templates.TemplateResponse("administration/ai_prompts/partials/prompt_table.html", context)


@router.get("/partials/details", response_class=HTMLResponse)
async def prompt_details_partial(
    request: Request,
    prompt_id: int,
    service: AIPromptService = Depends(get_prompt_service),
):
    """Render read-only prompt details modal."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)

    context = {
        "request": request,
        "prompt": _serialize_prompt(prompt),
    }
    return templates.TemplateResponse("administration/ai_prompts/partials/prompt_details.html", context)


@router.get("/forms/create", response_class=HTMLResponse)
async def prompt_create_form(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
    db: AsyncSession = Depends(get_db),
    base_prompt_id: Optional[int] = None,
):
    """Render create prompt form modal."""
    base_prompt = None
    if base_prompt_id:
        base_prompt = await service.get_prompt_by_id(base_prompt_id)

    form_data: Dict[str, Any] = {}
    if base_prompt:
        base_ns = _serialize_prompt(base_prompt)
        form_data = base_ns.__dict__
        form_data["prompt_key"] = base_prompt.prompt_key
        # Tenant overrides default to current tenant
        form_data["target_tenant_id"] = tenant_id

    global_admin = is_global_admin(current_user)
    available_tenants: List[Dict[str, Any]] = []
    if global_admin:
        available_tenants = await _tenant_options(db)

    context = {
        "request": request,
        "form_mode": "create",
        "prompt": None,
        "form_data": form_data,
        "errors": {},
        "detected_variables": [],
        "is_global_admin": global_admin,
        "available_tenants": available_tenants,
        "current_tenant": tenant_id,
    }
    return templates.TemplateResponse("administration/ai_prompts/partials/prompt_form.html", context)


@router.get("/forms/{prompt_id}/edit", response_class=HTMLResponse)
async def prompt_edit_form(
    request: Request,
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
    db: AsyncSession = Depends(get_db),
):
    """Render edit prompt form modal."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)

    if prompt.is_system and not is_global_admin(current_user):
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Only global administrators can edit system prompts.</div>",
            status_code=403,
        )

    if prompt.tenant_id and prompt.tenant_id != tenant_id and not is_global_admin(current_user):
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>You cannot edit prompts from another tenant.</div>",
            status_code=403,
        )

    global_admin = is_global_admin(current_user)
    available_tenants: List[Dict[str, Any]] = []
    if global_admin:
        available_tenants = await _tenant_options(db)

    serialized = _serialize_prompt(prompt)
    detected = service.validate_template(prompt.prompt_template)["variables"]

    context = {
        "request": request,
        "form_mode": "edit",
        "prompt": serialized,
        "form_data": serialized.__dict__,
        "errors": {},
        "detected_variables": detected,
        "is_global_admin": global_admin,
        "available_tenants": available_tenants,
        "current_tenant": tenant_id,
    }
    return templates.TemplateResponse("administration/ai_prompts/partials/prompt_form.html", context)


@router.post("/forms", response_class=HTMLResponse)
async def prompt_create_submit(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
    db: AsyncSession = Depends(get_db),
):
    """Process create prompt form submission."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()

    required_fields = ["prompt_key", "name", "category", "prompt_template"]
    form_handler.validate_required_fields(required_fields)

    payload = form_handler.form_data.copy()
    payload["tenant_id"] = tenant_id

    try:
        prompt_data = _prepare_prompt_payload(payload, tenant_id, current_user, is_create=True)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Invalid data"
        target_field = "required_variables" if "Required" in detail else "optional_variables" if "Optional" in detail else "general"
        form_handler.add_error(target_field, detail)

    if form_handler.has_errors():
        detected = service.validate_template(form_handler.form_data.get("prompt_template", "")).get("variables", [])
        context = await _form_context(
            request,
            current_user,
            tenant_id,
            form_mode="create",
            form_data=form_handler.form_data,
            errors=form_handler.errors,
            detected_variables=detected,
            db=db,
        )
        return templates.TemplateResponse(
            "administration/ai_prompts/partials/prompt_form.html",
            context,
            status_code=400,
        )

    try:
        await service.create_prompt(prompt_data)
    except Exception as exc:
        logger.error("Failed to create prompt", error=str(exc))
        form_handler.add_error("general", str(exc))
        detected = service.validate_template(form_handler.form_data.get("prompt_template", "")).get("variables", [])
        context = await _form_context(
            request,
            current_user,
            tenant_id,
            form_mode="create",
            form_data=form_handler.form_data,
            errors=form_handler.errors,
            detected_variables=detected,
            db=db,
        )
        return templates.TemplateResponse(
            "administration/ai_prompts/partials/prompt_form.html",
            context,
            status_code=400,
        )

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "closeModal, refreshPromptTable, promptSaved"
    return response


@router.post("/forms/{prompt_id}", response_class=HTMLResponse)
async def prompt_update_submit(
    request: Request,
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
    db: AsyncSession = Depends(get_db),
):
    """Process update prompt form submission."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)

    if prompt.is_system and not is_global_admin(current_user):
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Only global administrators can edit system prompts.</div>",
            status_code=403,
        )

    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["name", "prompt_template"])

    payload = form_handler.form_data.copy()
    payload["tenant_id"] = prompt.tenant_id or tenant_id
    try:
        prompt_data = _prepare_prompt_payload(payload, tenant_id, current_user, is_create=False)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Invalid data"
        target_field = "required_variables" if "Required" in detail else "optional_variables" if "Optional" in detail else "general"
        form_handler.add_error(target_field, detail)

    if form_handler.has_errors():
        detected = service.validate_template(form_handler.form_data.get("prompt_template", "")).get("variables", [])
        context = await _form_context(
            request,
            current_user,
            tenant_id,
            form_mode="edit",
            form_data=form_handler.form_data,
            errors=form_handler.errors,
            detected_variables=detected,
            prompt=prompt,
            db=db,
        )
        return templates.TemplateResponse(
            "administration/ai_prompts/partials/prompt_form.html",
            context,
            status_code=400,
        )

    try:
        await service.update_prompt(prompt_id, prompt_data)
    except Exception as exc:
        logger.error("Failed to update prompt", error=str(exc))
        form_handler.add_error("general", str(exc))
        detected = service.validate_template(form_handler.form_data.get("prompt_template", "")).get("variables", [])
        context = await _form_context(
            request,
            current_user,
            tenant_id,
            form_mode="edit",
            form_data=form_handler.form_data,
            errors=form_handler.errors,
            detected_variables=detected,
            prompt=prompt,
            db=db,
        )
        return templates.TemplateResponse(
            "administration/ai_prompts/partials/prompt_form.html",
            context,
            status_code=400,
        )

    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "closeModal, refreshPromptTable, promptSaved"
    return response


@router.post("/forms/{prompt_id}/deactivate", response_class=HTMLResponse)
async def prompt_deactivate(
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Deactivate a prompt."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)

    if prompt.is_system and not is_global_admin(current_user):
        return HTMLResponse("<div class='alert alert-danger mb-0'>Only global administrators can disable system prompts.</div>", status_code=403)

    if prompt.tenant_id and prompt.tenant_id != tenant_id and not is_global_admin(current_user):
        return HTMLResponse("<div class='alert alert-danger mb-0'>You cannot modify another tenant's prompt.</div>", status_code=403)

    updated = await service.update_prompt(prompt_id, {"is_active": False})
    if not updated:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)
    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "refreshPromptTable, promptDeactivated"
    return response


@router.post("/forms/{prompt_id}/restore", response_class=HTMLResponse)
async def prompt_restore(
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Restore a previously deactivated prompt."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)

    if prompt.tenant_id and prompt.tenant_id != tenant_id and not is_global_admin(current_user):
        return HTMLResponse("<div class='alert alert-danger mb-0'>You cannot modify another tenant's prompt.</div>", status_code=403)

    updated = await service.update_prompt(prompt_id, {"is_active": True})
    if not updated:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Prompt not found.</div>", status_code=404)
    response = Response(status_code=204)
    response.headers["HX-Trigger"] = "refreshPromptTable, promptRestored"
    return response


@router.post("/partials/validate-template", response_class=HTMLResponse)
async def validate_template_partial(
    request: Request,
    service: AIPromptService = Depends(get_prompt_service),
):
    """Validate template and return variable summary partial."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()

    template_str = form_handler.form_data.get("prompt_template", "")
    if not template_str:
        return HTMLResponse(
            "<div class='alert alert-warning mb-0'>Enter a template to detect variables.</div>"
        )

    validation = service.validate_template(template_str)
    context = {
        "request": request,
        "validation": validation,
    }
    return templates.TemplateResponse(
        "administration/ai_prompts/partials/template_validation_result.html",
        context,
    )


async def _form_context(
    request: Request,
    current_user: User,
    tenant_id: str,
    *,
    form_mode: str,
    form_data: Dict[str, Any],
    errors: Dict[str, List[str]],
    detected_variables: List[str],
    prompt: Optional[AIPrompt] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Assemble shared template context for form re-rendering."""
    available_tenants: List[Dict[str, Any]] = []
    if db and is_global_admin(current_user):
        try:
            available_tenants = await _tenant_options(db)
        except Exception:
            available_tenants = []

    context = {
        "request": request,
        "form_mode": form_mode,
        "prompt": _serialize_prompt(prompt) if prompt else None,
        "form_data": form_data,
        "errors": errors,
        "detected_variables": detected_variables,
        "is_global_admin": is_global_admin(current_user),
        "available_tenants": available_tenants,
        "current_tenant": tenant_id,
    }
    return context
