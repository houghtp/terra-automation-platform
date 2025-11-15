"""AI Prompt model for managing AI prompt templates with variable placeholders."""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.features.core.database import Base


class AIPrompt(Base):
    """
    Configurable AI prompts with Jinja2 template support and variable placeholders.

    This model allows tenants to customize AI behavior by editing prompt templates
    used for content generation, channel adaptation, and refinement operations.
    """
    __tablename__ = "ai_prompts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Tenant isolation (nullable for system prompts)
    tenant_id = Column(String(255), nullable=True, index=True)
    # System prompts have tenant_id=None, tenant overrides have specific tenant_id

    # Prompt identification
    prompt_key = Column(String(255), nullable=False, index=True)
    # Unique identifier like "seo_blog_generation", "channel_variant_twitter"
    # Uniqueness enforced per tenant via composite index

    name = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    # Categories: "content_generation", "channel_adaptation", "refinement", "seo_analysis"

    # Prompt template content (using Jinja2 syntax)
    prompt_template = Column(Text, nullable=False)
    # Template with {{variable}} placeholders, supports {% if %}, {% for %}, filters

    # Variable definitions (JSONB for flexibility)
    required_variables = Column(JSONB, default=dict)
    # Example: {"title": {"type": "string", "description": "Content title"}}

    optional_variables = Column(JSONB, default=dict)
    # Example: {"tone": {"type": "string", "default": "professional", "options": ["casual", "professional"]}}

    # AI model configuration
    ai_model = Column(String(100))  # "gpt-4-turbo", "gpt-4o-mini", "claude-3-opus"
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer)
    top_p = Column(Float)
    frequency_penalty = Column(Float)
    presence_penalty = Column(Float)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Status flags
    is_active = Column(Boolean, default=True, index=True)
    is_system = Column(Boolean, default=False, index=True)
    # System prompts can't be deleted, only overridden per tenant

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255))
    updated_by = Column(String(255))

    # Performance indexes
    __table_args__ = (
        # Composite unique index: prompt_key must be unique per tenant
        # NULL tenant_id = system prompt, specific tenant_id = tenant override
        Index('idx_ai_prompt_key_tenant', 'prompt_key', 'tenant_id', unique=True),
        Index('idx_ai_prompt_category', 'category', 'is_active'),
        Index('idx_ai_prompt_usage', 'usage_count', 'last_used_at'),
        Index('idx_ai_prompt_system', 'is_system', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert AI prompt to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "prompt_key": self.prompt_key,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "prompt_template": self.prompt_template,
            "required_variables": self.required_variables or {},
            "optional_variables": self.optional_variables or {},
            "ai_model": self.ai_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }

    def __repr__(self) -> str:
        """String representation of AI prompt."""
        tenant_str = f"tenant={self.tenant_id}" if self.tenant_id else "system"
        return (
            f"<AIPrompt(id={self.id}, {tenant_str}, "
            f"key={self.prompt_key}, model={self.ai_model})>"
        )

    @classmethod
    def get_category_icon(cls, category: str) -> str:
        """Get Tabler icon for prompt category."""
        category_icons = {
            "content_generation": "ti-file-text",
            "channel_adaptation": "ti-broadcast",
            "refinement": "ti-pencil",
            "seo_analysis": "ti-chart-line",
            "social_media": "ti-brand-twitter",
            "email": "ti-mail",
            "blog": "ti-article",
        }
        return category_icons.get(category, "ti-message-code")

    @classmethod
    def get_category_color(cls, category: str) -> str:
        """Get Bootstrap color class for category."""
        category_colors = {
            "content_generation": "primary",
            "channel_adaptation": "info",
            "refinement": "warning",
            "seo_analysis": "success",
            "social_media": "cyan",
            "email": "purple",
            "blog": "blue",
        }
        return category_colors.get(category, "secondary")

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100

    def get_all_variables(self) -> List[str]:
        """Get list of all variable names (required + optional)."""
        required = list((self.required_variables or {}).keys())
        optional = list((self.optional_variables or {}).keys())
        return required + optional

    def is_tenant_override(self) -> bool:
        """Check if this is a tenant-specific override of a system prompt."""
        return self.tenant_id is not None and self.is_system is False
