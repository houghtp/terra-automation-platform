"""
Content Planning Service - CRUD operations for content plans.

This service manages content ideas/topics that trigger AI-driven content generation.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, func
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import IntegrityError

from app.features.core.enhanced_base_service import BaseService
from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.audit_mixin import AuditContext
from ..models import ContentPlan, ContentPlanStatus, ContentItem
from .ai_generation_service import AIGenerationService

logger = get_logger(__name__)


class ContentPlanningService(BaseService[ContentPlan]):
    """
    Service for managing content plans.

    Content plans are the entry point for AI-driven content generation.
    Users create plans with topic ideas, and background workers process them.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    def _normalise_prompt_settings(self, settings: Optional[Dict[str, Any]]) -> Dict[str, int]:
        defaults = {
            "professionalism_level": 4,
            "humor_level": 1,
            "creativity_level": 3,
            "analysis_depth": 4,
            "strictness_level": 4,
        }
        if not settings:
            return defaults

        normalised: Dict[str, int] = {}
        for key, default in defaults.items():
            try:
                value = int(settings.get(key, default))
            except (TypeError, ValueError):
                value = default

            minimum = 0 if key == "humor_level" else 1
            normalised[key] = max(minimum, min(5, value))

        return normalised

    async def create_plan(
        self,
        title: str,
        description: Optional[str] = None,
        target_channels: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        tone: Optional[str] = None,
        seo_keywords: Optional[List[str]] = None,
        competitor_urls: Optional[List[str]] = None,
        min_seo_score: int = 95,
        max_iterations: int = 3,
        skip_research: bool = False,
        prompt_settings: Optional[Dict[str, Any]] = None,
        created_by_user=None
    ) -> ContentPlan:
        """
        Create a new content plan.

        Args:
            title: Content topic/idea (required)
            description: Additional context/instructions
            target_channels: List of channels (e.g., ["wordpress", "twitter"])
            target_audience: Target audience description
            tone: Writing tone (e.g., "professional", "casual")
            seo_keywords: Optional user-provided keywords
            competitor_urls: Optional URLs to analyze
            min_seo_score: Target SEO score (80-100, default 95)
            max_iterations: Max refinement loops (1-5, default 3)
            skip_research: Skip competitor research phase (default False)
            created_by_user: User object who created the plan (for audit trail)

        Returns:
            Created ContentPlan instance

        Raises:
            ValueError: If validation fails
        """
        try:
            # Validation
            if not title or len(title) < 3:
                raise ValueError("Title must be at least 3 characters")

            if len(title) > 500:
                raise ValueError("Title must be less than 500 characters")

            if min_seo_score < 80 or min_seo_score > 100:
                raise ValueError("min_seo_score must be between 80 and 100")

            if max_iterations < 1 or max_iterations > 5:
                raise ValueError("max_iterations must be between 1 and 5")

            # Create audit context
            audit_ctx = AuditContext.from_user(created_by_user) if created_by_user else None

            # Create plan
            plan = ContentPlan(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id or "global",
                title=title.strip(),
                description=description.strip() if description else None,
                target_channels=target_channels or [],
                target_audience=target_audience,
                tone=tone,
                seo_keywords=seo_keywords or [],
                competitor_urls=competitor_urls or [],
                min_seo_score=min_seo_score,
                max_iterations=max_iterations,
                skip_research=skip_research,
                status=ContentPlanStatus.PLANNED.value,
                current_iteration=0,
                latest_seo_score=None,
                research_data={},
                generation_metadata={},
                refinement_history=[],
                prompt_settings=self._normalise_prompt_settings(prompt_settings),
                generated_content_item_id=None,
                error_log=None,
                retry_count=0
            )

            # Set audit information with explicit timestamps
            if audit_ctx:
                plan.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            plan.created_at = datetime.now()
            plan.updated_at = datetime.now()

            self.db.add(plan)
            await self.db.flush()

            self.log_operation("content_plan_created", {
                "plan_id": plan.id,
                "title": plan.title,
                "tenant_id": plan.tenant_id,
                "target_channels": target_channels,
                "min_seo_score": min_seo_score,
                "prompt_settings": plan.prompt_settings,
            })

            logger.info(
                "Content plan created",
                plan_id=plan.id,
                title=plan.title,
                tenant_id=plan.tenant_id,
                status=plan.status
            )

            return plan

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to create content plan - IntegrityError",
                        error=error_str,
                        title=title,
                        tenant_id=self.tenant_id)
            raise ValueError(f"Failed to create content plan: {error_str}")
        except Exception as e:
            await self.db.rollback()
            logger.exception("Failed to create content plan")
            raise

    async def list_plans(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List content plans with filtering and pagination.

        Args:
            status: Filter by status (optional)
            search: Search in title and description
            limit: Number of items per page (default 100)
            offset: Pagination offset (default 0)

        Returns:
            Dict with 'data', 'total', 'offset', 'limit'
        """
        # Base query with tenant isolation
        stmt = self.create_base_query(ContentPlan)

        # Status filter
        if status:
            stmt = stmt.where(ContentPlan.status == status)

        # Search filter
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ContentPlan.title.ilike(search_term),
                    ContentPlan.description.ilike(search_term)
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()

        # Apply ordering and pagination
        stmt = stmt.order_by(desc(ContentPlan.created_at))
        stmt = stmt.limit(limit).offset(offset)

        # Execute query
        result = await self.db.execute(stmt)
        plans = result.scalars().all()

        return {
            "data": [plan.to_dict() for plan in plans],
            "total": total,
            "offset": offset,
            "limit": limit
        }

    async def get_plan(self, plan_id: str) -> Optional[ContentPlan]:
        """
        Get a single content plan by ID.

        Args:
            plan_id: Plan ID

        Returns:
            ContentPlan if found, None otherwise

        Raises:
            ValueError: If plan not found
        """
        plan = await self.get_by_id(ContentPlan, plan_id)

        if not plan:
            raise ValueError(f"Content plan {plan_id} not found")

        return plan

    async def update_plan(
        self,
        plan_id: str,
        updates: Dict[str, Any],
        updated_by_user=None
    ) -> ContentPlan:
        """
        Update a content plan (only allowed if not processing).

        Args:
            plan_id: Plan ID
            updates: Dictionary of fields to update
            updated_by_user: User object who updated the plan (for audit trail)

        Returns:
            Updated ContentPlan

        Raises:
            ValueError: If plan not found or cannot be updated
        """
        try:
            plan = await self.get_plan(plan_id)

            # Check if plan can be updated
            processing_states = [
                ContentPlanStatus.RESEARCHING.value,
                ContentPlanStatus.GENERATING.value,
                ContentPlanStatus.REFINING.value
            ]

            if plan.status in processing_states:
                raise ValueError(
                    f"Cannot update plan while processing (status: {plan.status})"
                )

            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user) if updated_by_user else None

            # Update allowed fields
            allowed_fields = [
                "title", "description", "target_channels", "target_audience",
                "tone", "seo_keywords", "competitor_urls", "min_seo_score", "max_iterations", "prompt_settings", "skip_research"
            ]

            for field, value in updates.items():
                if field in allowed_fields and hasattr(plan, field):
                    if field == "prompt_settings":
                        setattr(plan, field, self._normalise_prompt_settings(value))
                    else:
                        setattr(plan, field, value)

            # Set audit information with explicit timestamp
            if audit_ctx:
                plan.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            plan.updated_at = datetime.now()

            await self.db.flush()

            self.log_operation("content_plan_updated", {
                "plan_id": plan.id,
                "updates": list(updates.keys())
            })

            return plan

        except IntegrityError as e:
            await self.db.rollback()
            logger.error("Failed to update content plan - IntegrityError", error=str(e))
            raise ValueError(f"Failed to update content plan: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            logger.exception("Failed to update content plan")
            raise

    async def delete_plan(self, plan_id: str) -> bool:
        """
        Soft delete (archive) a content plan.

        Args:
            plan_id: Plan ID

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If plan not found or cannot be deleted
        """
        plan = await self.get_plan(plan_id)

        plan.generated_content_item_id = None
        plan.latest_seo_score = None
        generation_meta = plan.generation_metadata or {}
        run_history = generation_meta.get("run_history", [])
        for entry in run_history:
            content_item_id = entry.get("content_item_id")
            if not content_item_id:
                continue

            content_item = await self.db.get(ContentItem, content_item_id)
            if not content_item:
                continue

            metadata = content_item.content_metadata or {}
            status = metadata.get("plan_run_status")

            if status == "published":
                metadata.pop("generated_from_plan", None)
                metadata.pop("plan_run_id", None)
                metadata.pop("plan_run_parameters", None)
                metadata.pop("plan_run_status", None)
                content_item.content_metadata = metadata
                content_item.updated_at = datetime.now()
            else:
                await self.db.delete(content_item)

        plan.generation_metadata = {}

        await self.db.delete(plan)
        await self.db.flush()

        self.log_operation("content_plan_deleted", {
            "plan_id": plan.id,
            "title": plan.title
        })

        return True

    async def retry_plan(self, plan_id: str) -> ContentPlan:
        """
        Retry a failed content plan.

        Args:
            plan_id: Plan ID

        Returns:
            Updated ContentPlan

        Raises:
            ValueError: If plan not in failed state
        """
        plan = await self.get_plan(plan_id)

        if plan.status != ContentPlanStatus.FAILED.value:
            raise ValueError(f"Can only retry failed plans (current status: {plan.status})")

        # Reset plan for retry
        plan.status = ContentPlanStatus.PLANNED.value
        plan.error_log = None
        plan.retry_count += 1
        plan.updated_at = datetime.now()

        await self.db.flush()

        self.log_operation("content_plan_retried", {
            "plan_id": plan.id,
            "retry_count": plan.retry_count
        })

        return plan

    async def approve_draft(self, plan_id: str, approved_by: Optional[str] = None) -> ContentPlan:
        """
        Approve a draft-ready content plan.

        Args:
            plan_id: Plan ID
            approved_by: User ID who approved

        Returns:
            Updated ContentPlan

        Raises:
            ValueError: If plan not in draft_ready state
        """
        plan = await self.get_plan(plan_id)

        if plan.status != ContentPlanStatus.DRAFT_READY.value:
            raise ValueError(
                f"Can only approve draft-ready plans (current status: {plan.status})"
            )

        plan.status = ContentPlanStatus.APPROVED.value
        plan.updated_by = approved_by
        plan.updated_at = datetime.now()

        await self.db.flush()

        self.log_operation("content_plan_approved", {
            "plan_id": plan.id,
            "generated_content_id": plan.generated_content_item_id
        })

        return plan

    async def get_iteration_history(self, plan_id: str) -> List[Dict[str, Any]]:
        """
        Get refinement iteration history for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            List of iteration attempts with scores and feedback
        """
        plan = await self.get_plan(plan_id)

        return plan.refinement_history or []

    async def update_status(
        self,
        plan_id: str,
        new_status: str,
        **metadata
    ) -> ContentPlan:
        """
        Update plan status (used by worker processes).

        Args:
            plan_id: Plan ID
            new_status: New status value
            **metadata: Additional metadata to store

        Returns:
            Updated ContentPlan
        """
        plan = await self.get_plan(plan_id)

        plan.status = new_status
        plan.updated_at = datetime.now()

        # Update specific metadata fields
        if "current_iteration" in metadata:
            plan.current_iteration = metadata["current_iteration"]

        if "latest_seo_score" in metadata:
            plan.latest_seo_score = metadata["latest_seo_score"]

        if "research_data" in metadata:
            plan.research_data = metadata["research_data"]

        if "generation_metadata" in metadata:
            plan.generation_metadata = metadata["generation_metadata"]

        if "refinement_history" in metadata:
            plan.refinement_history = metadata["refinement_history"]

        if "error_log" in metadata:
            plan.error_log = metadata["error_log"]

        if "generated_content_item_id" in metadata:
            plan.generated_content_item_id = metadata["generated_content_item_id"]

        await self.db.flush()

        return plan

    # Alias for consistency with orchestrator service
    async def update_plan_status(
        self,
        plan_id: str,
        new_status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentPlan:
        """
        Alias for update_status() for consistency with orchestrator service.

        Args:
            plan_id: Plan ID
            new_status: New status value
            metadata: Optional dict of metadata to store

        Returns:
            Updated ContentPlan
        """
        if metadata is None:
            metadata = {}
        return await self.update_status(plan_id, new_status, **metadata)

    async def update_content_item_run_metadata(
        self,
        content_item_id: Optional[str],
        plan_id: str,
        run_id: Optional[str],
        status: str,
        parameters: Optional[Dict[str, Any]] = None,
        flush: bool = False
    ) -> Optional[ContentItem]:
        """Ensure a content item tracks its plan/run association."""
        if not content_item_id:
            return None

        content_item = await self.db.get(ContentItem, content_item_id)
        if not content_item:
            return None

        metadata = content_item.content_metadata or {}
        metadata["generated_from_plan"] = plan_id
        if run_id:
            metadata["plan_run_id"] = run_id
        metadata["plan_run_status"] = status
        if parameters:
            metadata["plan_run_parameters"] = parameters

        content_item.content_metadata = metadata
        content_item.updated_at = datetime.now()

        if flush:
            await self.db.flush()

        return content_item

    async def set_run_status(
        self,
        plan_id: str,
        run_id: str,
        new_status: str
    ) -> Dict[str, Any]:
        """Update the status of a specific run and archive the rest."""
        allowed_statuses = {"current", "published"}
        if new_status not in allowed_statuses:
            raise ValueError("Invalid run status")

        plan = await self.get_plan(plan_id)
        generation_meta = plan.generation_metadata or {}
        history = list(generation_meta.get("run_history", []))

        target = None
        for entry in history:
            entry_run_id = entry.get("run_id") or entry.get("content_item_id")
            if entry_run_id == run_id or entry.get("run_id") == run_id:
                target = entry
                break

        if not target:
            raise ValueError("Run not found")

        for entry in history:
            if entry is target:
                entry_status = new_status
            else:
                entry_status = "archived"
            entry["status"] = entry_status
            await self.update_content_item_run_metadata(
                entry.get("content_item_id"),
                plan_id,
                entry.get("run_id"),
                entry_status,
                entry.get("parameters"),
                flush=False
            )

        generation_meta["run_history"] = history
        generation_meta["current_run_id"] = target.get("run_id")
        if new_status == "published":
            generation_meta["published_run_id"] = target.get("run_id")
        else:
            if generation_meta.get("published_run_id") == target.get("run_id"):
                generation_meta.pop("published_run_id", None)

        plan.generation_metadata = dict(generation_meta)
        flag_modified(plan, "generation_metadata")
        if target.get("content_item_id"):
            plan.generated_content_item_id = target["content_item_id"]
        if target.get("seo_score") is not None:
            plan.latest_seo_score = target["seo_score"]
        if new_status == "published":
            plan.status = ContentPlanStatus.APPROVED.value

        plan.updated_at = datetime.now()
        await self.db.flush()

        self.log_operation("content_plan_run_status_updated", {
            "plan_id": plan_id,
            "run_id": run_id,
            "status": new_status
        })

        return target

    async def update_run_content(
        self,
        plan_id: str,
        run_id: str,
        title: str,
        body: str,
        edited_by_user=None,
        edit_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a run's content and flag human edits."""
        if not title:
            raise ValueError("Title cannot be empty")
        if not body:
            raise ValueError("Content body cannot be empty")

        plan = await self.get_plan(plan_id)
        generation_meta = plan.generation_metadata or {}
        history = list(generation_meta.get("run_history", []))

        target = None
        for entry in history:
            entry_run_id = entry.get("run_id") or entry.get("content_item_id")
            if entry_run_id == run_id or entry.get("run_id") == run_id:
                target = entry
                break

        if not target:
            raise ValueError("Run not found")

        content_item_id = target.get("content_item_id") or plan.generated_content_item_id
        if not content_item_id:
            raise ValueError("No content item associated with this run")

        content_item = await self.db.get(ContentItem, content_item_id)
        if not content_item:
            raise ValueError("Content item not found")

        audit_ctx = AuditContext.from_user(edited_by_user)
        timestamp = datetime.now().isoformat()

        content_item.title = title.strip()
        content_item.body = body
        content_item.updated_at = datetime.now()
        if audit_ctx:
            content_item.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

        metadata = content_item.content_metadata or {}
        metadata.update({
            "human_edited": True,
            "edited_by": audit_ctx.user_name,
            "edited_by_email": audit_ctx.user_email,
            "edited_at": timestamp,
            "edit_run_id": run_id
        })
        if edit_notes:
            metadata["edit_notes"] = edit_notes
        content_item.content_metadata = metadata

        target["human_edited"] = True
        target["edited_by"] = audit_ctx.user_name
        target["edited_by_email"] = audit_ctx.user_email
        target["edited_at"] = timestamp
        if edit_notes:
            target["edit_notes"] = edit_notes

        generation_meta["run_history"] = history
        plan.generation_metadata = dict(generation_meta)
        flag_modified(plan, "generation_metadata")
        plan.updated_at = datetime.now()

        await self.db.flush()

        self.log_operation("content_plan_run_edited", {
            "plan_id": plan_id,
            "run_id": run_id,
            "edited_by": audit_ctx.user_email
        })

        return target

    async def rerun_seo_validation(
        self,
        plan_id: str,
        run_id: str,
        openai_api_key: str
    ) -> Dict[str, Any]:
        """Re-run SEO validation for a specific run."""
        plan = await self.get_plan(plan_id)
        generation_meta = plan.generation_metadata or {}
        history = list(generation_meta.get("run_history", []))

        target = None
        for entry in history:
            entry_run_id = entry.get("run_id") or entry.get("content_item_id")
            if entry_run_id == run_id or entry.get("run_id") == run_id:
                target = entry
                break

        if not target:
            raise ValueError("Run not found")

        content_item_id = target.get("content_item_id") or plan.generated_content_item_id
        if not content_item_id:
            raise ValueError("No content item associated with this run")

        content_item = await self.db.get(ContentItem, content_item_id)
        if not content_item:
            raise ValueError("Content item not found")

        generation_service = AIGenerationService(self.db, self.tenant_id)
        validation_result = await generation_service.validate_content(
            title=content_item.title or plan.title,
            content=content_item.body,
            openai_api_key=openai_api_key,
            prompt_settings=plan.prompt_settings or {}
        )

        sub_scores = validation_result.get("sub_scores", {})
        metadata = validation_result.get("metadata", {})
        issues = validation_result.get("issues", [])
        recommendations = validation_result.get("recommendations", [])
        strengths = validation_result.get("strengths", [])

        target["seo_score"] = validation_result.get("score", 0)
        target["sub_scores"] = sub_scores
        target["validation_metadata"] = metadata
        target["issues"] = issues
        target["recommendations"] = recommendations
        target["strengths"] = strengths

        refinement_history = list(target.get("refinement_history") or [])
        refinement_history.append({
            "iteration": len(refinement_history) + 1,
            "score": validation_result.get("score", 0),
            "status": validation_result.get("status"),
            "issues": issues,
            "recommendations": recommendations,
            "refined_at": datetime.now().isoformat(),
            "manual": True
        })
        target["refinement_history"] = refinement_history
        target["iterations"] = len(refinement_history)

        generation_meta["run_history"] = history
        plan.generation_metadata = dict(generation_meta)
        flag_modified(plan, "generation_metadata")

        current_run_id = generation_meta.get("current_run_id")
        target_identifier = target.get("run_id") or target.get("content_item_id")
        if current_run_id and current_run_id == target_identifier:
            plan.latest_seo_score = validation_result.get("score", 0)
        elif plan.generated_content_item_id == content_item_id:
            plan.latest_seo_score = validation_result.get("score", 0)

        plan.updated_at = datetime.now()
        await self.db.flush()

        self.log_operation("content_plan_run_validated", {
            "plan_id": plan_id,
            "run_id": run_id,
            "score": validation_result.get("score", 0)
        })

        return validation_result

    async def update_run_content(
        self,
        plan_id: str,
        run_id: str,
        title: str,
        body: str,
        edited_by_user=None,
        edit_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update the content item tied to a run and flag manual edits."""
        if not title:
            raise ValueError("Title cannot be empty")
        if not body:
            raise ValueError("Content body cannot be empty")

        plan = await self.get_plan(plan_id)
        generation_meta = plan.generation_metadata or {}
        history = list(generation_meta.get("run_history", []))

        target = None
        for entry in history:
            entry_run_id = entry.get("run_id") or entry.get("content_item_id")
            if entry_run_id == run_id or entry.get("run_id") == run_id:
                target = entry
                break

        if not target:
            raise ValueError("Run not found")

        content_item_id = target.get("content_item_id") or plan.generated_content_item_id
        if not content_item_id:
            raise ValueError("No content item associated with this run")

        content_item = await self.db.get(ContentItem, content_item_id)
        if not content_item:
            raise ValueError("Content item not found")

        audit_ctx = AuditContext.from_user(edited_by_user)
        timestamp = datetime.now().isoformat()

        content_item.title = title.strip()
        content_item.body = body
        content_item.updated_at = datetime.now()
        if audit_ctx:
            content_item.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

        metadata = content_item.content_metadata or {}
        metadata.update({
            "human_edited": True,
            "edited_by": audit_ctx.user_name,
            "edited_by_email": audit_ctx.user_email,
            "edited_at": timestamp,
            "edit_run_id": run_id
        })
        if edit_notes:
            metadata["edit_notes"] = edit_notes
        content_item.content_metadata = metadata

        target["human_edited"] = True
        target["edited_by"] = audit_ctx.user_name
        target["edited_by_email"] = audit_ctx.user_email
        target["edited_at"] = timestamp
        if edit_notes:
            target["edit_notes"] = edit_notes

        generation_meta["run_history"] = history
        plan.generation_metadata = dict(generation_meta)
        flag_modified(plan, "generation_metadata")
        plan.updated_at = datetime.now()

        await self.db.flush()

        self.log_operation("content_plan_run_edited", {
            "plan_id": plan_id,
            "run_id": run_id,
            "edited_by": audit_ctx.user_email
        })

        return target
