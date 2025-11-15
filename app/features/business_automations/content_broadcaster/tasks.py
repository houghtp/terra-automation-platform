"""
Celery tasks for the Content Broadcaster planning workflow.

Provides a background task that runs the full AI orchestration pipeline
for a content plan. This keeps the /planning UI responsive while the
research/generation/refinement loop executes asynchronously.
"""

import asyncio
from typing import Any, Dict, Optional

import structlog
from celery import Task

from app.features.core.celery_app import celery_app
from app.features.core.database import get_async_session
from app.features.business_automations.content_broadcaster.services.content_orchestrator_service import (
    ContentOrchestratorService,
)
from app.features.business_automations.content_broadcaster.services.content_planning_service import (
    ContentPlanningService,
)
from app.features.business_automations.content_broadcaster.models import ContentPlanStatus
from app.features.administration.secrets.services import SecretsManagementService
from app.features.auth.models import User
from app.features.core.audit_mixin import AuditContext

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Utility to run async code inside a Celery task."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _load_user(db_session, user_payload: Optional[Dict[str, Any]]):
    """
    Fetch the triggering user for audit logging (best-effort).

    Returns:
        User ORM instance if found, else an AuditContext-compatible dict.
    """
    if not user_payload:
        return None

    user_id = user_payload.get("id")
    if user_id:
        try:
            user = await db_session.get(User, user_id)
            if user:
                return user
        except Exception:
            logger.warning("Failed to load triggering user", user_id=user_id)

    # Fallback lightweight context
    return {
        "id": user_payload.get("id"),
        "email": user_payload.get("email") or "system",
        "name": user_payload.get("name") or user_payload.get("email") or "System",
    }


async def _process_plan_async(
    plan_id: str,
    tenant_id: str,
    triggered_by: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute the AI content generation workflow for a plan.
    """
    async with get_async_session() as db:
        planning_service = ContentPlanningService(db, tenant_id)

        try:
            plan = await planning_service.get_plan(plan_id)
            if not plan:
                raise ValueError(f"Content plan {plan_id} not found")

            trigger_user = await _load_user(db, triggered_by)

            secrets_service = SecretsManagementService(db, tenant_id)
            openai_secret = await secrets_service.get_secret_by_name("OpenAI API Key")
            if not openai_secret:
                raise ValueError("OpenAI API key not configured in Secrets Management")

            secret_value = await secrets_service.get_secret_value(
                secret_id=openai_secret.id,
                accessed_by_user=trigger_user or AuditContext.system(),
            )
            if not secret_value or not secret_value.value:
                raise ValueError("Failed to retrieve OpenAI API key value")

            orchestrator = ContentOrchestratorService(db, tenant_id)
            result = await orchestrator.process_content_plan(
                plan_id=plan_id,
                openai_api_key=secret_value.value,
            )

            await db.commit()
            return result

        except Exception as exc:
            # Mark the plan as failed with error details for easier debugging.
            try:
                await planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.FAILED.value,
                    {"error_log": str(exc)},
                )
                await db.commit()
            except Exception:
                logger.exception(
                    "Failed to update plan status after task error",
                    plan_id=plan_id,
                    tenant_id=tenant_id,
                )
            raise


class ContentPlanTask(Task):
    """
    Base Celery task with structured logging and retries.
    """

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 90}
    retry_backoff = True

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Retrying content plan processing",
            task_id=task_id,
            plan_id=args[0] if args else None,
            tenant_id=args[1] if len(args) > 1 else None,
            error=str(exc),
        )

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "Content plan processed successfully (background)",
            task_id=task_id,
            plan_id=retval.get("plan_id") if isinstance(retval, dict) else None,
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Content plan processing failed",
            task_id=task_id,
            plan_id=args[0] if args else None,
            error=str(exc),
        )


@celery_app.task(
    name="content_broadcaster.process_content_plan",
    base=ContentPlanTask,
    bind=True,
)
def process_content_plan_task(
    self,
    plan_id: str,
    tenant_id: str,
    triggered_by: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Celery entrypoint for content plan processing.
    """
    logger.info(
        "Starting background content plan processing",
        plan_id=plan_id,
        tenant_id=tenant_id,
    )
    return _run_async(_process_plan_async(plan_id, tenant_id, triggered_by))
