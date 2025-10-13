# Content Broadcaster Implementation Progress

**Last Updated:** 2025-10-11
**Status:** Phase 1 (Database) - IN PROGRESS

---

## ✅ Completed Tasks

### 1. Documentation (100% Complete)
- ✅ Updated PRP with content planning flow
- ✅ Updated PROJECT_PLAN with new phases
- ✅ Created content_plans table schema design

### 2. Database Models (100% Complete)
- ✅ Created `ContentPlanStatus` enum (8 states)
- ✅ Created `VariantPurpose` enum (7 purposes)
- ✅ Implemented `ContentPlan` model (lines 70-174 in models.py)
  - Full JSONB support for research_data, generation_metadata, refinement_history
  - One-to-one relationship with ContentItem
  - Audit trail integration
- ✅ Implemented `ContentVariant` model (lines 242-298 in models.py)
  - Per-channel content optimization
  - Metadata storage for formatting constraints
  - Relationship with ContentItem

### 3. Database Migration (100% Complete)
- ✅ Created Alembic migration file: `a1b2c3d4e5f6_add_content_plans_and_variants_tables.py`
- ✅ Proper indexes for tenant isolation and query performance
- ✅ Foreign key constraints
- ✅ JSON/JSONB defaults
- ✅ Down migration for rollback

---

## 🚧 In Progress

### Database Deployment
- ⏳ Need to start PostgreSQL container
- ⏳ Apply migration: `python3 manage_db.py upgrade`
- ⏳ Verify tables created successfully

---

## 📋 Next Steps (Priority Order)

### HIGH PRIORITY - Core Services

#### 1. Content Planning Service
**File:** `app/features/business_automations/content_broadcaster/services/content_planning_service.py`

**Methods to implement:**
```python
class ContentPlanningService(BaseService[ContentPlan]):
    async def create_plan(self, plan_data: ContentPlanCreate) -> ContentPlan
    async def list_plans(self, filters: PlanFilters) -> List[ContentPlan]
    async def get_plan(self, plan_id: str) -> ContentPlan
    async def update_plan(self, plan_id: str, updates: ContentPlanUpdate) -> ContentPlan
    async def delete_plan(self, plan_id: str) -> bool
    async def retry_plan(self, plan_id: str) -> ContentPlan
    async def approve_draft(self, plan_id: str) -> ContentPlan
```

#### 2. AI Research Service
**File:** `app/features/business_automations/content_broadcaster/services/ai_research_service.py`

**Port logic from:** `docs/SEO Blog Generator.py` (lines 33-101)

**Methods to implement:**
```python
class AIResearchService:
    async def fetch_top_google_results(self, query: str, num_results: int = 5) -> List[Dict]
    async def scrape_article_content(self, url: str) -> str
    async def analyze_competitor_seo(self, combined_content: str) -> str
    async def process_research(self, plan_id: str, title: str) -> Dict
```

**API Keys needed** (from Secrets slice):
- `serpapi_key` or `scrapingbee_api_key`
- `openai_api_key` (for SEO analysis)

#### 3. AI Generation Service
**File:** `app/features/business_automations/content_broadcaster/services/ai_generation_service.py`

**Port logic from:** `docs/SEO Blog Generator.py` (lines 163-246)

**Methods to implement:**
```python
class AIGenerationService:
    async def generate_blog_post(
        self,
        title: str,
        seo_analysis: str,
        previous_content: Optional[str] = None,
        validation_feedback: Optional[Dict] = None
    ) -> str

    async def generate_variants_per_channel(
        self,
        content: str,
        channels: List[str]
    ) -> List[ContentVariant]
```

#### 4. AI Validation Service
**File:** `app/features/business_automations/content_broadcaster/services/ai_validation_service.py`

**Port logic from:** `docs/SEO Blog Generator.py` (lines 248-355)

**Methods to implement:**
```python
class AIValidationService:
    async def validate_content(self, title: str, body: str) -> Dict
    # Returns: {"score": 85, "status": "FAIL", "issues": [...], "recommendations": {...}}

    async def extract_json_response(self, raw_response: str) -> Dict
```

**SEO Scoring Criteria (0-100):**
- Keyword Optimization (20 points)
- Content Structure & Readability (15 points)
- Schema Markup & Metadata (15 points)
- Internal & External Links (15 points)
- Engagement & Interactive Elements (15 points)
- On-Page SEO & Mobile Friendliness (20 points)

#### 5. AI Refinement Service
**File:** `app/features/business_automations/content_broadcaster/services/ai_refinement_service.py`

**Methods to implement:**
```python
class AIRefinementService:
    async def refine_content(
        self,
        content: str,
        validation_feedback: Dict,
        previous_version: str
    ) -> str

    async def humanize_language(self, content: str) -> str

    async def refinement_loop(
        self,
        plan_id: str,
        initial_content: str,
        min_score: int,
        max_iterations: int
    ) -> Dict  # Returns: {final_content, final_score, iterations_used}
```

### MEDIUM PRIORITY - Background Worker

#### 6. Celery Worker
**File:** `app/features/business_automations/content_broadcaster/tasks.py`

**Task to implement:**
```python
@celery_app.task(name="content_broadcaster.process_content_plan")
def process_content_plan(plan_id: str):
    """
    Background task to process content plans:
    1. Update status to 'researching'
    2. Call ai_research_service.process_research()
    3. Update status to 'generating'
    4. Call ai_generation_service.generate_blog_post()
    5. Update status to 'refining'
    6. Call ai_refinement_service.refinement_loop()
    7. Create ContentItem with final draft
    8. Update plan status to 'draft_ready'
    9. Link plan to content_item
    """
```

**Error Handling:**
- Catch all exceptions
- Log to `content_plans.error_log`
- Set status to 'failed'
- Implement retry logic

### MEDIUM PRIORITY - API Routes

#### 7. Planning Routes
**File:** `app/features/business_automations/content_broadcaster/routes/planning_routes.py`

**Endpoints:**
- `GET /planning` - List plans
- `POST /planning` - Create plan (triggers worker)
- `GET /planning/{id}` - Get plan details
- `PUT /planning/{id}` - Update plan
- `DELETE /planning/{id}` - Archive plan
- `POST /planning/{id}/retry` - Retry failed plan
- `POST /planning/{id}/approve-draft` - Approve draft
- `GET /planning/{id}/iterations` - View refinement history

### LOWER PRIORITY - UI Templates

#### 8. Planning UI
**Files:**
- `templates/content_broadcaster/planning_list.html`
- `templates/content_broadcaster/partials/create_plan_modal.html`
- `templates/content_broadcaster/partials/plan_detail_modal.html`
- `templates/content_broadcaster/partials/plan_status_badge.html`

---

## 📊 Implementation Status by File

| File | Status | Lines | Notes |
|------|--------|-------|-------|
| `models.py` | ✅ Complete | 374 total | Added ContentPlan (105 lines), ContentVariant (57 lines) |
| `migrations/a1b2c3d4e5f6...py` | ✅ Complete | 181 lines | Migration ready to apply |
| `services/content_planning_service.py` | ❌ Not Started | 0 | HIGH PRIORITY |
| `services/ai_research_service.py` | ❌ Not Started | 0 | HIGH PRIORITY |
| `services/ai_generation_service.py` | ❌ Not Started | 0 | HIGH PRIORITY |
| `services/ai_validation_service.py` | ❌ Not Started | 0 | HIGH PRIORITY |
| `services/ai_refinement_service.py` | ❌ Not Started | 0 | HIGH PRIORITY |
| `tasks.py` | ❌ Not Started | 0 | MEDIUM PRIORITY |
| `routes/planning_routes.py` | ❌ Not Started | 0 | MEDIUM PRIORITY |
| Templates (planning UI) | ❌ Not Started | 0 | LOWER PRIORITY |

---

## 🔧 Technical Notes

### Database Schema Highlights

**content_plans table:**
- Primary key: UUID string
- Tenant isolation: `tenant_id` indexed
- Status enum: 8 states (planned → researching → generating → refining → draft_ready → approved/archived/failed)
- JSONB fields for flexible data storage
- One-to-one FK to content_items

**content_variants table:**
- Unique constraint: `(content_item_id, connector_catalog_key, purpose)`
- Optimized for multi-channel publishing
- JSONB metadata for channel-specific constraints

### Dependencies from SEO Blog Generator

**Python Packages Needed:**
- `openai` (already in requirements.txt)
- `requests` (already in requirements.txt)
- `beautifulsoup4` (already in requirements.txt)
- SerpAPI client or ScrapingBee client (need to add)

**API Keys Required (via Secrets slice):**
- `openai_api_key` ✅ Already supported
- `serpapi_key` ❌ Need to add support
- `scrapingbee_api_key` or `scrapingdog_api_key` ❌ Need to add

### Service Layer Architecture

All services should:
1. Inherit from `BaseService[Model]` for tenant isolation
2. Use async/await for all operations
3. Fetch API keys from Secrets slice (never hardcode)
4. Log all operations with structured logging
5. Handle errors gracefully with detailed error messages
6. Store intermediate results in JSONB fields for debugging

### Worker Architecture

Celery task should:
1. Poll `content_plans` where `status = 'planned'`
2. Update status before each step
3. Store all intermediate data in JSONB fields
4. Support graceful failure and retry
5. Be idempotent (can be run multiple times safely)
6. Have configurable timeouts

---

## 🎯 Success Criteria

### Phase 1 Complete When:
- ✅ Models created
- ✅ Migration created
- ⏳ Migration applied successfully
- ⏳ Tables visible in database

### Phase 2 Complete When:
- ❌ All 5 AI services implemented
- ❌ Unit tests for each service
- ❌ Integration with Secrets slice verified
- ❌ API keys fetched successfully

### Phase 3 Complete When:
- ❌ Celery worker implemented
- ❌ Worker processes plans successfully
- ❌ State transitions working correctly
- ❌ Error handling tested

### Phase 4 Complete When:
- ❌ Planning routes implemented
- ❌ Routes tested with Postman/httpx
- ❌ CRUD operations working

### Phase 5 Complete When:
- ❌ Basic planning UI created
- ❌ Users can create plans via web interface
- ❌ Plan status visible in UI
- ❌ Iteration history viewable

### PoC Complete When:
- ❌ End-to-end workflow tested: create plan → AI generates content → draft ready → approve → schedule → publish
- ❌ At least one successful content generation from planning to publishing
- ❌ All critical paths have error handling
- ❌ Documentation updated with usage examples

---

## 📝 Commands to Run Next

```bash
# 1. Start PostgreSQL
docker start postgres  # or docker-compose up -d postgres

# 2. Apply migration
python3 manage_db.py upgrade

# 3. Verify tables created
python3 manage_db.py current
# Should show: a1b2c3d4e5f6

# 4. Check database
psql $DATABASE_URL -c "\dt content_*"
# Should show: content_items, content_plans, content_variants

# 5. Start implementing services
# Create: services/content_planning_service.py
# Create: services/ai_research_service.py
# etc.
```

---

## 📚 Reference Documents

- **PRP:** [docs/PRP_Content_Broadcaster_Slice_FULL.md](PRP_Content_Broadcaster_Slice_FULL.md)
- **Project Plan:** [docs/PROJECT_PLAN_Content_Broadcaster_Slice.md](PROJECT_PLAN_Content_Broadcaster_Slice.md)
- **SEO Blog Generator:** [docs/SEO Blog Generator.py](SEO%20Blog%20Generator.py)
- **README:** [README.md](../README.md)
- **Models:** [models.py](../models.py)

---

## 🤝 Contributors

- AI Assistant: Architecture, models, migration, documentation
- Paul (Human): Requirements, SEO Blog Generator script, validation

---

**Next Session:** Start implementing AI services, beginning with `content_planning_service.py`
