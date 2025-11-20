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
from typing import Optional, Dict, Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.audit_mixin import AuditContext
from .content_planning_service import ContentPlanningService
from .ai_research_service import AIResearchService
from .ai_generation_service import AIGenerationService
from ..models import ContentPlanStatus, ContentItem, ContentState, ContentVariant

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
        self.generation_service = AIGenerationService(db_session, tenant_id)

    async def _commit_and_refresh_plan(self, plan_id: str):
        """
        Persist current transaction and refresh plan from the database so that
        other sessions (and subsequent reads) observe the latest status.
        """
        await self.db.commit()
        return await self.planning_service.get_plan(plan_id)

    async def process_content_plan(
        self,
        plan_id: str,
        openai_api_key: str,
        progress_callback: Optional[Callable[[str, str, str, Dict[str, Any]], Awaitable[None]]] = None
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
        async def emit_progress(stage: str, message: str, status: str = "running", data: Optional[Dict[str, Any]] = None):
            if not progress_callback:
                return
            try:
                await progress_callback(stage=stage, message=message, status=status, data=data or {})
            except Exception as emit_error:
                logger.warning(
                    "Progress callback failed",
                    plan_id=plan_id,
                    stage=stage,
                    error=str(emit_error)
                )

        try:
            # Get the content plan
            plan = await self.planning_service.get_plan(plan_id)
            if not plan:
                raise ValueError(f"Content plan {plan_id} not found")

            # Block only active processing statuses; all other states can be regenerated
            blocked_statuses = {
                ContentPlanStatus.GENERATING.value,
                ContentPlanStatus.REFINING.value
            }
            if plan.status in blocked_statuses:
                raise ValueError(
                    f"Cannot process plan in {plan.status} state because it is already running."
                )

            await emit_progress(
                "queued",
                f"Preparing '{plan.title}' for AI generation.",
                data={"plan_id": plan_id, "title": plan.title}
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
            raw_settings = plan.prompt_settings or {}
            prompt_settings = {
                "professionalism_level": int(raw_settings.get("professionalism_level", 4) or 4),
                "humor_level": int(raw_settings.get("humor_level", 1) or 1),
                "creativity_level": int(raw_settings.get("creativity_level", 3) or 3),
                "analysis_depth": int(raw_settings.get("analysis_depth", 4) or 4),
                "strictness_level": int(raw_settings.get("strictness_level", 4) or 4),
            }
            prompt_settings["humor_level"] = max(0, min(5, prompt_settings["humor_level"]))
            for key in ("professionalism_level", "creativity_level", "analysis_depth", "strictness_level"):
                prompt_settings[key] = max(1, min(5, prompt_settings[key]))

            # Step 1: Research Phase (conditionally skip)
            if plan.skip_research:
                logger.info(
                    "Skipping research phase (direct generation requested)",
                    plan_id=plan_id
                )
                await emit_progress(
                    "generating",
                    f"Generating draft for '{plan.title}' (research skipped).",
                    data={"plan_id": plan_id, "title": plan.title}
                )
                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.GENERATING.value,
                    {"message": "Generating content directly (research skipped)..."}
                )
                plan = await self._commit_and_refresh_plan(plan_id)
            else:
                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.RESEARCHING.value,
                    {"message": "Starting competitor research..."}
                )
                plan = await self._commit_and_refresh_plan(plan_id)

                await emit_progress(
                    "researching",
                    f"Researching competitors for '{plan.title}'.",
                    data={"plan_id": plan_id, "title": plan.title}
                )

                # Process research (API keys fetched inside process_research)
                research_data = await self.research_service.process_research(
                    title=plan.title,
                    db_session=self.db,
                    num_results=3,  # Analyze top 3 competitors
                    prompt_settings=prompt_settings
                )

                logger.info(
                    "Research phase completed",
                    plan_id=plan_id,
                    num_sources=len(research_data.get("scraped_content", []))
                )
                await emit_progress(
                    "research_complete",
                    f"Research complete – analyzed {len(research_data.get('scraped_content', []))} sources.",
                    data={"plan_id": plan_id, "title": plan.title}
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
                plan = await self._commit_and_refresh_plan(plan_id)

            await emit_progress(
                "generating",
                f"Generating initial draft for '{plan.title}'.",
                data={"plan_id": plan_id, "title": plan.title}
            )

            # Generate content with or without research insights
            content_body = await self.generation_service.generate_blog_post(
                title=plan.title,
                description=plan.description,
                target_audience=plan.target_audience,
                keywords=plan.seo_keywords or [],
                seo_analysis=research_data.get("seo_analysis", "") if not plan.skip_research else None,
                openai_api_key=openai_api_key,
                tone=plan.tone or "professional",
                prompt_settings=prompt_settings
            )

            logger.info(
                "Generation phase completed",
                plan_id=plan_id,
                content_length=len(content_body)
            )

            # Step 3: Iterative SEO Refinement Loop
            min_seo_score = plan.min_seo_score or 95
            max_iterations = plan.max_iterations or 3
            current_iteration = 1
            refinement_history = []
            best_content = content_body
            best_score = 0

            final_validation_result = None
            while current_iteration <= max_iterations:
                validation_settings = dict(prompt_settings)
                validation_settings["target_score"] = min_seo_score

                await self.planning_service.update_plan_status(
                    plan_id,
                    ContentPlanStatus.REFINING.value,
                    {
                        "message": f"Validating SEO quality (iteration {current_iteration}/{max_iterations})..."
                    }
                )
                plan = await self._commit_and_refresh_plan(plan_id)

                # Validate current content
                validation_result = await self.generation_service.validate_content(
                    title=plan.title,
                    content=content_body,
                    openai_api_key=openai_api_key,
                    prompt_settings=validation_settings
                )
                final_validation_result = validation_result

                seo_score = validation_result.get("score", 0)
                validation_status = validation_result.get("status", "UNKNOWN")

                # Record this iteration
                iteration_record = {
                    "iteration": current_iteration,
                    "score": seo_score,
                    "status": validation_status,
                    "issues": validation_result.get("issues", []),
                    "recommendations": validation_result.get("recommendations", []),
                    "timestamp": datetime.now().isoformat()
                }
                refinement_history.append(iteration_record)

                logger.info(
                    "SEO validation iteration completed",
                    plan_id=plan_id,
                    iteration=current_iteration,
                    score=seo_score,
                    status=validation_status,
                    target=min_seo_score
                )

                # Keep track of best version
                if seo_score > best_score:
                    best_score = seo_score
                    best_content = content_body

                # Check if we've met the target score
                if seo_score >= min_seo_score:
                    logger.info(
                        "SEO target score achieved",
                        plan_id=plan_id,
                        score=seo_score,
                        target=min_seo_score,
                        iteration=current_iteration
                    )
                    break

                # If not at target and not at max iterations, refine
                if current_iteration < max_iterations:
                    await self.planning_service.update_plan_status(
                        plan_id,
                        ContentPlanStatus.REFINING.value,
                        {
                            "message": f"Refining content (score: {seo_score}/{min_seo_score}, iteration {current_iteration}/{max_iterations})..."
                        }
                    )
                    plan = await self._commit_and_refresh_plan(plan_id)

                    # Create feedback for refinement
                    feedback_text = f"""
Current SEO Score: {seo_score}/100 (Target: {min_seo_score})
Status: {validation_status}

Issues to Address:
{chr(10).join(f"- {issue}" for issue in validation_result.get('issues', []))}

Recommendations:
{chr(10).join(f"- {rec}" for rec in validation_result.get('recommendations', []))}

Please improve the content to address these specific issues while maintaining the quality and message.
"""

                    # Regenerate with feedback
                    content_body = await self.generation_service.generate_blog_post(
                        title=plan.title,
                        description=plan.description,
                        target_audience=plan.target_audience,
                        keywords=plan.seo_keywords or [],
                        seo_analysis=research_data.get("seo_analysis", "") if not plan.skip_research else None,
                        previous_content=content_body,
                        validation_feedback=feedback_text,
                        openai_api_key=openai_api_key,
                        tone=plan.tone or "professional",
                        prompt_settings=prompt_settings
                    )

                    logger.info(
                        "Content refinement completed",
                        plan_id=plan_id,
                        iteration=current_iteration,
                        new_content_length=len(content_body)
                    )

                current_iteration += 1

            # Use the best version we achieved
            final_content = best_content
            final_score = best_score

            logger.info(
                "SEO refinement process completed",
                plan_id=plan_id,
                final_score=final_score,
                total_iterations=len(refinement_history),
                target_achieved=final_score >= min_seo_score
            )

            run_id = str(uuid.uuid4())
            run_parameters = {
                "tone": plan.tone or "professional",
                "skip_research": plan.skip_research,
                "target_channels": plan.target_channels or [],
                "prompt_settings": dict(prompt_settings),
                "min_seo_score": min_seo_score,
                "max_iterations": max_iterations
            }

            # Step 4: Create ContentItem with draft
            content_item = ContentItem(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                title=plan.title,
                body=final_content,
                state=ContentState.IN_REVIEW.value,
                content_metadata={
                    "generated_from_plan": plan_id,
                    "plan_run_id": run_id,
                    "plan_run_status": "current",
                    "plan_run_parameters": run_parameters,
                    "research_sources": len(research_data.get("sources", [])),
                    "tone": plan.tone or "professional",
                    "seo_score": final_score,
                    "refinement_iterations": len(refinement_history)
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

            existing_metadata = plan.generation_metadata or {}
            run_history_list = list(existing_metadata.get("run_history", []))
            for entry in run_history_list:
                entry["status"] = "archived"
                await self.planning_service.update_content_item_run_metadata(
                    entry.get("content_item_id"),
                    plan_id,
                    entry.get("run_id"),
                    "archived",
                    entry.get("parameters"),
                    flush=False
                )
            sub_scores = (final_validation_result or {}).get("sub_scores") if final_validation_result else None
            sub_score_details = (final_validation_result or {}).get("sub_score_details") if final_validation_result else None
            metadata = (final_validation_result or {}).get("metadata") if final_validation_result else None

            run_entry = {
                "run_id": run_id,
                "content_item_id": content_item.id,
                "seo_score": final_score,
                "iterations": len(refinement_history),
                "content_length": len(final_content),
                "created_at": datetime.now().isoformat(),
                "target_score": min_seo_score,
                "status": "current",
                "parameters": run_parameters,
                "refinement_history": [dict(iteration) for iteration in refinement_history],
                "sub_scores": sub_scores,
                "validation_metadata": metadata,
                "issues": (final_validation_result or {}).get("issues", []),
                "recommendations": (final_validation_result or {}).get("recommendations", []),
                "strengths": (final_validation_result or {}).get("strengths", []),
                "sub_score_details": sub_score_details
            }
            run_history_list.append(run_entry)
            updated_metadata = dict(existing_metadata)
            updated_metadata.update({
                "content_length": len(final_content),
                "tone": plan.tone or "professional",
                "seo_score": final_score,
                "refinement_iterations": len(refinement_history),
                "run_history": run_history_list,
                "current_run_id": run_id
            })

            await self.planning_service.update_plan_status(
                plan_id,
                ContentPlanStatus.DRAFT_READY.value,
                {
                    "research_data": research_data,
                    "generation_metadata": updated_metadata,
                    "latest_seo_score": final_score,
                    "refinement_history": refinement_history,
                    "message": f"Draft ready for review (SEO Score: {final_score}/100 after {len(refinement_history)} iterations)"
                }
            )
            plan = await self._commit_and_refresh_plan(plan_id)

            await emit_progress(
                "completed",
                f"Draft ready for '{plan.title}' (SEO {final_score}/100).",
                status="success",
                data={
                    "plan_id": plan_id,
                    "title": plan.title,
                    "content_item_id": content_item.id,
                    "seo_score": final_score
                }
            )

            # Step 5: Generate channel-specific variants (if channels specified)
            if plan.target_channels and len(plan.target_channels) > 0:
                logger.info(
                    "Generating channel variants",
                    plan_id=plan_id,
                    channels=plan.target_channels
                )

                try:
                    variants = await self.generation_service.generate_variants_per_channel(
                        content=final_content,
                        title=plan.title,
                        channels=plan.target_channels,
                        openai_api_key=openai_api_key,
                        prompt_settings=prompt_settings
                    )

                    # Save variants to database
                    for variant_data in variants:
                        variant = ContentVariant(
                            id=str(uuid.uuid4()),
                            tenant_id=self.tenant_id,
                            content_item_id=content_item.id,
                            connector_catalog_key=variant_data["channel"],
                            purpose="default",
                            body=variant_data["body"],
                            metadata=variant_data.get("variant_metadata", {})
                        )
                        self.db.add(variant)

                    await self.db.flush()

                    logger.info(
                        "Channel variants generated successfully",
                        plan_id=plan_id,
                        variant_count=len(variants)
                    )

                except Exception as variant_error:
                    # Don't fail the whole workflow if variant generation fails
                    logger.error(
                        "Failed to generate channel variants",
                        plan_id=plan_id,
                        error=str(variant_error)
                    )

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
                "content_length": len(final_content),
                "seo_score": final_score,
                "refinement_iterations": len(refinement_history),
                "target_achieved": final_score >= min_seo_score,
                "research_sources": len(research_data.get("sources", [])),
                "message": f"Content generated successfully (SEO: {final_score}/100 after {len(refinement_history)} iterations)"
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

            await emit_progress(
                "error",
                f"Content generation failed for '{plan_id}': {str(e)}",
                status="error",
                data={"plan_id": plan_id, "title": getattr(plan, "title", None)}
            )

            raise
