# PROJECT_PLAN: Content Broadcaster Slice (AI-Driven Content Planning & Multi-Channel Publishing)

Status legend: ☐ Not Started · ⏳ In Progress · ✅ Done

## Phase 0 — Prep
- ✅ Create slice directory `app/features/business_automations/content_broadcaster/`
- ✅ Register routers `/features/content-broadcaster`
- ✅ Add README with overview and endpoints

## Phase 1 — Database (Updated for Planning-First Flow)
- ⏳ Migrations for:
  - [ ] **content_plans (NEW)** — Content ideas/topics (starting point)
  - [x] content_items — AI-generated drafts
  - [ ] **content_variants (NEW)** — Per-channel optimized variants
  - [x] publish_jobs — Publishing tasks
  - [x] deliveries — Published results
  - [x] engagement_snapshots — Metrics tracking (optional)
- ☐ Indexes/constraints matching updated PRP
- ☐ Verify tenant_id + AuditMixin on all tables

## Phase 2 — Services (Expanded for AI Pipeline)

### 2.1 Content Planning Services
- ☐ **content_planning_service** — CRUD for content_plans
  - `create_plan()`, `list_plans()`, `get_plan()`, `update_plan()`, `delete_plan()`, `retry_plan()`

### 2.2 AI Research & Generation Services
- ☐ **ai_research_service** — Competitor analysis
  - `fetch_top_google_results(query)` — Using SerpAPI/ScrapingBee
  - `scrape_article_content(url)` — Extract text from URLs
  - `analyze_competitor_seo(combined_content)` — AI SEO gap analysis
  - Store results in `content_plans.research_data`

- ☐ **ai_generation_service** — Content creation
  - `generate_blog_post(title, seo_analysis, tone)` — First draft generation
  - `generate_variants_per_channel(content, channels)` — Create channel-specific versions
  - Persist to `content_items` + `content_variants`

- ☐ **ai_validation_service** — SEO scoring
  - `validate_content(title, body)` — Score 0-100 based on SEO criteria
  - `extract_validation_feedback(score, issues)` — Structured improvement suggestions
  - Return JSON: `{score, status, issues, recommendations}`

- ☐ **ai_refinement_service** — Iterative improvement
  - `refine_content(content, validation_feedback, prev_version)` — Improve based on feedback
  - `humanize_language(content)` — De-AI patterns, natural tone
  - Loop until `score >= min_seo_score` or `max_iterations` reached
  - Store all iterations in `content_plans.refinement_history`

### 2.3 Existing Services (Keep)
- ⏳ **content_service** — Content item CRUD, state management
- ☐ **approval_service** — Review workflow (approve/reject)
- ☐ **schedule_service** — Job creation, scheduling
- ☐ **publish_service** — Connector publishing
- ☐ **engagement_service** — Metrics polling (optional)

## Phase 3 — Routes (API + HTMX)

### 3.1 Content Planning Routes (NEW)
- ☐ `GET /planning` — List plans with status/score filters
- ☐ `POST /planning` — Create plan (triggers AI worker)
- ☐ `GET /planning/{id}` — View plan + processing status
- ☐ `PUT /planning/{id}` — Update plan (if not processing)
- ☐ `DELETE /planning/{id}` — Archive plan
- ☐ `POST /planning/{id}/retry` — Retry failed plan
- ☐ `POST /planning/{id}/approve-draft` — Move draft_ready → approved
- ☐ `GET /planning/{id}/iterations` — View refinement history

### 3.2 Content Routes (Updated)
- ⏳ Content CRUD: list/create/read/update/submit/approve/reject
- ☐ AI manual triggers (override): `/content/{id}/ai/generate`, `/content/{id}/ai/rewrite`
- ☐ Schedule: `/content/{id}/schedule`

### 3.3 Job & Delivery Routes (Keep)
- ⏳ Jobs: list/retry/cancel
- ⏳ Deliveries: list/detail

## Phase 4 — Templates (HTMX + Tabler)

### 4.1 Content Planning UI (NEW)
- ☐ `planning_list.html` — Dashboard showing all plans with status badges, scores
- ☐ `planning_create_modal.html` — Form to create new content plan
- ☐ `planning_detail.html` — View plan progress, iteration history, research data
- ☐ `partials/plan_status_badge.html` — Status indicators (planned/researching/generating/refining/ready)
- ☐ `partials/iteration_timeline.html` — Visual timeline of refinement attempts

### 4.2 Content Review UI (Updated)
- ☐ `content_list.html` — AI-generated drafts ready for review
- ☐ `content_edit.html` — Human refinement editor
- ☐ `review.html` — Approval queue
- ☐ `schedule.html` — Schedule publishing

### 4.3 Existing Templates (Keep)
- ☐ jobs.html
- ☐ deliveries.html
- ☐ partials/variant_table.html

## Phase 5 — Workers (Expanded for AI Pipeline)

### 5.1 Content Generation Worker (NEW - Critical)
- ☐ **Celery task:** `process_content_plan(plan_id)`
  - Poll `content_plans` where `status=planned`
  - **Step 1:** Research — Fetch Google results, scrape, analyze SEO
  - **Step 2:** Generate — Create first draft + variants
  - **Step 3:** Validate — Score content (0-100)
  - **Step 4:** Refine — Loop until score ≥ target or max iterations
  - **Step 5:** Present — Create `content_item`, set plan `status=draft_ready`
  - **Error handling:** Catch all exceptions, log to `error_log`, set `status=failed`

### 5.2 Publisher Worker (Keep)
- ☐ **Celery task:** `execute_publish_jobs()`
  - Poll `publish_jobs` where `run_at <= now AND status=queued`
  - Publish via connector adapters
  - Create deliveries, update statuses

### 5.3 Engagement Worker (Optional)
- ☐ Poll metrics from published content

## Phase 6 — Security & Validation

### 6.1 API Key Management
- ☐ Fetch all API keys via **Secrets slice** (never hardcode)
  - `openai_api_key` (required)
  - `serpapi_key` (required for research)
  - `scrapingbee_api_key` or `scrapingdog_api_key` (required for scraping)
- ☐ Validate keys exist before processing plans

### 6.2 RBAC & Authorization
- ☐ Content planning: Any authenticated user can create plans
- ☐ Approve drafts: Require `approver` or `admin` role
- ☐ Publish: Require `admin` role or content owner

### 6.3 Input Validation
- ☐ Title length: 3-500 chars
- ☐ Min SEO score: 80-100
- ☐ Max iterations: 1-5
- ☐ Target channels: Must be valid connector catalog keys
- ☐ Competitor URLs: Valid HTTP/HTTPS URLs

### 6.4 Tenant Isolation
- ☐ All queries filtered by `tenant_id`
- ☐ Secrets fetched per-tenant
- ☐ Storage paths include tenant ID

## Phase 7 — Testing

### 7.1 Unit Tests
- ☐ `test_content_planning_service.py` — CRUD operations
- ☐ `test_ai_research_service.py` — Mock SerpAPI/scraping responses
- ☐ `test_ai_generation_service.py` — Mock OpenAI responses
- ☐ `test_ai_validation_service.py` — SEO scoring logic
- ☐ `test_ai_refinement_service.py` — Iteration logic, humanization

### 7.2 Integration Tests
- ☐ `test_content_generation_workflow.py` — End-to-end: plan → research → generate → refine → draft_ready
- ☐ `test_approval_workflow.py` — draft_ready → approved → scheduled → published
- ☐ `test_worker_error_handling.py` — Failed API calls, retries, error logging

### 7.3 Worker Tests
- ☐ `test_content_generation_worker.py` — Celery task execution, state transitions
- ☐ `test_publisher_worker.py` — Publishing idempotency, retries

### 7.4 UI Tests (Playwright)
- ☐ Create content plan flow
- ☐ Monitor plan progress
- ☐ Approve generated draft
- ☐ Schedule and publish

## Phase 8 — Storage & File Management

- ☐ Create storage directories:
  - `/storage/planning/{tenant_id}/{plan_id}/` — Competitor research, SEO analysis
  - `/storage/drafts/{tenant_id}/{content_id}/` — Draft iterations with scores
  - `/storage/published/{tenant_id}/{content_id}/` — Final published content

- ☐ Implement file writes:
  - Research phase: Save scraped articles, SEO analysis
  - Generation phase: Save draft iterations with validation scores
  - Publishing phase: Save final payloads + connector responses

## Phase 9 — Docs & QA

- ✅ PRP updated with content_plans table and workflow
- ⏳ PROJECT_PLAN updated (this document)
- ☐ Update CURRENT_STATUS.md
- ✅ README.md with API examples
- ☐ Add workflow diagrams (planning → AI → approval → publish)
- ☐ Document API key setup instructions
- ☐ Document SEO scoring criteria

## Phase 10 — Code Cleanup & Refactoring

- ☐ Remove old manual content creation flow (if not needed)
- ☐ Refactor existing `services.py` to separate concerns
- ☐ Move SEO Blog Generator patterns into proper services
- ☐ Add comprehensive error messages and user feedback

---

## Exit Criteria (Updated)

- ☐ Users can create content plans with topic ideas
- ☐ Background worker automatically researches competitors
- ☐ AI generates SEO-optimized first drafts (score ≥95)
- ☐ Drafts are humanized and de-AI'd
- ☐ All iteration history is tracked and viewable
- ☐ Generated drafts presented to users for manual review
- ☐ Approval workflow functions correctly
- ☐ Scheduled jobs publish to connectors successfully
- ☐ Deliveries recorded + files written to storage
- ☐ RBAC enforced, API keys managed via Secrets slice
- ☐ Full workflow tested end-to-end

---

## Implementation Priority (PoC)

### **HIGHEST PRIORITY (PoC Focus)**
1. ✅ Update PRP document
2. ✅ Update PROJECT_PLAN (this file)
3. **Create content_plans table migration**
4. **Implement basic ai_research_service (Google search + scraping)**
5. **Implement ai_generation_service (OpenAI content creation)**
6. **Implement ai_validation_service (SEO scoring)**
7. **Create content generation Celery worker**
8. **Basic planning UI (create plan, view status)**

### **MEDIUM PRIORITY**
9. Complete ai_refinement_service (iteration loop)
10. Content variants table + generation
11. Approval workflow integration
12. Storage file writes

### **LOWER PRIORITY**
13. Publisher worker (reuse from phase 5.2)
14. Complete templates
15. Comprehensive testing
16. Engagement tracking
