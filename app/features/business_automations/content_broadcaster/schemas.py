"""
Pydantic schemas for the Content Broadcaster feature slice.

Keeping request/response models alongside the feature ensures the API contract
stays co-located with the business logic while remaining decoupled from the
SQLAlchemy models.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)


class ContentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    body: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ContentScheduleRequest(BaseModel):
    scheduled_at: datetime
    connector_ids: List[str] = Field(..., min_items=1)


class ApprovalRequest(BaseModel):
    comment: Optional[str] = None
    auto_schedule: bool = False


class RejectRequest(BaseModel):
    comment: str = Field(..., min_length=1)


class SEOContentGenerationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    ai_provider: str = Field(default="openai")
    fallback_ai: Optional[str] = Field(default="anthropic")
    search_provider: str = Field(default="serpapi")
    scraping_provider: str = Field(default="firecrawl")
    min_seo_score: int = Field(default=95, ge=80, le=100)
    max_iterations: int = Field(default=3, ge=1, le=5)
    auto_approve: bool = Field(default=False)


class ContentPlanCreate(BaseModel):
    """Request model for creating a content plan from the planning routes."""

    title: str = Field(..., min_length=3, max_length=500, description="Content topic or idea")
    description: Optional[str] = Field(None, description="Additional context or instructions")
    target_channels: Optional[List[str]] = Field(
        default=None,
        description="Target channels (e.g., ['wordpress', 'twitter'])"
    )
    target_audience: Optional[str] = Field(None, description="Target audience description")
    tone: Optional[str] = Field("professional", description="Writing tone")
    seo_keywords: Optional[List[str]] = Field(default=None, description="SEO keywords")
    competitor_urls: Optional[List[str]] = Field(
        default=None,
        description="Competitor URLs to analyze"
    )
    min_seo_score: int = Field(95, ge=80, le=100, description="Target SEO score")
    max_iterations: int = Field(3, ge=1, le=5, description="Max refinement iterations")
    prompt_settings: Optional[Dict[str, int]] = Field(default_factory=dict, description="Prompt tuning controls")


class ProcessPlanRequest(BaseModel):
    """Request model for processing a content plan with AI."""

    use_research: bool = Field(
        default=True,
        description="Whether to perform competitor research"
    )


__all__ = [
    "ApprovalRequest",
    "ContentCreateRequest",
    "ContentPlanCreate",
    "ContentScheduleRequest",
    "ContentUpdateRequest",
    "ProcessPlanRequest",
    "RejectRequest",
    "SEOContentGenerationRequest",
]
