"""
Integration tests for Content Broadcaster slice.

Tests the complete functionality including models, services, and routes
with proper multi-tenant isolation and workflow state transitions.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.features.core.database import get_db
from app.features.business_automations.content_broadcaster.models import (
    ContentItem, PublishJob, ContentState, ApprovalStatus, JobStatus
)
from app.features.business_automations.content_broadcaster.services import ContentBroadcasterService


@pytest.mark.asyncio
class TestContentBroadcasterModels:
    """Test the data models and their relationships."""

    async def test_content_item_creation(self, async_db_session: AsyncSession):
        """Test creating a content item with proper defaults."""
        content = ContentItem(
            id="test-content-1",
            tenant_id="test-tenant",
            title="Test Content",
            body="This is test content body",
            state=ContentState.DRAFT.value,
            approval_status=ApprovalStatus.PENDING.value,
            created_by="test@example.com"
        )

        async_db_session.add(content)
        await async_db_session.commit()
        await async_db_session.refresh(content)

        assert content.id == "test-content-1"
        assert content.tenant_id == "test-tenant"
        assert content.state == ContentState.DRAFT.value
        assert content.approval_status == ApprovalStatus.PENDING.value
        assert content.created_at is not None
        assert content.updated_at is not None

    async def test_content_item_to_dict(self, async_db_session: AsyncSession):
        """Test the to_dict method returns proper dictionary."""
        content = ContentItem(
            id="test-content-2",
            tenant_id="test-tenant",
            title="Test Content",
            body="Test body",
            state=ContentState.DRAFT.value,
            approval_status=ApprovalStatus.PENDING.value,
            created_by="test@example.com",
            tags=["test", "automation"]
        )

        result_dict = content.to_dict()

        assert result_dict["id"] == "test-content-2"
        assert result_dict["tenant_id"] == "test-tenant"
        assert result_dict["title"] == "Test Content"
        assert result_dict["tags"] == ["test", "automation"]
        assert "created_at" in result_dict
        assert "updated_at" in result_dict

    async def test_publish_job_creation(self, async_db_session: AsyncSession):
        """Test creating a publish job linked to content."""
        # First create content
        content = ContentItem(
            id="test-content-3",
            tenant_id="test-tenant",
            title="Test Content",
            body="Test body",
            state=ContentState.SCHEDULED.value,
            approval_status=ApprovalStatus.APPROVED.value,
            created_by="test@example.com"
        )
        async_db_session.add(content)

        # Create publish job
        job = PublishJob(
            id="test-job-1",
            tenant_id="test-tenant",
            content_item_id="test-content-3",
            connector_id="twitter",
            run_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status=JobStatus.QUEUED.value
        )
        async_db_session.add(job)

        await async_db_session.commit()
        await async_db_session.refresh(job)

        assert job.id == "test-job-1"
        assert job.content_item_id == "test-content-3"
        assert job.connector_id == "twitter"
        assert job.status == JobStatus.QUEUED.value


@pytest.mark.asyncio
class TestContentBroadcasterService:
    """Test the service layer functionality."""

    async def test_create_content(self, async_db_session: AsyncSession):
        """Test creating content through service."""
        service = ContentBroadcasterService(async_db_session, "test-tenant")

        content = await service.create_content(
            title="Service Test Content",
            body="Content created through service",
            created_by="service-test@example.com",
            tags=["service", "test"]
        )

        assert content.title == "Service Test Content"
        assert content.state == ContentState.DRAFT.value
        assert content.approval_status == ApprovalStatus.PENDING.value
        assert content.tenant_id == "test-tenant"
        assert content.tags == ["service", "test"]

    async def test_content_workflow_transitions(self, async_db_session: AsyncSession):
        """Test the content approval workflow."""
        service = ContentBroadcasterService(async_db_session, "test-tenant")

        # Create content
        content = await service.create_content(
            title="Workflow Test",
            body="Testing workflow transitions",
            created_by="workflow-test@example.com"
        )

        # Submit for review
        updated_content = await service.submit_for_review(
            content.id, "workflow-test@example.com"
        )
        assert updated_content.state == ContentState.IN_REVIEW.value

        # Approve content
        approved_content = await service.approve_content(
            content.id, "approver@example.com", "Looks good!"
        )
        assert approved_content.approval_status == ApprovalStatus.APPROVED.value

    async def test_content_scheduling(self, async_db_session: AsyncSession):
        """Test scheduling approved content."""
        service = ContentBroadcasterService(async_db_session, "test-tenant")

        # Create and approve content
        content = await service.create_content(
            title="Schedule Test",
            body="Testing scheduling",
            created_by="schedule-test@example.com"
        )

        await service.submit_for_review(content.id, "schedule-test@example.com")
        await service.approve_content(content.id, "approver@example.com")

        # Schedule content
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduled_content = await service.schedule_content(
            content.id,
            scheduled_at,
            ["twitter", "linkedin"],
            "scheduler@example.com"
        )

        assert scheduled_content.state == ContentState.SCHEDULED.value
        assert scheduled_content.scheduled_at == scheduled_at

        # Check that publish jobs were created
        jobs = await service.get_publish_jobs(content_id=content.id)
        assert jobs["total"] == 2  # Two connectors
        assert len(jobs["data"]) == 2

    async def test_tenant_isolation(self, async_db_session: AsyncSession):
        """Test that tenant isolation works properly."""
        service1 = ContentBroadcasterService(async_db_session, "tenant-1")
        service2 = ContentBroadcasterService(async_db_session, "tenant-2")

        # Create content in tenant 1
        content1 = await service1.create_content(
            title="Tenant 1 Content",
            body="Content for tenant 1",
            created_by="user1@tenant1.com"
        )

        # Create content in tenant 2
        content2 = await service2.create_content(
            title="Tenant 2 Content",
            body="Content for tenant 2",
            created_by="user2@tenant2.com"
        )

        # Service 1 should only see tenant 1 content
        tenant1_content = await service1.get_content_list()
        assert tenant1_content["total"] == 1
        assert tenant1_content["data"][0]["title"] == "Tenant 1 Content"

        # Service 2 should only see tenant 2 content
        tenant2_content = await service2.get_content_list()
        assert tenant2_content["total"] == 1
        assert tenant2_content["data"][0]["title"] == "Tenant 2 Content"

        # Cross-tenant access should return None
        cross_tenant_content = await service1.get_content_by_id(content2.id)
        assert cross_tenant_content is None

    async def test_dashboard_stats(self, async_db_session: AsyncSession):
        """Test dashboard statistics generation."""
        service = ContentBroadcasterService(async_db_session, "stats-tenant")

        # Create various content items in different states
        draft_content = await service.create_content(
            title="Draft Content", body="Draft", created_by="stats@example.com"
        )

        review_content = await service.create_content(
            title="Review Content", body="Review", created_by="stats@example.com"
        )
        await service.submit_for_review(review_content.id, "stats@example.com")

        approved_content = await service.create_content(
            title="Approved Content", body="Approved", created_by="stats@example.com"
        )
        await service.submit_for_review(approved_content.id, "stats@example.com")
        await service.approve_content(approved_content.id, "approver@example.com")

        # Get dashboard stats
        stats = await service.get_dashboard_stats()

        assert stats["total_content"] == 3
        assert stats["content_by_state"]["draft"] == 1
        assert stats["content_by_state"]["in_review"] == 1
        assert stats["pending_approvals"] == 1
        assert len(stats["recent_content"]) == 3


class TestContentBroadcasterRoutes:
    """Test the API routes and HTMX endpoints."""

    def test_main_page_loads(self):
        """Test that the main content broadcaster page loads."""
        client = TestClient(app)

        # This will likely require authentication in real scenario
        # For now, test that the route exists
        response = client.get("/features/content-broadcaster/")

        # May return 401 or redirect due to auth requirements
        assert response.status_code in [200, 302, 401]

    def test_api_endpoints_exist(self):
        """Test that API endpoints are properly registered."""
        client = TestClient(app)

        # Test API list endpoint (may require auth)
        response = client.get("/features/content-broadcaster/api/list")
        assert response.status_code in [200, 401, 422]  # 422 for missing dependencies

        # Test create endpoint (may require auth)
        response = client.post("/features/content-broadcaster/api/create", json={
            "title": "API Test",
            "body": "Test content creation via API"
        })
        assert response.status_code in [200, 401, 422]


@pytest.mark.asyncio
class TestContentBroadcasterIntegration:
    """Integration tests combining multiple components."""

    async def test_full_content_lifecycle(self, async_db_session: AsyncSession):
        """Test the complete content lifecycle from creation to scheduling."""
        service = ContentBroadcasterService(async_db_session, "lifecycle-tenant")

        # 1. Create content
        content = await service.create_content(
            title="Lifecycle Test Content",
            body="This content will go through the full lifecycle",
            created_by="lifecycle@example.com",
            tags=["integration", "test", "lifecycle"]
        )

        assert content.state == ContentState.DRAFT.value
        assert content.approval_status == ApprovalStatus.PENDING.value

        # 2. Update content
        updated_content = await service.update_content(
            content.id,
            title="Updated Lifecycle Test Content",
            body="This content has been updated",
            updated_by="lifecycle@example.com"
        )

        assert updated_content.title == "Updated Lifecycle Test Content"
        assert updated_content.state == ContentState.DRAFT.value

        # 3. Submit for review
        review_content = await service.submit_for_review(
            content.id, "lifecycle@example.com"
        )

        assert review_content.state == ContentState.IN_REVIEW.value

        # 4. Approve content
        approved_content = await service.approve_content(
            content.id,
            "approver@example.com",
            "Content looks great, approved for publishing!"
        )

        assert approved_content.approval_status == ApprovalStatus.APPROVED.value
        assert approved_content.approved_by == "approver@example.com"

        # 5. Schedule for publishing
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)
        scheduled_content = await service.schedule_content(
            content.id,
            scheduled_at,
            ["twitter", "linkedin", "facebook"],
            "scheduler@example.com"
        )

        assert scheduled_content.state == ContentState.SCHEDULED.value
        assert scheduled_content.scheduled_at == scheduled_at

        # 6. Verify publish jobs were created
        jobs = await service.get_publish_jobs(content_id=content.id)
        assert jobs["total"] == 3

        job_connectors = [job["connector_id"] for job in jobs["data"]]
        assert "twitter" in job_connectors
        assert "linkedin" in job_connectors
        assert "facebook" in job_connectors

        # 7. Test job management
        first_job = jobs["data"][0]

        # Cancel a job
        cancelled_job = await service.cancel_job(first_job["id"])
        assert cancelled_job.status == JobStatus.CANCELED.value

        # Retry the cancelled job
        retried_job = await service.retry_job(first_job["id"])
        assert retried_job.status == JobStatus.QUEUED.value

    async def test_rejection_workflow(self, async_db_session: AsyncSession):
        """Test content rejection and re-submission workflow."""
        service = ContentBroadcasterService(async_db_session, "rejection-tenant")

        # Create and submit content
        content = await service.create_content(
            title="Content for Rejection",
            body="This content will be rejected",
            created_by="reject-test@example.com"
        )

        await service.submit_for_review(content.id, "reject-test@example.com")

        # Reject the content
        rejected_content = await service.reject_content(
            content.id,
            "reviewer@example.com",
            "Content needs more detail and better formatting"
        )

        assert rejected_content.state == ContentState.REJECTED.value
        assert rejected_content.approval_status == ApprovalStatus.REJECTED.value
        assert rejected_content.approval_comment == "Content needs more detail and better formatting"

        # Update the rejected content
        updated_content = await service.update_content(
            content.id,
            body="This content has been updated with more detail and better formatting",
            updated_by="reject-test@example.com"
        )

        # Re-submit for review
        resubmitted_content = await service.submit_for_review(
            content.id, "reject-test@example.com"
        )

        assert resubmitted_content.state == ContentState.IN_REVIEW.value
        assert resubmitted_content.approval_status == ApprovalStatus.PENDING.value

        # Approve the resubmitted content
        final_content = await service.approve_content(
            content.id,
            "reviewer@example.com",
            "Much better! Approved."
        )

        assert final_content.approval_status == ApprovalStatus.APPROVED.value
