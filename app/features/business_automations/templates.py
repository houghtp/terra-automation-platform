"""
Automation Templates - Business-focused automations with flexible provider choices.

This demonstrates how to present connector flexibility through automation templates
rather than raw connector management.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EmailProvider(str, Enum):
    """Email service providers."""
    GMAIL = "gmail"
    MICROSOFT365 = "microsoft365"
    OUTLOOK = "outlook"


class AIProvider(str, Enum):
    """AI service providers."""
    OPENAI = "openai"
    CLAUDE = "anthropic"
    GEMINI = "gemini"


class MessagingProvider(str, Enum):
    """Team messaging providers."""
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"


class AutomationTemplate(BaseModel):
    """Base automation template configuration."""
    id: str
    name: str
    description: str
    icon: str
    category: str
    required_providers: Dict[str, List[str]]  # provider_type -> list of options
    optional_providers: Dict[str, List[str]] = {}
    configuration_schema: Dict[str, Any]


# Predefined automation templates
AUTOMATION_TEMPLATES = [
    AutomationTemplate(
        id="email_ai_response",
        name="Email + AI Response",
        description="Automatically respond to emails using AI. Choose your email provider and AI model.",
        icon="ti ti-mail-ai",
        category="communication",
        required_providers={
            "email": [EmailProvider.GMAIL, EmailProvider.MICROSOFT365],
            "ai": [AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.GEMINI]
        },
        optional_providers={
            "fallback_ai": [AIProvider.OPENAI, AIProvider.CLAUDE]
        },
        configuration_schema={
            "type": "object",
            "properties": {
                "email_provider": {
                    "type": "string",
                    "title": "Email Provider",
                    "enum": ["gmail", "microsoft365"],
                    "description": "Choose your email service"
                },
                "ai_provider": {
                    "type": "string",
                    "title": "AI Provider",
                    "enum": ["openai", "anthropic", "gemini"],
                    "description": "Choose your AI model provider"
                },
                "response_tone": {
                    "type": "string",
                    "title": "Response Tone",
                    "enum": ["professional", "friendly", "casual"],
                    "default": "professional"
                },
                "auto_send": {
                    "type": "boolean",
                    "title": "Auto-send responses",
                    "description": "Send responses automatically or save as drafts",
                    "default": False
                },
                "response_delay_minutes": {
                    "type": "integer",
                    "title": "Response delay (minutes)",
                    "description": "Wait time before responding",
                    "default": 5,
                    "minimum": 0,
                    "maximum": 60
                }
            },
            "required": ["email_provider", "ai_provider"]
        }
    ),

    AutomationTemplate(
        id="team_notifications",
        name="Smart Team Notifications",
        description="Send intelligent notifications to your team based on events and priorities.",
        icon="ti ti-bell-ringing",
        category="notifications",
        required_providers={
            "messaging": [MessagingProvider.SLACK, MessagingProvider.TEAMS]
        },
        optional_providers={
            "ai": [AIProvider.OPENAI, AIProvider.CLAUDE]  # For smart message formatting
        },
        configuration_schema={
            "type": "object",
            "properties": {
                "messaging_provider": {
                    "type": "string",
                    "title": "Messaging Platform",
                    "enum": ["slack", "teams"],
                    "description": "Choose your team messaging platform"
                },
                "default_channel": {
                    "type": "string",
                    "title": "Default Channel",
                    "description": "Default channel for notifications"
                },
                "priority_levels": {
                    "type": "array",
                    "title": "Priority Levels",
                    "items": {"type": "string"},
                    "default": ["low", "medium", "high", "critical"]
                },
                "smart_formatting": {
                    "type": "boolean",
                    "title": "AI-powered message formatting",
                    "description": "Use AI to format messages for better readability",
                    "default": True
                },
                "ai_provider": {
                    "type": "string",
                    "title": "AI Provider (for formatting)",
                    "enum": ["", "openai", "anthropic"],
                    "description": "Optional: AI for smart message formatting"
                }
            },
            "required": ["messaging_provider", "default_channel"]
        }
    ),

    AutomationTemplate(
        id="content_generation",
        name="Multi-Model Content Generation",
        description="Generate content using multiple AI providers for best results and redundancy.",
        icon="ti ti-article",
        category="content",
        required_providers={
            "primary_ai": [AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.GEMINI]
        },
        optional_providers={
            "fallback_ai": [AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.GEMINI],
            "review_ai": [AIProvider.OPENAI, AIProvider.CLAUDE]
        },
        configuration_schema={
            "type": "object",
            "properties": {
                "primary_ai": {
                    "type": "string",
                    "title": "Primary AI Provider",
                    "enum": ["openai", "anthropic", "gemini"],
                    "description": "Main AI for content generation"
                },
                "fallback_ai": {
                    "type": "string",
                    "title": "Fallback AI Provider",
                    "enum": ["", "openai", "anthropic", "gemini"],
                    "description": "Backup AI if primary fails"
                },
                "review_ai": {
                    "type": "string",
                    "title": "Review AI Provider",
                    "enum": ["", "openai", "anthropic"],
                    "description": "Optional: AI to review and improve content"
                },
                "content_types": {
                    "type": "array",
                    "title": "Content Types",
                    "items": {
                        "type": "string",
                        "enum": ["blog_post", "email", "social_media", "documentation", "marketing_copy"]
                    },
                    "default": ["blog_post", "email"]
                },
                "quality_checks": {
                    "type": "boolean",
                    "title": "Enable quality checks",
                    "description": "Use review AI to check content quality",
                    "default": True
                },
                "auto_publish": {
                    "type": "boolean",
                    "title": "Auto-publish approved content",
                    "default": False
                }
            },
            "required": ["primary_ai"]
        }
    ),

    AutomationTemplate(
        id="data_extraction_analysis",
        name="Web Data + AI Analysis",
        description="Extract data from websites and analyze it with AI for insights.",
        icon="ti ti-world-search",
        category="data",
        required_providers={
            "scraping": ["firecrawl", "selenium"],  # Could add more scrapers
            "ai": [AIProvider.OPENAI, AIProvider.CLAUDE]
        },
        optional_providers={
            "storage": ["google_sheets", "airtable", "notion"]
        },
        configuration_schema={
            "type": "object",
            "properties": {
                "scraping_provider": {
                    "type": "string",
                    "title": "Web Scraping Provider",
                    "enum": ["firecrawl", "selenium"],
                    "description": "Choose your web scraping service"
                },
                "ai_provider": {
                    "type": "string",
                    "title": "AI Analysis Provider",
                    "enum": ["openai", "anthropic"],
                    "description": "AI for data analysis and insights"
                },
                "storage_provider": {
                    "type": "string",
                    "title": "Data Storage",
                    "enum": ["", "google_sheets", "airtable", "notion"],
                    "description": "Where to store extracted data"
                },
                "analysis_frequency": {
                    "type": "string",
                    "title": "Analysis Frequency",
                    "enum": ["realtime", "hourly", "daily", "weekly"],
                    "default": "daily"
                },
                "insights_delivery": {
                    "type": "string",
                    "title": "How to deliver insights",
                    "enum": ["email", "slack", "dashboard"],
                    "default": "dashboard"
                }
            },
            "required": ["scraping_provider", "ai_provider"]
        }
    ),

    AutomationTemplate(
        id="seo_content_generation",
        name="SEO-Optimized Content Generation",
        description="Generate high-quality, SEO-optimized blog content using AI and competitor research.",
        icon="ti ti-article-filled",
        category="content",
        required_providers={
            "primary_ai": [AIProvider.OPENAI, AIProvider.CLAUDE],
            "search": ["serpapi", "scrapingdog", "scrapingbee"],
            "scraping": ["firecrawl", "scrapingbee", "scrapingdog"]
        },
        optional_providers={
            "fallback_ai": [AIProvider.OPENAI, AIProvider.CLAUDE]
        },
        configuration_schema={
            "type": "object",
            "properties": {
                "primary_ai": {
                    "type": "string",
                    "title": "Primary AI Provider",
                    "enum": ["openai", "anthropic"],
                    "description": "Main AI for content generation and analysis"
                },
                "fallback_ai": {
                    "type": "string",
                    "title": "Fallback AI Provider",
                    "enum": ["", "openai", "anthropic"],
                    "description": "Backup AI if primary fails"
                },
                "search_provider": {
                    "type": "string",
                    "title": "Search Provider",
                    "enum": ["serpapi", "scrapingdog", "scrapingbee"],
                    "description": "Service for competitor research",
                    "default": "serpapi"
                },
                "scraping_provider": {
                    "type": "string",
                    "title": "Web Scraping Provider",
                    "enum": ["firecrawl", "scrapingbee", "scrapingdog"],
                    "description": "Service for content extraction",
                    "default": "firecrawl"
                },
                "min_seo_score": {
                    "type": "integer",
                    "title": "Minimum SEO Score",
                    "description": "Minimum SEO score to accept (0-100)",
                    "default": 95,
                    "minimum": 80,
                    "maximum": 100
                },
                "max_iterations": {
                    "type": "integer",
                    "title": "Max Improvement Iterations",
                    "description": "Maximum number of content refinement iterations",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 5
                },
                "auto_approve": {
                    "type": "boolean",
                    "title": "Auto-approve high-scoring content",
                    "description": "Automatically approve content with score >= min_seo_score",
                    "default": False
                }
            },
            "required": ["primary_ai", "search_provider", "scraping_provider"]
        }
    )
]


class AutomationInstance(BaseModel):
    """A configured instance of an automation template."""
    id: str
    template_id: str
    name: str
    description: Optional[str] = None
    provider_configuration: Dict[str, str]  # provider_type -> chosen provider
    automation_configuration: Dict[str, Any]  # template-specific config
    is_active: bool = True
    created_at: str
    updated_at: str


def get_template_by_id(template_id: str) -> Optional[AutomationTemplate]:
    """Get automation template by ID."""
    return next((t for t in AUTOMATION_TEMPLATES if t.id == template_id), None)


def get_templates_by_category(category: str) -> List[AutomationTemplate]:
    """Get automation templates by category."""
    return [t for t in AUTOMATION_TEMPLATES if t.category == category]


def validate_provider_choice(template_id: str, provider_type: str, provider: str) -> bool:
    """Validate that a provider choice is valid for a template."""
    template = get_template_by_id(template_id)
    if not template:
        return False

    # Check required providers
    if provider_type in template.required_providers:
        return provider in template.required_providers[provider_type]

    # Check optional providers
    if provider_type in template.optional_providers:
        return provider in template.optional_providers[provider_type]

    return False


# Example usage
def create_email_ai_automation_instance(
    name: str,
    email_provider: EmailProvider,
    ai_provider: AIProvider,
    config: Dict[str, Any]
) -> AutomationInstance:
    """Create an instance of the email + AI automation."""

    return AutomationInstance(
        id=f"auto_{hash(name + email_provider + ai_provider)}",
        template_id="email_ai_response",
        name=name,
        provider_configuration={
            "email": email_provider.value,
            "ai": ai_provider.value
        },
        automation_configuration=config,
        created_at="2025-09-22T00:00:00Z",
        updated_at="2025-09-22T00:00:00Z"
    )


if __name__ == "__main__":
    # Example: Create an email automation with Gmail + OpenAI
    automation = create_email_ai_automation_instance(
        name="Customer Support AI Responses",
        email_provider=EmailProvider.GMAIL,
        ai_provider=AIProvider.OPENAI,
        config={
            "response_tone": "professional",
            "auto_send": False,
            "response_delay_minutes": 10
        }
    )

    print(f"Created automation: {automation.name}")
    print(f"Providers: {automation.provider_configuration}")
    print(f"Config: {automation.automation_configuration}")
