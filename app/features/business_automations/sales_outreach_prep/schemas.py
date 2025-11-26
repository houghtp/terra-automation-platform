"""
Pydantic schemas for Sales Outreach Prep feature.

Provides validation, serialization, and API contracts for:
- Campaigns
- Companies
- Prospects
- Enrichment logs
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ===== Campaign Schemas =====

class CampaignBase(BaseModel):
    """Base campaign fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    discovery_type: Optional[str] = Field("company_discovery", max_length=50, description="Discovery method: company_discovery, ai_research, manual_import")
    target_industry: Optional[str] = Field(None, max_length=255, description="Target industry")
    target_geography: Optional[str] = Field(None, max_length=255, description="Target geography (e.g., 'Boston, MA')")
    target_roles: Optional[str] = Field(None, description="Target roles (e.g., 'CTO, VP Engineering')")
    target_seniority: Optional[str] = Field(None, max_length=50, description="Target seniority level")
    research_prompt: Optional[str] = Field(None, description="Natural language research goal (for ai_research type)")
    auto_enrich_on_discovery: Optional[bool] = Field(False, description="Automatically enrich prospects with email after discovery")


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign."""
    status: Optional[str] = Field("draft", description="Campaign status")
    assigned_to_user_id: Optional[str] = Field(None, description="User ID assigned to campaign")
    discovery_type: Optional[str] = Field("company_discovery", description="Discovery method")
    auto_enrich_on_discovery: Optional[bool] = Field(False, description="Automatically enrich prospects with email after discovery")

    @field_validator('*', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None for all optional fields."""
        if v == '':
            return None
        return v

    @field_validator('auto_enrich_on_discovery', mode='before')
    @classmethod
    def convert_str_to_bool(cls, v):
        """Convert string 'true'/'false' to boolean."""
        if isinstance(v, str):
            if v.lower() == 'true':
                return True
            elif v.lower() == 'false':
                return False
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is allowed value."""
        allowed = ["draft", "active", "paused", "completed", "archived"]
        if v and v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v

    @field_validator('discovery_type')
    @classmethod
    def validate_discovery_type(cls, v):
        """Validate discovery_type is allowed value."""
        allowed = ["company_discovery", "ai_research", "manual_import"]
        if v and v not in allowed:
            raise ValueError(f"Discovery type must be one of: {', '.join(allowed)}")
        return v


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    discovery_type: Optional[str] = None
    target_industry: Optional[str] = Field(None, max_length=255)
    target_geography: Optional[str] = Field(None, max_length=255)
    target_roles: Optional[str] = None
    target_seniority: Optional[str] = Field(None, max_length=50)
    research_prompt: Optional[str] = None
    status: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    auto_enrich_on_discovery: Optional[bool] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is allowed value."""
        if v is not None:
            allowed = ["draft", "active", "paused", "completed", "archived"]
            if v not in allowed:
                raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v

    @field_validator('discovery_type')
    @classmethod
    def validate_discovery_type(cls, v):
        """Validate discovery_type is allowed value."""
        if v is not None:
            allowed = ["company_discovery", "ai_research", "manual_import"]
            if v not in allowed:
                raise ValueError(f"Discovery type must be one of: {', '.join(allowed)}")
        return v


class CampaignResponse(CampaignBase):
    """Schema for campaign responses."""
    id: str
    tenant_id: str
    discovery_type: str
    status: str
    assigned_to_user_id: Optional[str]
    research_data: Optional[dict] = Field(None, description="AI research results (organizations found, search steps, etc.)")
    auto_enrich_on_discovery: bool
    total_companies: int
    total_prospects: int
    enriched_prospects: int
    qualified_prospects: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]
    created_by_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ===== Company Schemas =====

class CompanyBase(BaseModel):
    """Base company fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    domain: Optional[str] = Field(None, max_length=255, description="Primary domain (e.g., 'acme.com')")
    industry: Optional[str] = Field(None, max_length=255, description="Industry")
    headquarters: Optional[str] = Field(None, max_length=255, description="Headquarters location")
    size: Optional[str] = Field(None, max_length=50, description="Company size")
    description: Optional[str] = Field(None, description="Company description")
    linkedin_url: Optional[str] = Field(None, max_length=500, description="LinkedIn company URL")
    website_url: Optional[str] = Field(None, max_length=500, description="Website URL")


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""
    alternate_domains: Optional[List[str]] = Field(default_factory=list, description="Alternate domains")


class CompanyUpdate(BaseModel):
    """Schema for updating a company (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    alternate_domains: Optional[List[str]] = None
    industry: Optional[str] = Field(None, max_length=255)
    headquarters: Optional[str] = Field(None, max_length=255)
    size: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    linkedin_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)
    market_size: Optional[str] = Field(None, max_length=50)
    product_breadth: Optional[str] = Field(None, max_length=50)
    innovation_score: Optional[int] = Field(None, ge=1, le=10)
    completeness_of_vision: Optional[int] = Field(None, ge=1, le=10)
    ability_to_execute: Optional[int] = Field(None, ge=1, le=10)


class CompanyResponse(CompanyBase):
    """Schema for company responses."""
    id: str
    tenant_id: str
    alternate_domains: List[str]
    logo_url: Optional[str]
    market_size: Optional[str]
    product_breadth: Optional[str]
    innovation_score: Optional[int]
    completeness_of_vision: Optional[int]
    ability_to_execute: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===== CampaignCompany Schemas =====

class CampaignCompanyCreate(BaseModel):
    """Schema for adding a company to a campaign."""
    company_id: str = Field(..., description="Company ID to add to campaign")


class CampaignCompanyResponse(BaseModel):
    """Schema for campaign-company relationship."""
    id: str
    campaign_id: str
    company_id: str
    research_status: str
    research_completed_at: Optional[datetime]
    market_position: Optional[dict]
    competitors: Optional[List[str]]
    ai_insights: Optional[List[str]]
    executive_summary: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ===== Prospect Schemas =====

class ProspectBase(BaseModel):
    """Base prospect fields."""
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title")
    location: Optional[str] = Field(None, max_length=255, description="Location")
    linkedin_url: Optional[str] = Field(None, max_length=500, description="LinkedIn profile URL")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    notes: Optional[str] = Field(None, description="User notes")


class ProspectCreate(ProspectBase):
    """Schema for creating a prospect."""
    company_id: Optional[str] = Field(None, description="Company ID")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags")


class ProspectUpdate(BaseModel):
    """Schema for updating a prospect (all fields optional)."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=255)
    seniority_level: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    company_id: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is allowed value."""
        if v is not None:
            allowed = ["new", "enriched", "qualified", "contacted", "unqualified", "bounced"]
            if v not in allowed:
                raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v

    @field_validator('seniority_level')
    @classmethod
    def validate_seniority(cls, v):
        """Validate seniority level is allowed value."""
        if v is not None:
            allowed = ["c-level", "vp", "director", "manager", "individual_contributor"]
            if v not in allowed:
                raise ValueError(f"Seniority must be one of: {', '.join(allowed)}")
        return v


class ProspectResponse(ProspectBase):
    """Schema for prospect responses."""
    id: str
    tenant_id: str
    campaign_id: str
    company_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    seniority_level: Optional[str]
    region: Optional[str]
    email_confidence: Optional[float]
    email_status: Optional[str]
    linkedin_snippet: Optional[str]
    enrichment_status: str
    enriched_at: Optional[datetime]
    enrichment_source: Optional[str]
    status: str
    tags: List[str]
    discovered_via: Optional[str]
    discovery_query: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===== Enrichment Log Schemas =====

class EnrichmentLogResponse(BaseModel):
    """Schema for enrichment log responses."""
    id: str
    prospect_id: str
    enrichment_type: str
    provider: str
    status: str
    confidence_score: Optional[float]
    attempted_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int

    model_config = ConfigDict(from_attributes=True)


# ===== Search & Filter Schemas =====

class ProspectSearchFilter(BaseModel):
    """Filters for prospect search."""
    search: Optional[str] = Field(None, description="Search term for name, title, company")
    status: Optional[str] = Field(None, description="Prospect status filter")
    enrichment_status: Optional[str] = Field(None, description="Enrichment status filter")
    seniority_level: Optional[str] = Field(None, description="Seniority level filter")
    tags: Optional[List[str]] = Field(None, description="Tags filter (any match)")
    company_id: Optional[str] = Field(None, description="Filter by company")


class CampaignSearchFilter(BaseModel):
    """Filters for campaign search."""
    search: Optional[str] = Field(None, description="Search term for name, description")
    status: Optional[str] = Field(None, description="Campaign status filter")
    assigned_to_user_id: Optional[str] = Field(None, description="Filter by assigned user")


# ===== Batch Operation Schemas =====

class BatchEnrichRequest(BaseModel):
    """Request to enrich multiple prospects."""
    prospect_ids: List[str] = Field(..., description="List of prospect IDs to enrich")
    enrichment_type: str = Field("email", description="Type of enrichment (email, phone, etc.)")

    @field_validator('enrichment_type')
    @classmethod
    def validate_enrichment_type(cls, v):
        """Validate enrichment type."""
        allowed = ["email", "phone", "linkedin"]
        if v not in allowed:
            raise ValueError(f"Enrichment type must be one of: {', '.join(allowed)}")
        return v


class ProspectDiscoveryRequest(BaseModel):
    """Request to discover prospects for a campaign."""
    campaign_id: str = Field(..., description="Campaign ID")
    company_ids: Optional[List[str]] = Field(None, description="Specific companies to search (if None, search all)")
    max_results_per_company: int = Field(20, ge=1, le=100, description="Max results per company")


# ===== Statistics Schemas =====

class CampaignStats(BaseModel):
    """Campaign statistics."""
    total_campaigns: int
    active_campaigns: int
    total_prospects: int
    enriched_prospects: int
    enrichment_rate: float  # Percentage


class EnrichmentStats(BaseModel):
    """Enrichment statistics."""
    total_attempts: int
    successful: int
    failed: int
    rate_limited: int
    success_rate: float  # Percentage
    average_confidence: Optional[float]
