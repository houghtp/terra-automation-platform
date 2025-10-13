"""
Content Orchestrator Service - Coordinates AI content generation workflow.

This service orchestrates the complete AI content generation pipeline:
1. Research (competitor analysis)
2. Generation (blog post creation)
3. Validation (SEO scoring)
4. Refinement (iterative improvement)
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.audit_mixin import AuditContext
from .content_planning_service import ContentPlanningService
from .ai_research_service import AIResearchService
from .ai_generation_service import AIGenerationService
from ..models import ContentPlanStatus, ContentItem, ContentState

logger = get_logger(__name__)


class ContentOrchestratorService:
    """
    Orchestrates the AI content generation workflow.

    This service coordinates all AI services to transform a content plan
    into a ready-to-publish draft.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: str):
        """
        Initialize orchestrator with all required services.

        Args:
            db_session: Database session
            tenant_id: Tenant ID for multi-tenant isolation
        """
        self.db = db_session
        self.tenant_id = tenant_id
        self.planning_service = ContentPlanningService(db_session, tenant_id)
        self.research_service = AIResearchService(tenant_id)
        self.generation_service = AIGenerationService()

    async def process_content_plan(
        self,
        plan_id: str,
        openai_api_key: str
    ) -> Dict[str, Any]:
        """
        Process a content plan through the complete AI workflow.

        Args:
            plan_id: ContentPlan ID to process
            openai_api_key: OpenAI API key for content generation

        Returns:
            Dictionary with results including:
            - plan_id: The processed plan ID
            - content_item_id: Created ContentItem ID
            - status: Final status
            - content_length: Length of generated content
            - research_sources: Number of sources analyzed

        Raises:
            ValueError: If plan not found or in invalid state
            Exception: If any step in the workflow fails

        Note:
            Research phase fetches scraping API keys internally from Secrets Management.
        """
        try:
            # Get the content plan
            plan = await self.planning_service.get_plan(plan_id)
            if not plan:
                raise ValueError(f"Content plan {plan_id} not found")

            # Allow planned and failed statuses (failed plans can be retried)
            allowed_statuses = [ContentPlanStatus.PLANNED.value, ContentPlanStatus.FAILED.value]
            if plan.status not in allowed_statuses:
                raise ValueError(
                    f"Cannot process plan in {plan.status} state. "
                    f"Only 'planned' or 'failed' status can be processed."
                )

            logger.info(
                "Starting content generation workflow",
                plan_id=plan_id,
                title=plan.title,
                tenant_id=plan.tenant_id,
                skip_research=plan.skip_research
            )

            # Initialize research_data for use in generation
            research_data = {}

            # Step 1: Research Phase (conditionally skip)
            if plan.skip_research:
                logger.info(
                    "Skipping research phase (direct generation requested)",
                    plan_id=plan_id
                )
                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.GENERATING.value,
                    {"message": "Generating content directly (research skipped)..."}
                )
            else:
                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.RESEARCHING.value,
                    {"message": "Starting competitor research..."}
                )

                # Process research (API keys fetched inside process_research)
                research_data = await self.research_service.process_research(
                    title=plan.title,
                    db_session=self.db,
                    num_results=3  # Analyze top 3 competitors
                )

                logger.info(
                    "Research phase completed",
                    plan_id=plan_id,
                    num_sources=len(research_data.get("scraped_content", []))
                )

                # Step 2: Generation Phase
                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.GENERATING.value,
                    {
                        "research_data": research_data,
                        "message": "Generating initial draft..."
                    }
                )

            # Generate content with or without research insights
            content_body = await self.generation_service.generate_blog_post(
                title=plan.title,
                description=plan.description,
                target_audience=plan.target_audience,
                keywords=plan.seo_keywords or [],
                seo_analysis=research_data.get("seo_analysis", "") if not plan.skip_research else None,
                openai_api_key=openai_api_key,
                tone=plan.tone or "professional"
            )

            logger.info(
                "Generation phase completed",
                plan_id=plan_id,
                content_length=len(content_body)
            )

            # Step 3: Create ContentItem with draft
            await self.planning_service.update_plan_status(
                plan_id,
                ContentPlanStatus.DRAFT_READY.value,
                {
                    "research_data": research_data,
                    "generation_metadata": {
                        "content_length": len(content_body),
                        "tone": plan.tone or "professional"
                    },
                    "message": "Draft ready for review"
                }
            )

            # Create the ContentItem with proper UUID (following standard pattern)
            content_item = ContentItem(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                title=plan.title,
                body=content_body,
                state=ContentState.DRAFT.value,
                content_metadata={
                    "generated_from_plan": plan_id,
                    "research_sources": len(research_data.get("sources", [])),
                    "tone": plan.tone or "professional"
                },
                tags=plan.seo_keywords or []
            )

            # Set audit information using standard pattern
            if plan.created_by_email:
                audit_ctx = AuditContext(
                    user_email=plan.created_by_email,
                    user_name=plan.created_by_name or plan.created_by_email
                )
                content_item.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            else:
                # System-generated content
                audit_ctx = AuditContext.system()
                content_item.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            content_item.created_at = datetime.now()
            content_item.updated_at = datetime.now()

            self.db.add(content_item)

            # Link plan to content item
            plan.generated_content_item_id = content_item.id

            await self.db.flush()
            await self.db.commit()

            logger.info(
                "Content generation workflow completed successfully",
                plan_id=plan_id,
                content_item_id=content_item.id,
                tenant_id=plan.tenant_id
            )

            return {
                "success": True,
                "plan_id": plan_id,
                "content_item_id": content_item.id,
                "status": plan.status,
                "title": plan.title,
                "content_length": len(content_body),
                "research_sources": len(research_data.get("sources", [])),
                "message": "Content generated successfully and saved as draft"
            }

        except Exception as e:
            # Update plan status to failed
            try:
                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.FAILED.value,
                    {"error_log": str(e)}
                )
                await self.db.commit()
            except:
                pass

            # Try to get tenant_id from plan if available
            tenant_id_for_log = "unknown"
            try:
                if plan:
                    tenant_id_for_log = plan.tenant_id
            except:
                pass

            logger.exception(
                "Content generation workflow failed",
                plan_id=plan_id,
                tenant_id=tenant_id_for_log
            )

            raise
