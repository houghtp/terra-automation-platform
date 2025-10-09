"""
Content Broadcaster service for multi-channel content publishing.

This service provides comprehensive content lifecycle management including
creation, approval workflows, scheduling, publishing job management,
and engagement tracking with full multi-tenant support.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import desc, and_, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    ContentItem, PublishJob, Delivery, EngagementSnapshot,
    ContentState, ApprovalStatus, JobStatus
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import BaseService
import structlog

logger = structlog.get_logger(__name__)


class ContentBroadcasterService(BaseService[ContentItem]):
    """
    Comprehensive content broadcasting service with multi-tenant support.

    Provides:
    - Content lifecycle management (draft → published)
    - Approval workflow management
    - Publishing job scheduling and management
    - Delivery tracking and engagement monitoring
    - Multi-tenant data isolation
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, tenant_id)

    # ==================== CONTENT MANAGEMENT ====================

    async def get_content_list(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        state: Optional[ContentState] = None,
        created_by: Optional[str] = None,
        approval_status: Optional[ApprovalStatus] = None
    ) -> Dict[str, Any]:
        """Get paginated list of content items with filtering."""
        try:
            # Build base query with tenant isolation
            query = select(ContentItem).filter(ContentItem.tenant_id == self.tenant_id)

            # Apply filters
            if search:
                query = query.filter(
                    or_(
                        ContentItem.title.ilike(f"%{search}%"),
                        ContentItem.body.ilike(f"%{search}%")
                    )
                )

            if state:
                query = query.filter(ContentItem.state == state.value)

            if created_by:
                query = query.filter(ContentItem.created_by == created_by)

            if approval_status:
                query = query.filter(ContentItem.approval_status == approval_status.value)

            # Get total count
            count_query = select(func.count(ContentItem.id)).filter(ContentItem.tenant_id == self.tenant_id)
            if search:
                count_query = count_query.filter(
                    or_(
                        ContentItem.title.ilike(f"%{search}%"),
                        ContentItem.body.ilike(f"%{search}%")
                    )
                )
            if state:
                count_query = count_query.filter(ContentItem.state == state.value)
            if created_by:
                count_query = count_query.filter(ContentItem.created_by == created_by)
            if approval_status:
                count_query = count_query.filter(ContentItem.approval_status == approval_status.value)

            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(ContentItem.created_at))
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            items = result.scalars().all()

            return {
                "data": [item.to_dict() for item in items],
                "total": total,
                "offset": offset,
                "limit": limit
            }

        except Exception as e:
            logger.exception(f"Failed to get content list for tenant {self.tenant_id}")
            raise

    async def get_content_by_id(self, content_id: str) -> Optional[ContentItem]:
        """Get content item by ID with tenant isolation."""
        try:
            query = select(ContentItem).filter(
                and_(
                    ContentItem.id == content_id,
                    ContentItem.tenant_id == self.tenant_id
                )
            ).options(selectinload(ContentItem.publish_jobs))

            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Failed to get content {content_id} for tenant {self.tenant_id}")
            raise

    async def create_content(
        self,
        title: str,
        body: str,
        created_by_user,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> ContentItem:
        """Create new content item in draft state."""
        # Create audit context
        audit_ctx = AuditContext.from_user(created_by_user)

        try:
            content = ContentItem(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                title=title,
                body=body,
                state=ContentState.DRAFT.value,
                approval_status=ApprovalStatus.PENDING.value,
                content_metadata=metadata or {},
                tags=tags or []
            )
            # Set audit information
            content.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            self.db.add(content)
            await self.db.flush()
            await self.db.refresh(content)

            logger.info(f"Created content: {content.title} (ID: {content.id}) for tenant {self.tenant_id}")
            return content

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to create content for tenant {self.tenant_id}")
            raise

    async def update_content(
        self,
        content_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        updated_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[ContentItem]:
        """Update existing content item."""
        try:
            content = await self.get_content_by_id(content_id)
            if not content:
                return None

            # Only allow updates if content is in draft or rejected state
            if content.state not in [ContentState.DRAFT.value, ContentState.REJECTED.value]:
                raise ValueError(f"Cannot update content in {content.state} state")

            if title is not None:
                content.title = title
            if body is not None:
                content.body = body
            if updated_by is not None:
                content.updated_by = updated_by
            if metadata is not None:
                content.content_metadata = metadata
            if tags is not None:
                content.tags = tags

            content.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(content)

            return content

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to update content {content_id} for tenant {self.tenant_id}")
            raise

    async def submit_for_review(self, content_id: str, updated_by: str) -> Optional[ContentItem]:
        """Submit content for review (draft → in_review)."""
        try:
            content = await self.get_content_by_id(content_id)
            if not content:
                return None

            if content.state != ContentState.DRAFT.value:
                raise ValueError(f"Cannot submit content in {content.state} state for review")

            content.state = ContentState.IN_REVIEW.value
            content.approval_status = ApprovalStatus.PENDING.value
            content.updated_by = updated_by
            content.updated_at = datetime.now(timezone.utc)

            await self.db.flush()
            await self.db.refresh(content)

            logger.info(f"Submitted content {content_id} for review")
            return content

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to submit content {content_id} for review")
            raise

    # ==================== APPROVAL WORKFLOW ====================

    async def get_pending_approvals(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get content items pending approval."""
        try:
            query = select(ContentItem).filter(
                and_(
                    ContentItem.tenant_id == self.tenant_id,
                    ContentItem.state == ContentState.IN_REVIEW.value,
                    ContentItem.approval_status == ApprovalStatus.PENDING.value
                )
            ).order_by(desc(ContentItem.created_at))

            # Get total count
            count_query = select(func.count(ContentItem.id)).filter(
                and_(
                    ContentItem.tenant_id == self.tenant_id,
                    ContentItem.state == ContentState.IN_REVIEW.value,
                    ContentItem.approval_status == ApprovalStatus.PENDING.value
                )
            )

            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            query = query.offset(offset).limit(limit)
            result = await self.db.execute(query)
            items = result.scalars().all()

            return {
                "data": [item.to_dict() for item in items],
                "total": total,
                "offset": offset,
                "limit": limit
            }

        except Exception as e:
            logger.exception(f"Failed to get pending approvals for tenant {self.tenant_id}")
            raise

    async def approve_content(
        self,
        content_id: str,
        approved_by: str,
        comment: Optional[str] = None,
        auto_schedule: bool = False
    ) -> Optional[ContentItem]:
        """Approve content for publishing."""
        try:
            content = await self.get_content_by_id(content_id)
            if not content:
                return None

            if content.state != ContentState.IN_REVIEW.value:
                raise ValueError(f"Cannot approve content in {content.state} state")

            content.approval_status = ApprovalStatus.APPROVED.value
            content.approved_by = approved_by
            content.approved_at = datetime.now(timezone.utc)
            content.approval_comment = comment

            # Move to scheduled state if has scheduled_at time
            if auto_schedule and content.scheduled_at:
                content.state = ContentState.SCHEDULED.value
            else:
                content.state = ContentState.DRAFT.value  # Back to draft for scheduling

            await self.db.flush()
            await self.db.refresh(content)

            logger.info(f"Approved content {content_id} by user {approved_by}")
            return content

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to approve content {content_id}")
            raise

    async def reject_content(
        self,
        content_id: str,
        rejected_by: str,
        comment: str
    ) -> Optional[ContentItem]:
        """Reject content and return to draft."""
        try:
            content = await self.get_content_by_id(content_id)
            if not content:
                return None

            if content.state != ContentState.IN_REVIEW.value:
                raise ValueError(f"Cannot reject content in {content.state} state")

            content.state = ContentState.REJECTED.value
            content.approval_status = ApprovalStatus.REJECTED.value
            content.approved_by = rejected_by
            content.approved_at = datetime.now(timezone.utc)
            content.approval_comment = comment

            await self.db.flush()
            await self.db.refresh(content)

            logger.info(f"Rejected content {content_id} by user {rejected_by}")
            return content

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to reject content {content_id}")
            raise

    # ==================== SCHEDULING & PUBLISHING ====================

    async def schedule_content(
        self,
        content_id: str,
        scheduled_at: datetime,
        connector_ids: List[str],
        updated_by: str
    ) -> Optional[ContentItem]:
        """Schedule content for publishing to specified connectors."""
        try:
            content = await self.get_content_by_id(content_id)
            if not content:
                return None

            # Content must be approved before scheduling
            if content.approval_status != ApprovalStatus.APPROVED.value:
                raise ValueError("Content must be approved before scheduling")

            if content.state not in [ContentState.DRAFT.value, ContentState.SCHEDULED.value]:
                raise ValueError(f"Cannot schedule content in {content.state} state")

            # Update content
            content.scheduled_at = scheduled_at
            content.state = ContentState.SCHEDULED.value
            content.updated_by = updated_by
            content.updated_at = datetime.now(timezone.utc)

            # Create publish jobs for each connector
            for connector_id in connector_ids:
                job = PublishJob(
                    id=str(uuid.uuid4()),
                    tenant_id=self.tenant_id,
                    content_item_id=content_id,
                    connector_id=connector_id,
                    run_at=scheduled_at,
                    status=JobStatus.QUEUED.value
                )
                self.db.add(job)

            await self.db.flush()
            await self.db.refresh(content)

            logger.info(f"Scheduled content {content_id} for {len(connector_ids)} connectors")
            return content

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to schedule content {content_id}")
            raise

    # ==================== JOB MANAGEMENT ====================

    async def get_publish_jobs(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[JobStatus] = None,
        connector_id: Optional[str] = None,
        content_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of publish jobs."""
        try:
            query = select(PublishJob).filter(
                PublishJob.tenant_id == self.tenant_id
            ).options(selectinload(PublishJob.content_item))

            # Apply filters
            if status:
                query = query.filter(PublishJob.status == status.value)
            if connector_id:
                query = query.filter(PublishJob.connector_id == connector_id)
            if content_id:
                query = query.filter(PublishJob.content_item_id == content_id)

            # Get total count
            count_query = select(func.count(PublishJob.id)).filter(PublishJob.tenant_id == self.tenant_id)
            if status:
                count_query = count_query.filter(PublishJob.status == status.value)
            if connector_id:
                count_query = count_query.filter(PublishJob.connector_id == connector_id)
            if content_id:
                count_query = count_query.filter(PublishJob.content_item_id == content_id)

            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(PublishJob.run_at))
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            jobs = result.scalars().all()

            return {
                "data": [job.to_dict() for job in jobs],
                "total": total,
                "offset": offset,
                "limit": limit
            }

        except Exception as e:
            logger.exception(f"Failed to get publish jobs for tenant {self.tenant_id}")
            raise

    async def retry_job(self, job_id: str) -> Optional[PublishJob]:
        """Retry a failed publish job."""
        try:
            query = select(PublishJob).filter(
                and_(
                    PublishJob.id == job_id,
                    PublishJob.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                return None

            if job.status not in [JobStatus.FAILED.value, JobStatus.CANCELED.value]:
                raise ValueError(f"Cannot retry job in {job.status} state")

            job.status = JobStatus.QUEUED.value
            job.last_error = None
            job.updated_at = datetime.now(timezone.utc)

            await self.db.flush()
            await self.db.refresh(job)

            logger.info(f"Retrying publish job {job_id}")
            return job

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to retry job {job_id}")
            raise

    async def cancel_job(self, job_id: str) -> Optional[PublishJob]:
        """Cancel a queued publish job."""
        try:
            query = select(PublishJob).filter(
                and_(
                    PublishJob.id == job_id,
                    PublishJob.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                return None

            if job.status not in [JobStatus.QUEUED.value, JobStatus.RETRYING.value]:
                raise ValueError(f"Cannot cancel job in {job.status} state")

            job.status = JobStatus.CANCELED.value
            job.updated_at = datetime.now(timezone.utc)

            await self.db.flush()
            await self.db.refresh(job)

            logger.info(f"Canceled publish job {job_id}")
            return job

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to cancel job {job_id}")
            raise

    # ==================== DELIVERY & ENGAGEMENT ====================

    async def create_delivery(
        self,
        job_id: str,
        external_post_id: str,
        permalink: Optional[str] = None,
        response_json: Optional[Dict[str, Any]] = None
    ) -> Delivery:
        """Create delivery record for successful publish."""
        try:
            delivery = Delivery(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                publish_job_id=job_id,
                external_post_id=external_post_id,
                permalink=permalink,
                response_json=response_json
            )

            self.db.add(delivery)
            await self.db.flush()
            await self.db.refresh(delivery)

            logger.info(f"Created delivery record for job {job_id}")
            return delivery

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to create delivery for job {job_id}")
            raise

    async def record_engagement(
        self,
        delivery_id: str,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        views: int = 0,
        metrics_json: Optional[Dict[str, Any]] = None
    ) -> EngagementSnapshot:
        """Record engagement snapshot for delivered content."""
        try:
            snapshot = EngagementSnapshot(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                delivery_id=delivery_id,
                captured_at=datetime.now(timezone.utc),
                likes=likes,
                comments=comments,
                shares=shares,
                views=views,
                metrics_json=metrics_json
            )

            self.db.add(snapshot)
            await self.db.flush()
            await self.db.refresh(snapshot)

            return snapshot

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to record engagement for delivery {delivery_id}")
            raise

    # ==================== DASHBOARD STATS ====================

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics for content broadcasting."""
        try:
            # Content counts by state
            state_counts = {}
            for state in ContentState:
                count_query = select(func.count(ContentItem.id)).filter(
                    and_(
                        ContentItem.tenant_id == self.tenant_id,
                        ContentItem.state == state.value
                    )
                )
                result = await self.db.execute(count_query)
                state_counts[state.value] = result.scalar()

            # Recent content items
            recent_query = select(ContentItem).filter(
                ContentItem.tenant_id == self.tenant_id
            ).order_by(desc(ContentItem.created_at)).limit(5)

            recent_result = await self.db.execute(recent_query)
            recent_content = [item.to_dict() for item in recent_result.scalars().all()]

            # Pending approvals count
            pending_count_query = select(func.count(ContentItem.id)).filter(
                and_(
                    ContentItem.tenant_id == self.tenant_id,
                    ContentItem.state == ContentState.IN_REVIEW.value,
                    ContentItem.approval_status == ApprovalStatus.PENDING.value
                )
            )
            pending_result = await self.db.execute(pending_count_query)
            pending_approvals = pending_result.scalar()

            # Upcoming scheduled jobs
            upcoming_query = select(PublishJob).filter(
                and_(
                    PublishJob.tenant_id == self.tenant_id,
                    PublishJob.status == JobStatus.QUEUED.value,
                    PublishJob.run_at > datetime.now(timezone.utc)
                )
            ).order_by(PublishJob.run_at).limit(5)

            upcoming_result = await self.db.execute(upcoming_query)
            upcoming_jobs = [job.to_dict() for job in upcoming_result.scalars().all()]

            return {
                "content_by_state": state_counts,
                "recent_content": recent_content,
                "pending_approvals": pending_approvals,
                "upcoming_jobs": upcoming_jobs,
                "total_content": sum(state_counts.values())
            }

        except Exception as e:
            logger.exception(f"Failed to get dashboard stats for tenant {self.tenant_id}")
            raise

    async def delete_content(self, content_id: str) -> bool:
        """Delete content item and all related data."""
        try:
            content = await self.get_content_by_id(content_id)
            if not content:
                return False

            # Can only delete draft or rejected content
            if content.state not in [ContentState.DRAFT.value, ContentState.REJECTED.value]:
                raise ValueError(f"Cannot delete content in {content.state} state")

            await self.db.delete(content)
            await self.db.flush()

            logger.info(f"Deleted content {content_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Failed to delete content {content_id}")
            raise
