"""
Shared Pydantic models for Content Broadcaster routes.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ==================== PYDANTIC MODELS ====================

class ContentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    metadata: Optional[dict] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)


class ContentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    body: Optional[str] = Field(None, min_length=1)
    metadata: Optional[dict] = None
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

