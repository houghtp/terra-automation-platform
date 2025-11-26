# Sales Outreach Prep - Product Requirements Document (PRD)

**Version**: 1.0
**Date**: 2025-11-23
**Status**: Draft - Awaiting Approval

---

## Executive Summary

Transform the existing `market_mapper.py` script into a full-featured web application that helps sales teams identify, research, and prepare outreach to key decision-makers in target companies and industries.

**Core Value Proposition**: Automate the manual process of finding contacts, enriching their data, and preparing personalized outreach campaigns.

---

## Table of Contents

1. [Background & Problem Statement](#1-background--problem-statement)
2. [Goals & Objectives](#2-goals--objectives)
3. [User Personas](#3-user-personas)
4. [Feature Requirements](#4-feature-requirements)
5. [User Workflows](#5-user-workflows)
6. [Technical Architecture](#6-technical-architecture)
7. [Data Models](#7-data-models)
8. [API Integrations](#8-api-integrations)
9. [UI/UX Design](#9-uiux-design)
10. [Success Metrics](#10-success-metrics)
11. [Implementation Phases](#11-implementation-phases)
12. [Open Questions](#12-open-questions)

---

## 1. Background & Problem Statement

### Current Situation
- Sales teams manually search LinkedIn, company websites, and other sources to find decision-makers
- Contact information (emails, phone numbers) requires multiple tools and manual effort
- No centralized system to track prospect research and outreach preparation
- Market intelligence gathering is ad-hoc and inconsistent

### Existing Asset
The `market_mapper.py` script provides:
- ✅ OpenAI-powered competitive analysis
- ✅ Firecrawl integration for LinkedIn profile discovery
- ✅ Hunter.io integration for email enrichment
- ✅ Gartner-style market quadrant visualization
- ✅ Excel report generation

### The Problem
Converting this one-off script into a scalable, multi-user web application that can:
- Store and manage prospect data over time
- Run searches asynchronously (background jobs)
- Support multiple campaigns and territories
- Provide CRUD interfaces for managing prospects
- Track enrichment status and data quality

---

## 2. Goals & Objectives

### Primary Goals
1. **Automate Prospect Discovery**: Find decision-makers in target companies/industries using AI-powered web search
2. **Enrich Contact Data**: Automatically find email addresses, phone numbers, and other contact details
3. **Organize Campaigns**: Group prospects into outreach campaigns with context and notes
4. **Track Data Quality**: Know which contacts have been enriched, verified, or need manual review

### Secondary Goals
1. Market intelligence dashboard (competitive landscape)
2. Integration with CRM systems (future)
3. Automated outreach sequencing (future)
4. Team collaboration features (shared campaigns, notes)

### Success Criteria
- ✅ Users can create a campaign and find 50+ prospects in under 10 minutes
- ✅ 70%+ of prospects have enriched email addresses
- ✅ Zero manual Excel exports needed
- ✅ All data persisted and searchable

---

## 3. User Personas

### Primary: Sales Development Representative (SDR)
- **Needs**: Quick access to decision-maker contacts in target accounts
- **Pain Points**: Spending hours on manual research, low email accuracy
- **Tech Savvy**: Medium (familiar with CRMs, LinkedIn Sales Navigator)

### Secondary: Sales Manager
- **Needs**: Oversight of team campaigns, data quality metrics
- **Pain Points**: Inconsistent prospecting quality across team
- **Tech Savvy**: Medium-High

### Tertiary: Marketing Operations
- **Needs**: Market intelligence, competitive analysis data
- **Pain Points**: No structured way to track market landscape changes
- **Tech Savvy**: High

---

## 4. Feature Requirements

### 4.1 Campaign Management (MUST HAVE - Phase 1)

**Description**: Organize prospect research into logical campaigns (e.g., "Boston Healthcare CIOs Q1 2025")

**Features**:
- ✅ Create/Edit/Delete campaigns
- ✅ Campaign metadata:
  - Name, description
  - Target industry/vertical
  - Target geography/region
  - Target roles (e.g., "CTO, VP Engineering, Head of IT")
  - Status (Draft, Active, Paused, Completed)
  - Created by, assigned to
  - Date range
- ✅ Campaign dashboard showing:
  - Total prospects found
  - Enrichment completion %
  - Last activity date
- ✅ Bulk actions: Clone campaign, archive, export

**User Stories**:
- As an SDR, I want to create a campaign called "Boston SaaS CTOs" so I can organize my Q1 prospecting efforts
- As a Sales Manager, I want to see all active campaigns across my team so I can track coverage

---

### 4.2 Company Research (MUST HAVE - Phase 1)

**Description**: Research target companies and their competitive landscape

**Features**:
- ✅ Add companies to a campaign (manual entry or import CSV)
- ✅ For each company, automatically generate:
  - Competitive analysis (using OpenAI)
  - Market positioning quadrant chart
  - List of 5-10 competitors
  - Executive summary of market landscape
  - AI-generated insights
- ✅ View company profile:
  - Basic info (name, industry, size, headquarters)
  - Discovered competitors
  - Market quadrant position
  - AI insights
- ✅ Search for company domains (auto-detect via OpenAI)
- ✅ Company logo integration (Clearbit API)

**User Stories**:
- As an SDR, I want to add "Acme Corp" to my campaign and see who their competitors are
- As a Sales Manager, I want to understand where our target companies sit in the market landscape

**Data Sources**:
- OpenAI GPT-4 (competitive analysis)
- Clearbit Logo API (company logos)
- User input (manual company details)

---

### 4.3 Prospect Discovery (MUST HAVE - Phase 1)

**Description**: Find decision-makers at target companies using web search

**Features**:
- ✅ Search for executives by:
  - Company name
  - Geographic region (e.g., "Boston", "New York", "United States")
  - Role/title keywords (e.g., "CTO OR VP Engineering OR Head of IT")
  - Seniority level (C-level, VP, Director, Manager)
- ✅ Search LinkedIn profiles via Firecrawl
- ✅ Extract from search results:
  - Full name
  - Job title
  - Current company
  - Location/region
  - LinkedIn profile URL
  - Profile snippet/bio
- ✅ Background job processing:
  - Queue search jobs (Celery)
  - Progress tracking
  - Results displayed as they're found
- ✅ De-duplication logic (same person across multiple searches)
- ✅ Filtering & sorting:
  - Filter by enrichment status
  - Filter by role/seniority
  - Sort by name, title, date added

**User Stories**:
- As an SDR, I want to search for "CTOs in Boston at healthcare companies" and see results appear in real-time
- As an SDR, I want to avoid duplicate prospects when running multiple searches

**Data Sources**:
- Firecrawl API (LinkedIn search)
- OpenAI (role/title classification, data extraction)

---

### 4.4 Contact Enrichment (MUST HAVE - Phase 1)

**Description**: Automatically find email addresses and other contact details for prospects

**Features**:
- ✅ Email discovery:
  - Use Hunter.io API to find work email
  - Try multiple domain variations (company.com, company.co.uk, etc.)
  - Confidence score (Hunter.io provides this)
  - Verification status (deliverable, risky, unknown)
- ✅ Enrichment queue:
  - Batch processing (avoid API rate limits)
  - Retry logic for failed enrichments
  - Manual "re-enrich" button
- ✅ Enrichment status tracking:
  - Not Started
  - In Progress
  - Enriched (email found)
  - Failed (no email found)
  - Verified (email verified as deliverable)
- ✅ Display enriched data:
  - Email address
  - Confidence score
  - Last enriched date
  - Enrichment source (Hunter.io, manual entry, etc.)

**User Stories**:
- As an SDR, I want to enrich 100 prospects and see which ones have verified emails
- As a Sales Manager, I want to know what % of our prospects have valid contact info

**Data Sources**:
- Hunter.io API (email finding & verification)
- Clearbit Enrichment API (optional - future phase)
- ZoomInfo API (optional - future phase)

---

### 4.5 Prospect Management (MUST HAVE - Phase 1)

**Description**: CRUD interface for managing individual prospects

**Features**:
- ✅ Prospect list (Tabulator table):
  - Columns: Name, Title, Company, Location, Email, Status, Actions
  - Inline editing (edit email, notes)
  - Bulk selection & actions
  - Export to CSV
  - Quick search & filters
- ✅ Prospect detail view/modal:
  - Contact info (name, title, email, phone)
  - Company details
  - LinkedIn profile link
  - Notes field (user can add context)
  - Enrichment history log
  - Tags (e.g., "hot lead", "gatekeeper", "decision maker")
- ✅ Manual prospect creation:
  - Add prospect directly without search
  - Upload CSV of contacts
- ✅ Prospect statuses:
  - New (just discovered)
  - Enriched (contact info added)
  - Qualified (SDR reviewed and approved)
  - Contacted (outreach initiated)
  - Unqualified (not a good fit)

**User Stories**:
- As an SDR, I want to edit a prospect's email if I find a better one manually
- As an SDR, I want to add notes to a prospect like "Met at conference, ask about their Q1 budget"
- As a Sales Manager, I want to export all qualified prospects to CSV for import into our CRM

---

### 4.6 Market Intelligence Dashboard (SHOULD HAVE - Phase 2)

**Description**: Visualize competitive landscape and market trends

**Features**:
- ✅ Gartner-style quadrant chart:
  - X-axis: Completeness of Vision
  - Y-axis: Ability to Execute
  - Bubble size: Market share estimate
  - Interactive (click to see company details)
- ✅ Competitor comparison table:
  - Compare 5-10 competitors side-by-side
  - Metrics: Innovation score, product breadth, market size
- ✅ AI-generated insights:
  - Display key insights from OpenAI analysis
  - Highlight outliers, disruptors, strategic risks
- ✅ Executive summary:
  - Auto-generated narrative (150 words)
  - Editable by user

**User Stories**:
- As a Sales Manager, I want to show my VP of Sales where our target accounts sit in the market
- As Marketing Ops, I want to understand our competitive positioning to inform messaging

---

### 4.7 Integration with Other Tools (COULD HAVE - Phase 3)

**Ideas for future consideration**:
- Salesforce/HubSpot CRM sync
- Slack notifications when new prospects are enriched
- Email sequencing (automated follow-ups)
- Calendar integration (schedule outreach)
- LinkedIn Sales Navigator integration

---

## 5. User Workflows

### Workflow 1: Create Campaign & Find Prospects

1. User clicks "New Campaign"
2. Fills out campaign form:
   - Name: "Boston Healthcare CTOs Q1 2025"
   - Industry: "Healthcare"
   - Region: "Boston, MA"
   - Target Roles: "CTO, VP Engineering, Chief Technology Officer"
3. Saves campaign
4. From campaign detail page, clicks "Add Companies"
5. Enters company names or uploads CSV
6. System runs background job to:
   - Research each company (competitive analysis)
   - Generate market quadrant chart
7. User clicks "Find Prospects"
8. System runs Firecrawl search for each company
9. Results appear in real-time as they're found
10. User reviews prospects, clicks "Enrich All"
11. System queues email enrichment jobs (Hunter.io)
12. User sees enrichment progress bar
13. When complete, user filters to "Enriched" prospects
14. Reviews, qualifies, and exports to CSV for CRM import

**Time to Complete**: ~10 minutes for 50 prospects

---

### Workflow 2: Manual Prospect Entry

1. User is in a campaign
2. Clicks "Add Prospect Manually"
3. Fills out form:
   - Name, Title, Company, LinkedIn URL
4. Saves prospect
5. System auto-enriches email (background job)
6. User gets notification when enrichment completes

---

### Workflow 3: Review & Qualify Prospects

1. User opens campaign
2. Views prospect table
3. Filters to "Enriched" status
4. Reviews each prospect:
   - Clicks to see LinkedIn profile
   - Checks company website
   - Adds notes
   - Changes status to "Qualified" or "Unqualified"
5. Exports qualified prospects to CSV
6. Imports CSV into CRM (Salesforce, HubSpot, etc.)

---

## 6. Technical Architecture

### 6.1 Technology Stack

**Backend**:
- FastAPI (existing platform)
- PostgreSQL (database)
- SQLAlchemy 2.0 (ORM)
- Celery + Redis (background jobs)
- Pydantic (validation)

**Frontend**:
- Jinja2 templates (server-side rendering)
- HTMX (dynamic interactions)
- Tabulator (data tables)
- Plotly (charts/visualizations)
- Tabler UI (existing design system)

**Integrations**:
- OpenAI API (GPT-4 for analysis)
- Firecrawl API (LinkedIn search)
- Hunter.io API (email finding)
- Clearbit Logo API (company logos)

---

### 6.2 Service Architecture

```
sales_outreach_prep/
├── models.py                 # SQLAlchemy models
├── schemas.py                # Pydantic schemas
├── dependencies.py           # Dependency injection
├── routes/
│   ├── __init__.py
│   ├── campaigns/
│   │   ├── __init__.py
│   │   ├── crud_routes.py   # Campaign CRUD API
│   │   └── form_routes.py   # Campaign forms (HTMX)
│   ├── companies/
│   │   ├── __init__.py
│   │   ├── crud_routes.py   # Company CRUD API
│   │   └── form_routes.py   # Company forms
│   ├── prospects/
│   │   ├── __init__.py
│   │   ├── crud_routes.py   # Prospect CRUD API
│   │   └── form_routes.py   # Prospect forms
│   └── pages_routes.py      # Dashboard pages
├── services/
│   ├── __init__.py
│   ├── campaigns/
│   │   └── crud_services.py
│   ├── companies/
│   │   ├── crud_services.py
│   │   └── research_services.py  # AI-powered company research
│   ├── prospects/
│   │   ├── crud_services.py
│   │   ├── discovery_services.py  # Firecrawl search
│   │   └── enrichment_services.py # Hunter.io enrichment
│   └── market_intelligence/
│       └── analysis_services.py   # Market quadrant generation
├── tasks/
│   ├── __init__.py
│   ├── company_research_tasks.py  # Celery tasks
│   ├── prospect_discovery_tasks.py
│   └── enrichment_tasks.py
├── templates/
│   ├── campaigns/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── partials/
│   │       └── form.html
│   ├── companies/
│   ├── prospects/
│   └── dashboard/
│       ├── market_intelligence.html
│       └── campaign_overview.html
├── static/
│   ├── js/
│   │   ├── campaigns-table.js
│   │   ├── prospects-table.js
│   │   └── market-quadrant.js
│   └── css/
├── utils/
│   ├── firecrawl_client.py    # Firecrawl API wrapper
│   ├── hunter_client.py       # Hunter.io API wrapper
│   ├── openai_client.py       # OpenAI API wrapper
│   └── data_parsers.py        # LinkedIn data extraction
└── docs/
    ├── PRD.md                  # This document
    ├── API.md                  # API documentation
    └── INTEGRATION_GUIDE.md    # Third-party API setup
```

---

### 6.3 Background Job Processing

**Use Cases**:
1. Company competitive analysis (OpenAI - 10-30 seconds per company)
2. Prospect discovery (Firecrawl search - 5-15 seconds per search)
3. Email enrichment (Hunter.io - 1-2 seconds per prospect, but rate limited)
4. Market quadrant chart generation (Plotly - 2-5 seconds)

**Celery Task Design**:
```python
# tasks/company_research_tasks.py
@celery_app.task(bind=True)
def research_company_task(self, company_id: str, tenant_id: str):
    """Background task to research a company using OpenAI."""
    service = CompanyResearchService(db_session, tenant_id)
    result = await service.analyze_competitive_landscape(company_id)
    return result

# tasks/prospect_discovery_tasks.py
@celery_app.task(bind=True, max_retries=3)
def discover_prospects_task(self, campaign_id: str, company_id: str, tenant_id: str):
    """Search for prospects using Firecrawl."""
    service = ProspectDiscoveryService(db_session, tenant_id)
    prospects = await service.search_linkedin_profiles(
        company_id=company_id,
        campaign_id=campaign_id
    )
    return {"found": len(prospects), "company_id": company_id}

# tasks/enrichment_tasks.py
@celery_app.task(bind=True, rate_limit='10/m')  # Hunter.io free tier: 50/month
def enrich_prospect_email_task(self, prospect_id: str, tenant_id: str):
    """Find email address for a prospect using Hunter.io."""
    service = EnrichmentService(db_session, tenant_id)
    result = await service.find_email(prospect_id)
    return result
```

**Task Monitoring**:
- Use Celery Flower for real-time task monitoring
- Display task progress in UI (via WebSocket or polling)
- Retry logic for failed tasks
- Rate limiting to respect API quotas

---

## 7. Data Models

### 7.1 Campaign

**Purpose**: Organize prospect research efforts into logical groupings

```python
class Campaign(Base, AuditMixin):
    __tablename__ = "sales_campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Target criteria
    target_industry = Column(String(255), nullable=True)
    target_geography = Column(String(255), nullable=True)  # e.g., "Boston, MA"
    target_roles = Column(Text, nullable=True)  # e.g., "CTO, VP Engineering"
    target_seniority = Column(String(50), nullable=True)  # e.g., "C-level", "VP", "Director"

    # Metadata
    status = Column(String(50), default="draft")  # draft, active, paused, completed
    assigned_to_user_id = Column(String(36), nullable=True)

    # Stats (denormalized for performance)
    total_companies = Column(Integer, default=0)
    total_prospects = Column(Integer, default=0)
    enriched_prospects = Column(Integer, default=0)
    qualified_prospects = Column(Integer, default=0)

    # Relationships
    companies = relationship("CampaignCompany", back_populates="campaign")
    prospects = relationship("Prospect", back_populates="campaign")
```

---

### 7.2 CampaignCompany

**Purpose**: Link companies to campaigns (many-to-many)

```python
class CampaignCompany(Base, AuditMixin):
    __tablename__ = "campaign_companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    campaign_id = Column(String(36), ForeignKey("sales_campaigns.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)

    # Research status
    research_status = Column(String(50), default="pending")  # pending, completed, failed
    research_completed_at = Column(DateTime, nullable=True)

    # AI-generated insights (cached)
    market_position = Column(JSON, nullable=True)  # {vision: 7, execution: 8, ...}
    competitors = Column(JSON, nullable=True)  # List of competitor IDs
    ai_insights = Column(JSON, nullable=True)  # List of insight strings
    executive_summary = Column(Text, nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="companies")
    company = relationship("Company")
```

---

### 7.3 Company

**Purpose**: Store information about companies being researched

```python
class Company(Base, AuditMixin):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)  # Primary domain (e.g., "acme.com")
    alternate_domains = Column(JSON, default=list)  # Additional domains

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

    # Indexes
    __table_args__ = (
        Index('idx_companies_name_tenant', 'name', 'tenant_id'),
        Index('idx_companies_domain', 'domain'),
    )
```

---

### 7.4 Prospect

**Purpose**: Store information about individual contacts/prospects

```python
class Prospect(Base, AuditMixin):
    __tablename__ = "prospects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    campaign_id = Column(String(36), ForeignKey("sales_campaigns.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)

    # Contact information
    full_name = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)  # Parsed
    last_name = Column(String(100), nullable=True)   # Parsed

    job_title = Column(String(255), nullable=True)
    seniority_level = Column(String(50), nullable=True)  # C-level, VP, Director, Manager, IC

    # Location
    location = Column(String(255), nullable=True)  # e.g., "Boston, MA"
    region = Column(String(100), nullable=True)     # e.g., "Northeast", "EMEA"

    # Contact details (enriched)
    email = Column(String(255), nullable=True)
    email_confidence = Column(Float, nullable=True)  # Hunter.io confidence score (0-100)
    email_status = Column(String(50), nullable=True)  # valid, invalid, risky, unknown
    phone = Column(String(50), nullable=True)

    # LinkedIn data
    linkedin_url = Column(String(500), nullable=True)
    linkedin_snippet = Column(Text, nullable=True)  # Bio/summary

    # Enrichment tracking
    enrichment_status = Column(String(50), default="not_started")
    # not_started, in_progress, enriched, failed, verified
    enriched_at = Column(DateTime, nullable=True)
    enrichment_source = Column(String(100), nullable=True)  # hunter.io, manual, etc.

    # Prospect management
    status = Column(String(50), default="new")
    # new, enriched, qualified, contacted, unqualified, bounced
    tags = Column(JSON, default=list)  # ["decision_maker", "hot_lead", etc.]
    notes = Column(Text, nullable=True)  # User notes

    # Discovery metadata
    discovered_via = Column(String(100), nullable=True)  # firecrawl, manual, import
    discovery_query = Column(String(500), nullable=True)  # Search query used

    # Relationships
    campaign = relationship("Campaign", back_populates="prospects")
    company = relationship("Company")

    # Indexes
    __table_args__ = (
        Index('idx_prospects_campaign', 'campaign_id'),
        Index('idx_prospects_company', 'company_id'),
        Index('idx_prospects_email', 'email'),
        Index('idx_prospects_status', 'status', 'enrichment_status'),
    )
```

---

### 7.5 EnrichmentLog

**Purpose**: Track enrichment attempts and results for audit/debugging

```python
class EnrichmentLog(Base):
    __tablename__ = "enrichment_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    prospect_id = Column(String(36), ForeignKey("prospects.id"), nullable=False)

    # Enrichment details
    enrichment_type = Column(String(50), nullable=False)  # email, phone, linkedin
    provider = Column(String(100), nullable=False)  # hunter.io, clearbit, manual

    # Results
    status = Column(String(50), nullable=False)  # success, failed, rate_limited
    result_data = Column(JSON, nullable=True)  # Raw API response
    confidence_score = Column(Float, nullable=True)

    # Timing
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
```

---

## 8. API Integrations

### 8.1 OpenAI API

**Use Cases**:
1. Competitive landscape analysis
2. Company domain discovery
3. Market insight generation
4. Role/title classification

**Key Functions** (from existing script):
- `query_openai_for_market_data()` - Analyze competitors
- `get_company_domains_via_gpt()` - Find company domains

**API Quota Management**:
- GPT-4: ~$0.01-0.03 per company analysis
- Cache results in database to avoid re-analysis
- User confirmation before running expensive operations

---

### 8.2 Firecrawl API

**Use Cases**:
1. LinkedIn profile search
2. Web scraping for contact discovery

**Key Functions** (from existing script):
- `find_executives_via_firecrawl()` - Search LinkedIn
- `search_firecrawl()` - Generic web search

**Configuration**:
- API Key: Stored in secrets management
- Rate Limits: 100 searches/day (free tier)
- Retry Logic: 3 attempts with exponential backoff

**Data Extraction**:
- Profile name, title, company, location
- Profile URL
- Snippet/bio text

---

### 8.3 Hunter.io API

**Use Cases**:
1. Email address discovery
2. Email verification

**Key Functions** (from existing script):
- `find_email()` - Find email by name + domain

**Configuration**:
- API Key: Stored in secrets management
- Rate Limits: 50 requests/month (free tier), 1,000/month (starter)
- Cost: $49/mo for 1,000 searches

**Response Data**:
```json
{
  "email": "john.doe@acme.com",
  "confidence": 95,
  "sources": [
    {"uri": "https://acme.com/about", "extracted_on": "2024-01-15"}
  ],
  "verification": {
    "status": "valid",
    "smtp_check": true,
    "mx_records": true
  }
}
```

---

### 8.4 Clearbit Logo API

**Use Cases**:
1. Company logo display

**Configuration**:
- Free tier available
- URL format: `https://logo.clearbit.com/{domain}`

**Fallback**: Use company initials if logo not found

---

## 9. UI/UX Design

### 9.1 Navigation Structure

```
Sales Outreach Prep (main nav item)
├── Dashboard (campaigns overview)
├── Campaigns
│   ├── All Campaigns (list)
│   └── [Campaign Detail]
│       ├── Overview tab (stats, charts)
│       ├── Companies tab (table)
│       ├── Prospects tab (table)
│       └── Market Intelligence tab (quadrant chart)
├── Companies (global company database)
└── Settings
    └── API Integrations (configure keys)
```

---

### 9.2 Key Pages/Views

#### Campaign List Page
```
┌─────────────────────────────────────────────────────────────┐
│ Sales Outreach Prep > Campaigns                             │
├─────────────────────────────────────────────────────────────┤
│ [+ New Campaign]  [Import CSV]  [Export]                    │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Search campaigns...                    [🔍]           │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ╔═══════════════════════════════════════════════════════╗  │
│ ║ Name          │ Status  │ Prospects │ Enriched % │ ... ║  │
│ ╠═══════════════════════════════════════════════════════╣  │
│ ║ Boston SaaS   │ Active  │    127    │    85%     │ ✎ 🗑 ║  │
│ ║ Healthcare    │ Draft   │     45    │    12%     │ ✎ 🗑 ║  │
│ ╚═══════════════════════════════════════════════════════╝  │
└─────────────────────────────────────────────────────────────┘
```

#### Campaign Detail Page - Prospects Tab
```
┌─────────────────────────────────────────────────────────────┐
│ Boston SaaS CTOs Q1 2025                                    │
├─────────────────────────────────────────────────────────────┤
│ [Overview] [Companies] [Prospects] [Market Intelligence]    │
│                                                              │
│ [+ Add Prospect] [Import CSV] [Find Prospects] [Enrich All] │
│                                                              │
│ Filters: Status [All ▼] | Enriched [All ▼] | Role [All ▼]  │
│                                                              │
│ ╔════════════════════════════════════════════════════════╗ │
│ ║ Name     │ Title     │ Company │ Email      │ Status  ║ │
│ ╠════════════════════════════════════════════════════════╣ │
│ ║ John Doe │ CTO       │ Acme    │ j@acme.com │ ✓ Enrich║ │
│ ║ Jane S.  │ VP Eng    │ Beta    │ [Finding] │ ⏳ Pend.║ │
│ ║ Bob Lee  │ Head IT   │ Gamma   │ ✗ Not Fnd │ ✗ Failed║ │
│ ╚════════════════════════════════════════════════════════╝ │
│                                                              │
│ Showing 127 prospects | 85% enriched                        │
└─────────────────────────────────────────────────────────────┘
```

#### Market Intelligence Chart
```
┌─────────────────────────────────────────────────────────────┐
│ Market Quadrant: SaaS Platforms                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   High                                                      │
│    │                    ● Acme (You)                        │
│    │         ● CompetitorA                                  │
│ A  │                                                         │
│ b  │  ● CompB                     ● CompC                   │
│ i  │                                                         │
│ l  │                  ● CompD                               │
│ i  │                                                         │
│ t  │                                                         │
│ y  │                                                         │
│    │                                                         │
│   Low────────────────────────────────────────────High      │
│               Completeness of Vision                        │
│                                                              │
│ Legend: ● High Market Share  ◐ Medium  ○ Low               │
└─────────────────────────────────────────────────────────────┘
```

---

### 9.3 Modal Forms

**Campaign Form**:
- Name (required)
- Description (textarea)
- Target Industry (text)
- Target Geography (text with examples)
- Target Roles (textarea with examples: "CTO, VP Engineering")
- Target Seniority (dropdown: C-level, VP, Director, Manager)
- Assigned To (user picker)

**Prospect Form**:
- Full Name (required)
- Job Title
- Company (autocomplete from existing companies)
- LinkedIn URL
- Email (manual override)
- Notes (textarea)
- Tags (multi-select: decision_maker, gatekeeper, influencer, etc.)

---

## 10. Success Metrics

### Product Metrics
- **Time to First Campaign**: How long from signup to first campaign created
- **Prospects per Campaign**: Average number of prospects per campaign
- **Enrichment Success Rate**: % of prospects with valid email found
- **Weekly Active Users**: Users who create/view campaigns weekly
- **API Cost per Prospect**: Total API spend ÷ total prospects enriched

### Business Metrics
- **Qualified Prospects Generated**: # of prospects marked as "qualified"
- **CRM Export Rate**: % of campaigns that get exported to CRM
- **Time Saved vs Manual**: Estimated hours saved vs manual research
- **Email Deliverability**: % of enriched emails that are deliverable

### Technical Metrics
- **Background Job Success Rate**: % of Celery tasks that complete successfully
- **API Rate Limit Errors**: # of times we hit API quotas
- **Average Enrichment Time**: Seconds per prospect enrichment
- **Database Query Performance**: P95 query time for prospect list

---

## 11. Implementation Phases

### Phase 1: MVP (4-6 weeks) ✅ APPROVED SCOPE

**Goal**: Basic campaign management + prospect discovery + email enrichment

**Features**:
1. ✅ Campaign CRUD (create, edit, delete, list)
2. ✅ Company management (add companies to campaign)
3. ✅ Prospect discovery via Firecrawl (LinkedIn search)
4. ✅ Email enrichment via Hunter.io
5. ✅ Prospect CRUD (view, edit, export CSV)
6. ✅ Background jobs (Celery) for search & enrichment
7. ✅ Basic dashboard (campaign stats)

**Out of Scope for MVP**:
- ❌ Market quadrant charts (Phase 2)
- ❌ AI competitive analysis (Phase 2)
- ❌ Advanced filtering/tagging (Phase 2)
- ❌ CRM integrations (Phase 3)

**Success Criteria**:
- User can create a campaign
- User can add companies
- User can search for prospects
- User can enrich emails
- User can export CSV

---

### Phase 2: Market Intelligence (2-3 weeks)

**Goal**: Add AI-powered competitive analysis and visualizations

**Features**:
1. ✅ OpenAI competitive landscape analysis
2. ✅ Market quadrant chart generation (Plotly)
3. ✅ AI insights display
4. ✅ Company domain auto-detection
5. ✅ Clearbit logo integration
6. ✅ Enhanced company profiles

**Success Criteria**:
- User can see competitive positioning chart
- User can read AI-generated insights
- Charts are interactive (click to see details)

---

### Phase 3: Advanced Features (4-6 weeks)

**Goal**: Power user features and integrations

**Features**:
1. ✅ Advanced prospect filtering & tagging
2. ✅ Bulk actions (bulk enrich, bulk qualify)
3. ✅ CSV import (upload prospect lists)
4. ✅ Email verification (Hunter.io verification API)
5. ✅ Salesforce/HubSpot export integration
6. ✅ Team collaboration (shared campaigns, activity log)
7. ✅ Slack notifications (new prospects enriched)

**Success Criteria**:
- Power users can manage 1000+ prospects efficiently
- Seamless CRM integration (1-click export)
- Team can collaborate on campaigns

---

### Phase 4: Automation & Intelligence (Future)

**Ideas**:
- Automated outreach sequencing (email cadences)
- Predictive lead scoring (AI ranks prospects)
- LinkedIn Sales Navigator integration
- Automated follow-up reminders
- Intent data integration (buyer signals)

---

## 12. Open Questions

### Technical Questions
1. **Q**: Should we support multiple email enrichment providers (Hunter.io, Clearbit, ZoomInfo)?
   **A**: TBD - Start with Hunter.io, add others if needed

2. **Q**: How do we handle de-duplication across campaigns?
   **A**: TBD - Use email + company as unique key? Allow duplicates but warn user?

3. **Q**: Should prospects be global or campaign-scoped?
   **A**: TBD - Proposal: Prospects belong to campaigns, but we can add "link to existing prospect" feature

4. **Q**: How do we handle LinkedIn rate limiting?
   **A**: TBD - Use Firecrawl's rate limiting, add queue delays, allow user to set max searches/day

5. **Q**: Should we cache OpenAI competitive analysis results?
   **A**: TBD - Yes, cache for 30 days, allow manual "refresh" button

### Product Questions
1. **Q**: Should users be able to share campaigns across their team?
   **A**: TBD - Phase 3 feature, start with single-user campaigns

2. **Q**: Do we need role-based permissions (admin can see all campaigns, SDR only their own)?
   **A**: TBD - Phase 3, use existing tenant isolation for now

3. **Q**: Should we track outreach activity (emails sent, responses)?
   **A**: TBD - Phase 4, focus on prep not execution for MVP

4. **Q**: How do we handle international prospects (non-US phone formats, GDPR)?
   **A**: TBD - Phase 2, add country/region support and GDPR compliance flags

### Business Questions
1. **Q**: What's the pricing model for API costs (pass-through to user or absorb)?
   **A**: TBD - Track costs per tenant, potentially set quotas

2. **Q**: Do we need API usage dashboards (show user their quota)?
   **A**: TBD - Phase 2 feature, helpful for transparency

3. **Q**: Should we offer a "free tier" with limited enrichments?
   **A**: TBD - Business decision, but technically easy to implement

---

## Appendix A: API Cost Estimates

### Hunter.io Pricing
- **Free**: 50 searches/month
- **Starter**: $49/mo for 1,000 searches
- **Growth**: $99/mo for 5,000 searches
- **Business**: $399/mo for 50,000 searches

**Cost per prospect**: $0.05 - $0.10 depending on plan

### OpenAI Pricing (GPT-4)
- **Input**: $0.03 per 1K tokens
- **Output**: $0.06 per 1K tokens

**Competitive analysis**: ~1,000 tokens input + 1,500 tokens output = $0.12 per company

### Firecrawl Pricing
- **Free**: 100 searches/day
- **Pro**: $200/mo for unlimited searches

**Cost**: $0 (free tier sufficient for MVP)

### Total Cost per Campaign (estimate)
- 10 companies × $0.12 = $1.20 (OpenAI)
- 100 prospects × $0.08 = $8.00 (Hunter.io)
- **Total**: ~$10 per campaign with 100 prospects

---

## Appendix B: Existing Code Assets

### market_mapper.py - Reusable Functions

**Already implemented**:
1. ✅ `query_openai_for_market_data()` - Get competitors + analysis
2. ✅ `generate_quadrant_chart()` - Create Plotly chart
3. ✅ `find_executives_via_firecrawl()` - Search LinkedIn
4. ✅ `get_company_domains_via_gpt()` - Find company domains
5. ✅ `find_email()` - Hunter.io email lookup (via utils)
6. ✅ `export_to_excel()` - Excel export (for reference)

**Needs adaptation for web app**:
- Convert to async service methods
- Add database persistence
- Add background job queueing
- Add tenant isolation
- Add error handling & retries

---

## Next Steps

1. ✅ **Review this PRD** - Stakeholder feedback
2. ⏳ **Finalize Phase 1 scope** - Agree on MVP features
3. ⏳ **Create database migration** - Set up initial tables
4. ⏳ **Build service layer** - Port market_mapper logic to services
5. ⏳ **Build CRUD routes** - Campaign & prospect management
6. ⏳ **Build UI** - Tables, forms, dashboard
7. ⏳ **Integration testing** - Firecrawl, Hunter.io, OpenAI
8. ⏳ **Deploy to staging** - Test with real data
9. ⏳ **User acceptance testing** - Get SDR feedback
10. ⏳ **Production deployment** - Launch Phase 1

---

**Document Status**: 📋 Draft - Awaiting Review
**Feedback Requested By**: [DATE]
**Target Start Date**: [DATE]
**Estimated Completion (Phase 1)**: [DATE + 6 weeks]
