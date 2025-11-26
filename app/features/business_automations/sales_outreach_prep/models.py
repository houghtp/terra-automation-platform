"""
Database models for Sales Outreach Prep feature.

Follows platform best practices:
- All models inherit from Base and AuditMixin
- All models have tenant_id for multi-tenancy
- Uses timezone-naive datetimes (PostgreSQL TIMESTAMP WITHOUT TIME ZONE)
- Structured logging via get_logger
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, Text, JSON, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class Campaign(Base, AuditMixin):
    """
    Sales outreach campaign to organize prospect research.

    A campaign represents a coordinated effort to find and enrich
    prospects in a specific market, industry, or geography.
    """

    __tablename__ = "sales_campaigns"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Tenant isolation (REQUIRED)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Discovery type - determines how prospects are found
    discovery_type = Column(String(50), default="company_discovery", nullable=False)
    # Values: company_discovery (search by industry/location),
    #         ai_research (AI-powered multi-step research),
    #         manual_import (import from CSV/list)

    # Target criteria (for company_discovery type)
    target_industry = Column(String(255), nullable=True)
    target_geography = Column(String(255), nullable=True)  # e.g., "Boston, MA"
    target_roles = Column(Text, nullable=True)  # e.g., "CTO, VP Engineering"
    target_seniority = Column(String(50), nullable=True)  # e.g., "C-level", "VP"

    # AI research (for ai_research type)
    research_prompt = Column(Text, nullable=True)
    # Natural language research goal: "Find organizers of large corporate events in UK..."

    research_data = Column(JSON, nullable=True)
    # Stores AI research results, including:
    # - Research plan and steps executed
    # - Organizations found
    # - Venues/events/associations researched
    # - AI reasoning and confidence scores

    # Metadata
    status = Column(String(50), default="draft", nullable=False)
    # Status values: draft, active, paused, completed, archived
    assigned_to_user_id = Column(String(36), nullable=True)

    # Enrichment settings
    auto_enrich_on_discovery = Column(Boolean, default=False, nullable=False)
    # If True, automatically trigger email enrichment after prospect discovery

    # Denormalized stats (updated by service layer)
    total_companies = Column(Integer, default=0, nullable=False)
    total_prospects = Column(Integer, default=0, nullable=False)
    enriched_prospects = Column(Integer, default=0, nullable=False)
    qualified_prospects = Column(Integer, default=0, nullable=False)

    # Timestamps (from AuditMixin: created_at, updated_at, created_by, etc.)

    # Relationships
    companies = relationship("CampaignCompany", back_populates="campaign", cascade="all, delete-orphan")
    prospects = relationship("Prospect", back_populates="campaign", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_campaigns_tenant_status', 'tenant_id', 'status'),
        Index('idx_campaigns_assigned_user', 'assigned_to_user_id'),
    )

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "discovery_type": self.discovery_type,
            "target_industry": self.target_industry,
            "target_geography": self.target_geography,
            "target_roles": self.target_roles,
            "target_seniority": self.target_seniority,
            "research_prompt": self.research_prompt,
            "research_data": self.research_data,
            "status": self.status,
            "assigned_to_user_id": self.assigned_to_user_id,
            "auto_enrich_on_discovery": self.auto_enrich_on_discovery,
            "total_companies": self.total_companies,
            "total_prospects": self.total_prospects,
            "enriched_prospects": self.enriched_prospects,
            "qualified_prospects": self.qualified_prospects,
        }
        # Add audit fields from AuditMixin
        base_dict.update(self.get_audit_info())
        return base_dict


class Company(Base, AuditMixin):
    """
    Company/organization being targeted for outreach.

    Stores company details, domains for email enrichment,
    and cached market intelligence data.
    """

    __tablename__ = "sales_companies"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Tenant isolation (REQUIRED)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)  # Primary domain (e.g., "acme.com")
    alternate_domains = Column(JSON, default=list)  # Additional domains as list

    # Company details
    industry = Column(String(255), nullable=True)
    headquarters = Column(String(255), nullable=True)
    size = Column(String(50), nullable=True)  # "1-10", "11-50", "51-200", etc.
    description = Column(Text, nullable=True)

    # External references
    logo_url = Column(String(500), nullable=True)  # Clearbit logo URL
    linkedin_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)

    # Market intelligence (cached from AI analysis)
    market_size = Column(String(50), nullable=True)  # Low, Medium, High
    product_breadth = Column(String(50), nullable=True)  # Niche, Moderate, Broad
    innovation_score = Column(Integer, nullable=True)  # 1-10
    completeness_of_vision = Column(Integer, nullable=True)  # 1-10 (for quadrant chart)
    ability_to_execute = Column(Integer, nullable=True)  # 1-10 (for quadrant chart)

    # Relationships
    campaign_links = relationship("CampaignCompany", back_populates="company")
    prospects = relationship("Prospect", back_populates="company")

    # Indexes
    __table_args__ = (
        Index('idx_companies_tenant_name', 'tenant_id', 'name'),
        Index('idx_companies_domain', 'domain'),
    )

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "domain": self.domain,
            "alternate_domains": self.alternate_domains or [],
            "industry": self.industry,
            "headquarters": self.headquarters,
            "size": self.size,
            "description": self.description,
            "logo_url": self.logo_url,
            "linkedin_url": self.linkedin_url,
            "website_url": self.website_url,
            "market_size": self.market_size,
            "product_breadth": self.product_breadth,
            "innovation_score": self.innovation_score,
            "completeness_of_vision": self.completeness_of_vision,
            "ability_to_execute": self.ability_to_execute,
        }
        base_dict.update(self.get_audit_info())
        return base_dict


class CampaignCompany(Base, AuditMixin):
    """
    Many-to-many relationship linking campaigns to companies.

    Stores campaign-specific company data like research status
    and cached competitive analysis results.
    """

    __tablename__ = "campaign_companies"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Tenant isolation (REQUIRED)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Foreign keys
    campaign_id = Column(String(36), ForeignKey("sales_campaigns.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(String(36), ForeignKey("sales_companies.id", ondelete="CASCADE"), nullable=False)

    # Research status
    research_status = Column(String(50), default="pending", nullable=False)
    # Status values: pending, in_progress, completed, failed
    research_completed_at = Column(DateTime, nullable=True)

    # AI-generated insights (cached for this campaign)
    market_position = Column(JSON, nullable=True)
    # Example: {"vision": 7, "execution": 8, "innovation": 6}

    competitors = Column(JSON, nullable=True)
    # Example: ["company-id-1", "company-id-2", ...]

    ai_insights = Column(JSON, nullable=True)
    # Example: ["Insight 1", "Insight 2", ...]

    executive_summary = Column(Text, nullable=True)
    # AI-generated narrative summary

    # Relationships
    campaign = relationship("Campaign", back_populates="companies")
    company = relationship("Company", back_populates="campaign_links")

    # Indexes
    __table_args__ = (
        Index('idx_campaign_companies_campaign', 'campaign_id'),
        Index('idx_campaign_companies_company', 'company_id'),
        Index('idx_campaign_companies_unique', 'campaign_id', 'company_id', unique=True),
    )

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "company_id": self.company_id,
            "research_status": self.research_status,
            "research_completed_at": self.research_completed_at.isoformat() if self.research_completed_at else None,
            "market_position": self.market_position,
            "competitors": self.competitors or [],
            "ai_insights": self.ai_insights or [],
            "executive_summary": self.executive_summary,
        }
        base_dict.update(self.get_audit_info())
        return base_dict


class Prospect(Base, AuditMixin):
    """
    Individual contact/prospect discovered during campaign.

    Stores contact information, enrichment status, and prospect
    qualification data.
    """

    __tablename__ = "sales_prospects"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Tenant isolation (REQUIRED)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Foreign keys
    campaign_id = Column(String(36), ForeignKey("sales_campaigns.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(String(36), ForeignKey("sales_companies.id", ondelete="SET NULL"), nullable=True)

    # Contact information
    full_name = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    job_title = Column(String(255), nullable=True)
    seniority_level = Column(String(50), nullable=True)
    # Values: c-level, vp, director, manager, individual_contributor

    # Location
    location = Column(String(255), nullable=True)  # e.g., "Boston, MA"
    region = Column(String(100), nullable=True)  # e.g., "Northeast", "EMEA"

    # Contact details (enriched)
    email = Column(String(255), nullable=True)
    email_confidence = Column(Float, nullable=True)  # Hunter.io confidence (0-100)
    email_status = Column(String(50), nullable=True)
    # Values: valid, invalid, risky, unknown, accept_all

    phone = Column(String(50), nullable=True)

    # LinkedIn data
    linkedin_url = Column(String(500), nullable=True)
    linkedin_snippet = Column(Text, nullable=True)  # Bio/summary from search result

    # Enrichment tracking
    enrichment_status = Column(String(50), default="not_started", nullable=False)
    # Values: not_started, in_progress, enriched, failed, verified

    enriched_at = Column(DateTime, nullable=True)
    enrichment_source = Column(String(100), nullable=True)  # hunter.io, clearbit, manual

    # Prospect management
    status = Column(String(50), default="new", nullable=False)
    # Values: new, enriched, qualified, contacted, unqualified, bounced

    tags = Column(JSON, default=list)
    # Example: ["decision_maker", "hot_lead", "gatekeeper"]

    notes = Column(Text, nullable=True)  # User notes

    # Discovery metadata
    discovered_via = Column(String(100), nullable=True)  # firecrawl, manual, csv_import
    discovery_query = Column(String(500), nullable=True)  # Search query used

    # Relationships
    campaign = relationship("Campaign", back_populates="prospects")
    company = relationship("Company", back_populates="prospects")
    enrichment_logs = relationship("EnrichmentLog", back_populates="prospect", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_prospects_campaign', 'campaign_id'),
        Index('idx_prospects_company', 'company_id'),
        Index('idx_prospects_email', 'email'),
        Index('idx_prospects_status', 'status', 'enrichment_status'),
        Index('idx_prospects_tenant_campaign', 'tenant_id', 'campaign_id'),
    )

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "company_id": self.company_id,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "job_title": self.job_title,
            "seniority_level": self.seniority_level,
            "location": self.location,
            "region": self.region,
            "email": self.email,
            "email_confidence": self.email_confidence,
            "email_status": self.email_status,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "linkedin_snippet": self.linkedin_snippet,
            "enrichment_status": self.enrichment_status,
            "enriched_at": self.enriched_at.isoformat() if self.enriched_at else None,
            "enrichment_source": self.enrichment_source,
            "status": self.status,
            "tags": self.tags or [],
            "notes": self.notes,
            "discovered_via": self.discovered_via,
            "discovery_query": self.discovery_query,
        }
        base_dict.update(self.get_audit_info())
        return base_dict


class EnrichmentLog(Base):
    """
    Audit log of enrichment attempts for prospects.

    Tracks API calls to enrichment providers (Hunter.io, etc.)
    for debugging, cost tracking, and data quality analysis.

    Note: Does NOT inherit from AuditMixin since it's a log table.
    """

    __tablename__ = "enrichment_logs"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Tenant isolation (REQUIRED)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Foreign key
    prospect_id = Column(String(36), ForeignKey("sales_prospects.id", ondelete="CASCADE"), nullable=False)

    # Enrichment details
    enrichment_type = Column(String(50), nullable=False)  # email, phone, linkedin
    provider = Column(String(100), nullable=False)  # hunter.io, clearbit, manual

    # Results
    status = Column(String(50), nullable=False)  # success, failed, rate_limited, invalid
    result_data = Column(JSON, nullable=True)  # Raw API response (for debugging)
    confidence_score = Column(Float, nullable=True)

    # Timing
    attempted_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Relationship
    prospect = relationship("Prospect", back_populates="enrichment_logs")

    # Indexes
    __table_args__ = (
        Index('idx_enrichment_logs_prospect', 'prospect_id'),
        Index('idx_enrichment_logs_status', 'status'),
        Index('idx_enrichment_logs_attempted', 'attempted_at'),
    )

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "prospect_id": self.prospect_id,
            "enrichment_type": self.enrichment_type,
            "provider": self.provider,
            "status": self.status,
            "result_data": self.result_data,
            "confidence_score": self.confidence_score,
            "attempted_at": self.attempted_at.isoformat() if self.attempted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }
