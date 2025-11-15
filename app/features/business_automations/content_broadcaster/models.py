"""
Content Broadcaster models for multi-channel content publishing.

This module defines the database models for the content broadcasting system,
supporting multi-tenant content management, approval workflows, scheduling,
and publishing across various connectors.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class ContentPlanStatus(str, Enum):
    """Content plan status enumeration."""
    PLANNED = "planned"
    RESEARCHING = "researching"
    GENERATING = "generating"
    REFINING = "refining"
    DRAFT_READY = "draft_ready"
    APPROVED = "approved"
    ARCHIVED = "archived"
    FAILED = "failed"


class ContentState(str, Enum):
    """Content item state enumeration."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    """Content approval status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class JobStatus(str, Enum):
    """Publish job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELED = "canceled"


class VariantPurpose(str, Enum):
    """Content variant purpose enumeration."""
    DEFAULT = "default"
    SHORT = "short"
    LONG = "long"
    TEASER = "teaser"
    SUMMARY = "summary"
    A = "A"
    B = "B"


class ContentPlan(Base, AuditMixin):
    """
    Content planning table - the entry point for AI-driven content generation.

    Users create content plans with topic ideas, and background workers automatically:
    1. Research competitors and analyze SEO opportunities
    2. Generate first drafts using AI
    3. Validate and score content (0-100)
    4. Iteratively refine until SEO score meets target
    5. Present final draft to users for approval
    """
    __tablename__ = "content_plans"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Content idea/topic
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Target configuration
    target_channels = Column(JSON, nullable=False, default=list)  # ["wordpress", "twitter", "linkedin"]
    target_audience = Column(String(100), nullable=True)  # "developers", "executives"
    tone = Column(String(50), nullable=True)  # "professional", "casual", "technical"
    seo_keywords = Column(JSON, nullable=False, default=list)  # Optional user-provided keywords
    competitor_urls = Column(JSON, nullable=False, default=list)  # Optional URLs to analyze

    # AI generation parameters
    min_seo_score = Column(Integer, nullable=False, default=95)  # Target SEO score (80-100)
    max_iterations = Column(Integer, nullable=False, default=3)  # Max refinement loops
    skip_research = Column(Boolean, nullable=False, default=False)  # Skip competitor research phase

    # Status tracking
    status = Column(String(20), nullable=False, default=ContentPlanStatus.PLANNED.value, index=True)
    current_iteration = Column(Integer, nullable=False, default=0)
    latest_seo_score = Column(Integer, nullable=True)

    # Processing results (JSONB for flexible storage)
    research_data = Column(JSONB, nullable=False, default=dict)
    # Structure: {
    #   "top_results": [{"title": "...", "url": "...", "scraped_content": "..."}],
    #   "seo_analysis": "AI-generated SEO gap analysis",
    #   "keywords_found": ["api", "best practices", ...]
    # }

    generation_metadata = Column(JSONB, nullable=False, default=dict)
    # Structure: {
    #   "model": "gpt-4",
    #   "prompt_tokens": 1500,
    #   "completion_tokens": 2000,
    #   "cost_estimate": 0.15,
    #   "generated_at": "2025-10-11T..."
    # }

    refinement_history = Column(JSONB, nullable=False, default=list)
    # Structure: [
    #   {
    #     "iteration": 1,
    #     "score": 78,
    #     "issues": ["Schema Markup", "Keyword Density"],
    #     "feedback": {...},
    #     "refined_at": "2025-10-11T..."
    #   },
    #   ...
    # ]

    prompt_settings = Column(JSONB, nullable=False, default=dict)

    # Link to generated content item (one-to-one)
    generated_content_item_id = Column(String(36), ForeignKey("content_items.id"), nullable=True, index=True)

    # Error handling
    error_log = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Relationships
    generated_content = relationship("ContentItem", foreign_keys=[generated_content_item_id], uselist=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "target_channels": self.target_channels or [],
            "target_audience": self.target_audience,
            "tone": self.tone,
            "seo_keywords": self.seo_keywords or [],
            "competitor_urls": self.competitor_urls or [],
            "min_seo_score": self.min_seo_score,
            "max_iterations": self.max_iterations,
            "skip_research": self.skip_research,
            "status": self.status,
            "current_iteration": self.current_iteration,
            "latest_seo_score": self.latest_seo_score,
            "research_data": self.research_data or {},
            "generation_metadata": self.generation_metadata or {},
            "refinement_history": self.refinement_history or [],
            "prompt_settings": self.prompt_settings or {},
            "generated_content_item_id": self.generated_content_item_id,
            "error_log": self.error_log,
            "retry_count": self.retry_count,
        }
        # Add audit information
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        return f"<ContentPlan(id={self.id}, tenant_id='{self.tenant_id}', title='{self.title}', status='{self.status}')>"


class ContentItem(Base, AuditMixin):
    """
    Content items for multi-channel broadcasting.

    Supports content lifecycle from draft through approval, scheduling,
    and publishing with full audit trail and multi-tenant isolation.
    """
    __tablename__ = "content_items"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Core content fields
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    # State management
    state = Column(String(20), nullable=False, default=ContentState.DRAFT.value, index=True)

    # Scheduling fields
    scheduled_at = Column(DateTime, nullable=True, index=True)  # When user plans to publish
    publish_at = Column(DateTime, nullable=True, index=True)   # Actual publish timestamp

    # Approval workflow
    approval_status = Column(String(20), nullable=False, default=ApprovalStatus.PENDING.value, index=True)
    approved_by = Column(String(36), nullable=True)  # User ID who approved
    approved_at = Column(DateTime, nullable=True)
    approval_comment = Column(Text, nullable=True)

    # Note: Audit fields are now provided by AuditMixin with human-readable data

    # Metadata and tags
    content_metadata = Column(JSONB, nullable=True)
    tags = Column(JSON, nullable=True, default=list)

    # Relationships
    publish_jobs = relationship("PublishJob", back_populates="content_item", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "publish_at": self.publish_at.isoformat() if self.publish_at else None,
            "approval_status": self.approval_status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_comment": self.approval_comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "content_metadata": self.content_metadata,
            "tags": self.tags or [],
        }
        # Add audit information with human-readable data
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        return f"<ContentItem(id={self.id}, tenant_id='{self.tenant_id}', title='{self.title}', state='{self.state}')>"


class ContentVariant(Base):
    """
    Per-channel content variants for multi-platform publishing.

    Each content item can have multiple variants optimized for different
    platforms (Twitter 280 chars, LinkedIn professional, WordPress long-form, etc.)
    """
    __tablename__ = "content_variants"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Relationship to parent content
    content_item_id = Column(String(36), ForeignKey("content_items.id"), nullable=False, index=True)

    # Channel identification
    connector_catalog_key = Column(String(100), nullable=False, index=True)  # "twitter", "wordpress", "linkedin"

    # Variant purpose/type
    purpose = Column(String(20), nullable=False, default=VariantPurpose.DEFAULT.value)

    # Channel-optimized content
    body = Column(Text, nullable=False)

    # Variant metadata (channel-specific formatting, constraints)
    # Note: Cannot use 'metadata' as column name - it's reserved by SQLAlchemy
    variant_metadata = Column(JSONB, nullable=False, default=dict)
    # Structure: {
    #   "char_count": 240,
    #   "hashtags": ["#API", "#Development"],
    #   "html": true,
    #   "mentions": ["@username"],
    #   "truncated": false
    # }

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    content_item = relationship("ContentItem", foreign_keys=[content_item_id])

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "content_item_id": self.content_item_id,
            "connector_catalog_key": self.connector_catalog_key,
            "purpose": self.purpose,
            "body": self.body,
            "variant_metadata": self.variant_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ContentVariant(id={self.id}, content_item_id='{self.content_item_id}', channel='{self.connector_catalog_key}', purpose='{self.purpose}')>"


class PublishJob(Base):
    """
    Individual publish jobs for each connector per content item.

    Tracks the execution of publishing content to specific connectors
    with retry logic and status monitoring.
    """
    __tablename__ = "publish_jobs"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Relationships
    content_item_id = Column(String(36), ForeignKey("content_items.id"), nullable=False, index=True)
    connector_id = Column(String(36), nullable=False, index=True)  # References connector system

    # Execution scheduling
    run_at = Column(DateTime, nullable=False, index=True)

    # Status tracking
    status = Column(String(20), nullable=False, default=JobStatus.QUEUED.value, index=True)
    attempt = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc), index=True)

    # Execution metadata
    execution_metadata = Column(JSONB, nullable=True)

    # Relationships
    content_item = relationship("ContentItem", back_populates="publish_jobs")
    deliveries = relationship("Delivery", back_populates="publish_job", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "content_item_id": self.content_item_id,
            "connector_id": self.connector_id,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "status": self.status,
            "attempt": self.attempt,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "execution_metadata": self.execution_metadata,
        }

    def __repr__(self) -> str:
        return f"<PublishJob(id={self.id}, content_item_id='{self.content_item_id}', status='{self.status}')>"


class Delivery(Base):
    """
    Successful delivery records for published content.

    Stores the results of successful publishes including external
    post IDs and permalinks for tracking and engagement monitoring.
    """
    __tablename__ = "deliveries"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Relationship
    publish_job_id = Column(String(36), ForeignKey("publish_jobs.id"), nullable=False, index=True)

    # External platform data
    external_post_id = Column(String(255), nullable=False, index=True)
    permalink = Column(String(1000), nullable=True)
    response_json = Column(JSONB, nullable=True)

    # Tracking
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    publish_job = relationship("PublishJob", back_populates="deliveries")
    engagement_snapshots = relationship("EngagementSnapshot", back_populates="delivery", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "publish_job_id": self.publish_job_id,
            "external_post_id": self.external_post_id,
            "permalink": self.permalink,
            "response_json": self.response_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Delivery(id={self.id}, external_post_id='{self.external_post_id}')>"


class EngagementSnapshot(Base):
    """
    Engagement metrics snapshots for delivered content.

    Tracks engagement metrics over time for published content
    including likes, comments, shares, and views.
    """
    __tablename__ = "engagement_snapshots"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Relationship
    delivery_id = Column(String(36), ForeignKey("deliveries.id"), nullable=False, index=True)

    # Snapshot timing
    captured_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Engagement metrics
    likes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    views = Column(Integer, nullable=False, default=0)

    # Extended metrics
    metrics_json = Column(JSONB, nullable=True)

    # Relationships
    delivery = relationship("Delivery", back_populates="engagement_snapshots")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "delivery_id": self.delivery_id,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "views": self.views,
            "metrics_json": self.metrics_json,
        }

    def __repr__(self) -> str:
        return f"<EngagementSnapshot(id={self.id}, delivery_id='{self.delivery_id}', captured_at='{self.captured_at}')>"
