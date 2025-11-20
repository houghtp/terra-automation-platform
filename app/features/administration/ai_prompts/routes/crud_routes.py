"""
JSON CRUD routes for AI prompt management.

Provides tenant-aware list/detail endpoints plus template validation helpers
used by the HTMX forms.
"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional

from fastapi import status

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    Request,
    HTTPException,
    AsyncSession,
    get_db,
    tenant_dependency,
    get_current_user,
    rate_limit_api,
    is_global_admin,
    User,
    get_logger,
)
from app.features.administration.ai_prompts.services import AIPromptService

router = APIRouter(prefix="/api", tags=["ai-prompts-api"])
logger = get_logger(__name__)


async def get_prompt_service(
    db: AsyncSession = Depends(get_db),
) -> AIPromptService:
    """Provide a fresh prompt service per request."""
    return AIPromptService(db)


@router.get("/list")
async def list_prompts_api(
    request: Request,
    include_system: bool = True,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    scope_tenant_id: Optional[str] = None,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
    _rate_limit: Dict[str, Any] = Depends(rate_limit_api),
):
    """
    Return prompts for the requested tenant scope (Tabulator list endpoint).

    Global admins can pass `scope_tenant_id` to inspect another tenant.
    Tenant admins are limited to their own tenant plus system prompts.
    """
    try:
        target_tenant = tenant_id
        if scope_tenant_id and is_global_admin(current_user):
            target_tenant = scope_tenant_id

        prompts = await service.list_prompts(
            tenant_id=target_tenant,
            category=category,
            is_active=is_active,
            include_system=include_system,
        )

        return [prompt.to_dict() for prompt in prompts]
    except Exception as exc:
        logger.error("Failed to list prompts", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompts: {exc}",
        ) from exc


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Fetch a single prompt for inspection."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.tenant_id and prompt.tenant_id not in {tenant_id, "global"} and not is_global_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this prompt")

    return prompt.to_dict()


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: Dict[str, Any],
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Create a new prompt via JSON payload."""
    prompt_data = _prepare_prompt_payload(payload, tenant_id, current_user, is_create=True)
    prompt = await service.create_prompt(prompt_data)
    return prompt.to_dict()


@router.put("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    payload: Dict[str, Any],
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Update an existing prompt."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.is_system and not is_global_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only global admins can edit system prompts")

    if prompt.tenant_id and prompt.tenant_id != tenant_id and not is_global_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit another tenant's prompt")

    prompt_data = _prepare_prompt_payload(payload, tenant_id, current_user, is_create=False)

    updated = await service.update_prompt(prompt_id, prompt_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    return updated.to_dict()


@router.post("/prompts/{prompt_id}/restore")
async def restore_prompt(
    prompt_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Re-activate a previously disabled prompt."""
    prompt = await service.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.tenant_id and prompt.tenant_id != tenant_id and not is_global_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another tenant's prompt")

    updated = await service.update_prompt(prompt_id, {"is_active": True, "updated_by": current_user.email})
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore prompt")

    return updated.to_dict()


@router.post("/validate-template")
async def validate_template(
    payload: Dict[str, Any],
    service: AIPromptService = Depends(get_prompt_service),
):
    """Validate a prompt template and return detected variables."""
    template_str = payload.get("template") or payload.get("prompt_template")
    if not template_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template string is required")

    validation = service.validate_template(template_str)
    return validation


@router.get("/categories")
async def list_categories(
    tenant_id: str = Depends(tenant_dependency),
    include_system: bool = True,
    scope_tenant_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: AIPromptService = Depends(get_prompt_service),
):
    """Return available categories for the selected tenant scope."""
    target_tenant = tenant_id
    if scope_tenant_id and is_global_admin(current_user):
        target_tenant = scope_tenant_id

    categories = await service.get_categories(target_tenant if include_system else None)
    return categories


def _prepare_prompt_payload(
    payload: Dict[str, Any],
    tenant_id: str,
    current_user: User,
    *,
    is_create: bool,
) -> Dict[str, Any]:
    """Normalise prompt payloads from both JSON APIs and HTMX forms."""
    prompt_data: Dict[str, Any] = payload.copy()

    # Map JSON strings to dicts when forms send them as text
    for field in ("required_variables", "optional_variables"):
        value = prompt_data.get(field)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                prompt_data[field] = {}
            else:
                try:
                    prompt_data[field] = json.loads(value)
                except json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"{field.replace('_', ' ').title()} must be valid JSON: {exc}",
                    ) from exc

    # Numeric coercion (ignore blanks)
    for numeric_field in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
        value = prompt_data.get(numeric_field)
        if value in (None, ""):
            prompt_data[numeric_field] = None
        else:
            try:
                prompt_data[numeric_field] = float(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{numeric_field.replace('_', ' ').title()} must be numeric",
                ) from exc

    for numeric_field in ("max_tokens",):
        value = prompt_data.get(numeric_field)
        if value in (None, ""):
            prompt_data[numeric_field] = None
        else:
            try:
                prompt_data[numeric_field] = int(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{numeric_field.replace('_', ' ').title()} must be an integer",
                ) from exc

    if is_create and "usage_count" not in prompt_data:
        prompt_data["usage_count"] = 0
        prompt_data["success_count"] = 0
        prompt_data["failure_count"] = 0

    # Decide tenant scope and system flag
    scope = prompt_data.pop("target_tenant_id", None) or prompt_data.get("tenant_id")
    global_scope = scope in (None, "", "system")

    if global_scope:
        prompt_data["tenant_id"] = None
        prompt_data["is_system"] = True
    else:
        prompt_data["tenant_id"] = scope
        prompt_data["is_system"] = bool(prompt_data.get("is_system", False) and is_global_admin(current_user))

    if prompt_data["tenant_id"] and prompt_data["tenant_id"] == "global":
        prompt_data["tenant_id"] = None

    # Audit fields
    actor = current_user.email or current_user.name
    if is_create:
        prompt_data["created_by"] = actor
    prompt_data["updated_by"] = actor

    # Normalise booleans from forms
    for boolean_field in ("is_active", "is_system"):
        value = prompt_data.get(boolean_field)
        if isinstance(value, str):
            prompt_data[boolean_field] = value.lower() in {"true", "1", "yes", "on"}
        elif value is None and boolean_field == "is_active":
            prompt_data[boolean_field] = True

    return prompt_data
