# PRP: Content Broadcaster Slice (AI-Driven Content Planning, Generation, Refinement & Multi-Channel Publishing)

**Feature Owner:** Business Automations – Content Broadcasting
**Vertical Slice Path:** `app/features/content_broadcaster/`
**Depends On:**
- `core/` (DB, tenants, auth, scheduler, storage, logging)
- `features/connectors/` (installed connectors as publish targets)
- `features/secrets/` (**source of truth for OpenAI, SerpAPI, scraping API credentials**)
- `features/notifications/` (optional future use)

**Goal (V1+):**
Deliver a complete **AI-first content workflow**: users input content ideas → AI researches competitors → AI generates SEO-optimized first drafts → AI-assisted refinement to humanize language → manual review & approval → multi-channel scheduling & publishing.

---

## 1) Explicit Scope

### **Core Workflow (Planning-First Approach)**

```
Content Planning (user inputs topic ideas)
    ↓
AI Research & Analysis (scrape top competitors, analyze SEO gaps)
    ↓
AI Content Generation (create first draft + per-channel variants)
    ↓
AI Refinement Loop (iterative SEO validation & humanization, score ≥95/100)
    ↓
Present Draft to User (ready for human review)
    ↓
Manual Review & Approval (draft → in_review → approved/rejected)
    ↓
Scheduling (select connectors, schedule publish time)
    ↓
Background Publishing (Celery worker publishes to platforms)
    ↓
Delivery Tracking & Engagement Metrics
```

### **Feature Scope**

- **Content Planning:** Users create content ideas/topics in a planning table
- **AI Research:** Automatically fetch top Google results, scrape competitor content, analyze SEO opportunities
- **AI Generation:** Generate SEO-optimized long-form content + per-channel variants using OpenAI
- **AI Validation & Refinement:** Iteratively score content (0-100) against SEO criteria, refine until ≥95/100
- **Humanization:** De-AI language patterns, natural tone, conversational style
- **Multi-Channel Variants:** Per-channel content optimization (Twitter 280 chars, WordPress long-form, LinkedIn professional)
- **Approval Workflow:** Human-in-the-loop review before publishing
- **Scheduling & Jobs:** One publish job per selected connector; Celery worker executes
- **Publishing:** Adapter-based calls through Connectors slice
- **Storage:** Write all versions (competitor research, SEO analysis, draft iterations, final content) to disk
- **Engagement:** Optional polling for basic metrics; store snapshots
- **Security:** Tenant isolation, RBAC for approval/publishing actions
- **Validation:** Strong server-side checks (dates, states, connector readiness, API credentials)
- **Observability:** Structured logs, job metrics, idempotency keys, AI token usage tracking

**Out of Scope (initial release):** Media pipeline (image resizing), A/B testing, advanced analytics dashboard, multi-approver chains (single approver), OAuth callback UIs (handled by connectors slice), real-time collaboration.

---

## 2) Architecture Summary

- **API Layer (FastAPI, async):** content planning, AI research, AI generation, refinement, approvals, scheduling, jobs, deliveries
- **Services:**
  - `content_planning_service` — CRUD for content ideas/plans
  - `ai_research_service` — Google search, web scraping, competitor analysis (uses SerpAPI, scraping APIs)
  - `ai_generation_service` — SEO-optimized content generation using OpenAI (via Secrets slice)
  - `ai_validation_service` — Iterative SEO scoring (0-100), refinement feedback
  - `ai_refinement_service` — Humanization, de-AI patterns, tone adjustment
  - `content_service` — Content item CRUD, state management
  - `approval_service` — Review workflow, approve/reject
  - `schedule_service` — Job creation, scheduling
  - `publish_service` — Connector integration, publishing
  - `engagement_service` — Metrics polling (optional)
- **Workers (Celery + Redis):**
  - `content_generator` — Process content plans: research → generate → refine → present drafts
  - `publisher` — Execute publish_jobs to connectors
  - `engagement_poller` — Poll metrics (optional)
- **Data:** Postgres (SQLAlchemy 2.x), JSONB for flexible AI responses, research data, variants
- **Secrets:** **All API keys fetched via Secrets slice** (OpenAI, SerpAPI, scraping APIs) at call-time, never persisted to logs
- **Storage:** Local file system with versioned content:
  - `/storage/planning/{plan_id}/` — competitor research, SEO analysis
  - `/storage/drafts/{content_id}/` — draft iterations with scores
  - `/storage/published/{content_id}/` — final published payloads

---

## 3) Data Model (PostgreSQL / SQLAlchemy 2.x)

> All tenant-scoped tables include `tenant_id` (string, indexed). Use `AuditMixin` (created_at, updated_at, created_by, updated_by). Enforce FKs and indexes exactly as stated.

### 3.0 `content_plans` (**NEW - The Starting Point**)

**Purpose:** Store content ideas/topics entered by users. Background worker picks these up for AI processing.

- `id` (uuid, pk)
- `tenant_id` (string, idx)
- `title` (string(500), not null) — The content topic/idea (e.g., "Best Practices for API Design")
- `description` (text, nullable) — Additional context, instructions, target audience details
- `target_channels` (json array, default `[]`) — e.g., `["wordpress", "twitter", "linkedin"]`
- `target_audience` (string(100), nullable) — e.g., "developers", "executives", "general public"
- `tone` (string(50), nullable) — e.g., "professional", "casual", "technical", "friendly"
- `seo_keywords` (json array, default `[]`) — Optional user-provided keywords
- `competitor_urls` (json array, default `[]`) — Optional URLs to analyze
- `min_seo_score` (int, default 95) — Target SEO validation score (80-100)
- `max_iterations` (int, default 3) — Max refinement loops before presenting draft
- **Status Tracking:**
  - `status` (enum: `planned`, `researching`, `generating`, `refining`, `draft_ready`, `approved`, `archived`, `failed`)
  - `current_iteration` (int, default 0) — Track refinement loops
  - `latest_seo_score` (int, nullable) — Most recent validation score
- **Processing Results (JSONB storage):**
  - `research_data` (jsonb, default `{}`) — Scraped competitor content, top Google results
    ```json
    {
      "top_results": [{"title": "...", "url": "...", "scraped_content": "..."}],
      "seo_analysis": "AI-generated SEO gap analysis",
      "keywords_found": ["api", "best practices", ...]
    }
    ```
  - `generation_metadata` (jsonb, default `{}`) — AI generation details
    ```json
    {
      "model": "gpt-4",
      "prompt_tokens": 1500,
      "completion_tokens": 2000,
      "cost_estimate": 0.15,
      "generated_at": "2025-10-11T..."
    }
    ```
  - `refinement_history` (jsonb array, default `[]`) — All iteration attempts
    ```json
    [
      {
        "iteration": 1,
        "score": 78,
        "issues": ["Schema Markup", "Keyword Density"],
        "feedback": {...},
        "refined_at": "2025-10-11T..."
      },
      {
        "iteration": 2,
        "score": 92,
        "issues": ["Engagement Elements"],
        ...
      }
    ]
    ```
- **Linking:**
  - `generated_content_item_id` (uuid, nullable, fk → content_items.id) — One-to-one link to final draft
- **Error Handling:**
  - `error_log` (text, nullable) — Capture generation failures, API errors
  - `retry_count` (int, default 0) — Track automatic retries
- **Audit Fields:** `created_at`, `updated_at`, `created_by`, `updated_by` (from AuditMixin)

**Indexes:**
- `(tenant_id)`
- `(status, created_at)` — For worker polling
- `(generated_content_item_id)` — Lookup final draft

**State Transitions:**
```
planned → researching → generating → refining ⟲ (loop) → draft_ready → approved
                                          ↓
                                       failed
```

---

### 3.1 `content_items`
- `id` (uuid, pk)  
- `tenant_id` (string, idx)  
- `title` (text, not null)  
- `body` (text, not null) — **canonical body**, generally long-form  
- `state` (enum: `draft`, `in_review`, `scheduled`, `publishing`, `published`, `failed`, `rejected`)  
- `scheduled_at` (timestamptz, nullable)  
- `publish_at` (timestamptz, nullable)  
- **Approval fields:**  
  - `approval_status` (enum: `pending`, `approved`, `rejected`, default `pending`)  
  - `approved_by` (uuid, nullable), `approved_at` (timestamptz, nullable), `approval_comment` (text, nullable)  
- **AI fields:**  
  - `ai_prompt` (text, nullable)  
  - `ai_response` (jsonb, default `{}`)  — full OpenAI response meta: model, prompt_tokens, completion_tokens, cost_estimate, created_at  
  - `ai_generated` (boolean, default false)  
- **Variants pointer (optional):** no direct pointer; variants linked via `content_variants`  
- `created_by`, `updated_by` (uuid)  
- `created_at`, `updated_at` (timestamptz)

**Indexes:** `(tenant_id)`, `(state, scheduled_at)`, `(approval_status)`

### 3.2 `content_variants` (per-channel/per-purpose content)
- `id` (uuid, pk)  
- `tenant_id` (string, idx)  
- `content_item_id` (uuid, fk → content_items.id, idx)  
- `connector_catalog_key` (text, idx) — e.g., `twitter`, `wordpress` (stable key from catalog)  
- `purpose` (enum: `default`, `short`, `long`, `teaser`, `summary`, `A`, `B`)  
- `body` (text, not null) — channel-formatted text  
- `metadata` (jsonb, default `{}`) — e.g., `{ "char_count": 240, "hashtags": ["..."], "html": true }`  
- `created_at`, `updated_at`

**Uniqueness:** `(content_item_id, connector_catalog_key, purpose)`

### 3.3 `publish_jobs`
- `id` (uuid, pk)  
- `tenant_id` (string, idx)  
- `content_item_id` (uuid, fk → content_items.id, idx)  
- `connector_id` (uuid, fk → connectors.id, idx) — **installed instance**  
- `variant_id` (uuid, fk → content_variants.id, nullable) — if specific variant chosen  
- `run_at` (timestamptz, not null)  
- `status` (enum: `queued`, `running`, `success`, `failed`, `retrying`, `canceled`)  
- `attempt` (int, default 0)  
- `last_error` (text, nullable)  
- `correlation_id` (text, nullable, idx) — idempotency key: `${content_item_id}:${connector_id}:${run_at}`  
- `created_at`, `updated_at`

**Indexes:** `(run_at, status)`, `(tenant_id)`, `(content_item_id)`

### 3.4 `deliveries`
- `id` (uuid, pk)  
- `tenant_id` (string, idx)  
- `publish_job_id` (uuid, fk → publish_jobs.id, unique)  
- `external_post_id` (text)  
- `permalink` (text)  
- `response_json` (jsonb, default `{}`)  
- `created_at`

### 3.5 `engagement_snapshots` (optional)
- `id` (uuid, pk)  
- `tenant_id` (string, idx)  
- `delivery_id` (uuid, fk → deliveries.id, idx)  
- `captured_at` (timestamptz)  
- `likes`, `comments`, `shares`, `views` (ints, nullable)  
- `metrics_json` (jsonb, default `{}`)

---

## 4) Routes & Endpoints (API + HTMX)

Prefix: `/features/content_broadcaster`

### 4.0 Content Planning CRUD (**NEW - Entry Point**)

**Purpose:** Manage content ideas/topics. Creating a plan triggers background AI processing.

- `GET /planning` — List content plans with filters
  - **Query params:** `status`, `limit`, `offset`, `search`
  - **Returns:** Paginated list with current status, SEO score, iteration count

- `POST /planning` — Create new content plan (triggers AI processing)
  - **Body:**
    ```json
    {
      "title": "Best Practices for API Design",
      "description": "Target developers building REST APIs",
      "target_channels": ["wordpress", "medium", "linkedin"],
      "target_audience": "software developers",
      "tone": "professional",
      "seo_keywords": ["API", "REST", "best practices"],
      "competitor_urls": ["https://example.com/api-guide"],
      "min_seo_score": 95,
      "max_iterations": 3
    }
    ```
  - **Action:** Creates `content_plans` record with `status=planned`
  - **Background:** Celery worker picks up plan, starts research → generate → refine cycle

- `GET /planning/{id}` — Get plan details + processing status
  - **Returns:** Plan data, research_data, refinement_history, generated_content_item_id
  - **Use case:** Monitor AI progress, view iteration scores

- `PUT /planning/{id}` — Update plan (only if status=`planned` or `failed`)
  - **Body:** Same as POST, partial updates allowed
  - **Restriction:** Cannot edit while processing (researching/generating/refining)

- `DELETE /planning/{id}` — Soft delete plan (only if not draft_ready or approved)
  - **Action:** Set `status=archived`

- `POST /planning/{id}/retry` — Manually trigger retry for failed plans
  - **Action:** Reset `status=planned`, increment `retry_count`, clear `error_log`

- `POST /planning/{id}/approve-draft` — Move draft_ready → approved
  - **Action:** Update `status=approved`, link remains to content_item
  - **Result:** ContentItem becomes editable draft for human refinement

- `GET /planning/{id}/iterations` — View refinement history
  - **Returns:** Array of all refinement attempts with scores, issues, feedback

---

### 4.1 Content CRUD & Workflow
- `GET /content` — list/filter by state/date/assignee  
- `POST /content` — create draft (title, body)  
- `GET /content/{id}` — read item + variants  
- `PUT /content/{id}` — update draft (title, body); **write to /storage/drafts**  
- `POST /content/{id}/submit` — `draft → in_review`  
- `POST /content/{id}/approve` — set approval fields; if `schedule` block is present, create jobs + `state=scheduled`  
- `POST /content/{id}/reject` — set rejection + comment, move `→ draft`

### 4.2 AI Generation & Rewrite (OpenAI via Secrets)
- `POST /content/{id}/ai/generate`
  - **Body:** `{ "topic": "...", "channels": ["twitter","wordpress"], "tone": "professional", "cta": "Learn more", "length": "short|long" }`
  - Service constructs prompts per channel → **creates/updates `content_variants`** accordingly
  - Persists `ai_prompt`, `ai_response`, sets `ai_generated=true`
- `POST /content/{id}/ai/rewrite`
  - **Body:** `{ "variant_id": "...", "instruction": "shorten to 240 chars and add 2 hashtags" }`
  - Updates specific variant body + metadata
- **Secrets Usage:** All OpenAI API keys are fetched from **Secrets slice** at runtime (per-tenant). Key name: `openai_api_key` (must exist). Optional: `openai_org`, `openai_project`.

### 4.3 Scheduling & Jobs
- `POST /content/{id}/schedule`
  - **Body:** `{ "run_at": "ISO8601", "connector_ids": ["..."], "variant_strategy": "auto|by_channel|specific", "variant_map": { "twitter": "variant_uuid", ... } }`
  - Creates `publish_jobs`; set `state=scheduled`
- `GET /jobs` — list jobs with filters (status/date)
- `POST /jobs/{id}/retry` — requeue with backoff
- `POST /jobs/{id}/cancel` — cancel if queued

### 4.4 Deliveries & Engagement
- `GET /deliveries?content_id=...` — list deliveries, permalinks
- `GET /deliveries/{id}` — details (raw response_json)
- (Optional) `POST /engagement/poll?content_id=...` — trigger engagement polling job

---

## 5) Services (Business Logic)

### 5.1 `content_service`
- CRUD operations + writes draft file: `/storage/drafts/{content_id}.json` and/or `.md`
- `change_state(content_id, to_state, by_user)` enforcing legal transitions
- `get_item_with_variants(content_id)`

### 5.2 `ai_service` (uses **Secrets slice**)
- `get_openai_client(tenant_id)` — fetch secret `openai_api_key`; no logging of secret
- `generate_variants(tenant_id, content_id, topic, channels, tone, cta, length)`
  - **Models:** short-form → `gpt-4o-mini`; long-form → `gpt-4-turbo`
  - Channel-aware prompts with constraints (char limits, plain text vs markdown)
  - Persist variants + `ai_*` fields
- `rewrite_variant(tenant_id, variant_id, instruction)` — mutate variant body safely

**Prompt Template (per-channel):**
```
System: You are a senior copywriter generating {channel} copy.
User: Topic: "{topic}"
Constraints: {constraints_json}
Tone: {tone}
CTA: {cta}
Output: plain text for {channel}; keep within limits.
```

### 5.3 `schedule_service`
- `create_jobs(content_id, connector_ids, run_at, variant_strategy, variant_map)`
- Validations: run_at future; connectors active; variants exist
- Idempotency via `correlation_id`

### 5.4 `publish_service` (worker helper)
- `execute_job(job_id)` — resolve connector adapter, choose variant, publish
- On success: `deliveries` insert + `/storage/published/{content_id}/{job_id}.json`, update content publish_at if all succeeded
- On failure: status→failed, attempt++, record `last_error`, schedule retry/backoff

### 5.5 `engagement_service` (optional)
- Poll recent deliveries for metrics; store `engagement_snapshots`

---

## 6) Worker Processes

- Celery app; `publisher` runs minutely, selecting `(run_at <= now && status=queued)`
- Retry policy: exponential backoff with jitter, `max_attempts` (3–5)
- Engagement poller (optional CRON)

---

## 7) Templates (HTMX + Jinja + Tabler)

- `list.html` (filters)  
- `edit.html` (editor + **Generate with AI** modal)  
- `review.html` (approval queue)  
- `schedule.html` (datetime + connector multi-select + variant strategy)  
- `jobs.html` (status, retry/cancel)  
- `deliveries.html` (permalinks)  
- `partials/variant_table.html` (per-channel variants + Rewrite action)

---

## 8) Validation Rules (Hard Requirements)

- Title/body required (min lengths: title ≥ 3, body ≥ 10)  
- Schedule `run_at` ≥ now + 60s  
- Connectors must be tenant-owned and `active`  
- When `variant_strategy="specific"`, **every** selected connector must have a variant provided  
- AI `topic` length 2–200; reject outside bounds with 422  
- Trim AI outputs to channel constraints; if truncate → add `…` suffix  
- Secrets slice **must** have `openai_api_key`; else 422 with remediation message

---

## 9) Security, RBAC & Secrets

- Tenant isolation on all queries; verify ownership on content and variants
- Roles: **Editor** (draft/AI/submit), **Approver** (approve/reject/schedule), **Owner/Admin** (all)
- Secrets fetched at call-time; **never** persisted to logs or responses
- `authz` dependency wrappers per CLAUDE.md; reject unauthorised with 403

---

## 10) Observability

- Structured logs include: tenant_id, content_id, variant_id, job_id, connector_id, correlation_id
- Metrics: queued/running/success/failed, retry counts, AI call latency/tokens
- Dead-letter: expose UI filter for `failed` jobs with “Retry” action

---

## 11) Testing

- Unit: services (AI prompt build, variant save, schedule rules, state transitions)
- Integration: full happy path with mock connector adapter
- Worker: retry/backoff, idempotency (same correlation_id yields single publish)
- UI: HTMX flows (save, AI generate, approve, schedule, retry)
- Security: RBAC checks; secret missing/invalid

---

## 12) Success Criteria

- AI-assisted variants created and editable per channel
- Approved items can be scheduled to installed connectors
- Worker publishes, records deliveries, and writes published payloads
- States remain consistent; retries work
- No secret leakage; strong validation and RBAC enforcement

---

## 13) Deliverables Checklist

- Models + migrations (all tables)
- Routes (content, AI, schedule, jobs, deliveries)
- Services (content, AI with Secrets, schedule, publish, engagement)
- Worker tasks (publisher + optional engagement)
- Templates (editor + AI modal, variants, approval, schedule, jobs, deliveries)
- Tests (unit + integration + UI)
- Slice README
