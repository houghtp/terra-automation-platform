# Content Broadcaster Implementation Progress

**Last Updated:** 2025-11-10  
**Current Phase:** 3 — End-to-End Workflow Demo (async Celery path live; SSE progress pending)

This document now reflects the current state of the codebase. The previous version still described the pre-service state, so every section below was rewritten after inspecting the live modules under `app/features/business_automations/content_broadcaster/`.

---

## ✅ Completed Work

### Phase 1 – Data Foundations
- `models.py` defines fully-audited SQLAlchemy models for `ContentPlan`, `ContentVariant`, `ContentItem`, approvals, and publish jobs (lines 79-410).
- Alembic migrations shipped (`migrations/versions/a1b2c3d4e5f6_*.py`, `493767b1324e_add_skip_research_to_content_plan.py`, `2025_11_03_add_prompt_settings_to_content_plans.py`) covering plan+variant tables, skip-research flag, and prompt settings JSON.

### Phase 2 – Service Layer & AI Workflow
- `services/content_planning_service.py` implements full CRUD + filtering, retry, audit-aware status updates, and refinement history helpers (501 LOC, lines 16-532).
- `services/ai_research_service.py` now uses centralized Secret-managed OpenAI + Firecrawl clients, scrapes competitors, and returns structured research data (lines 1-377).
- `services/ai_generation_service.py` handles blog generation, per-channel variants, SEO validation, and metadata extraction; prompt content comes from the AI Prompt Service (lines 1-520).
- `services/content_orchestrator_service.py` coordinates research/generation/refinement, persists `latest_seo_score`, `refinement_history`, creates `ContentItem`s, and stores `ContentVariant`s when `target_channels` are provided.
- `services/progress_stream.py` introduces an SSE-friendly pub/sub manager for live progress updates.

### Phase 3 – API + UI (Async Demo Path)
- FastAPI routers (`routes/planning_routes.py`, `form_routes.py`, `dashboard_routes.py`, `crud_routes.py`, `api_routes.py`) expose HTMX-friendly planning endpoints, CRUD APIs, dashboard views, and streaming SEO generation APIs.
- `/planning` supports create/list/detail/edit/delete/retry/process/approve flows with audit + tenant isolation. The `/planning/{plan_id}/process-async` endpoint now enqueues a Celery worker while `/process` remains as a synchronous fallback.
- Celery worker (`tasks.py`) + queue wiring (`celery_app`, `task_manager`) run the same orchestrator pipeline headlessly, updating status + error logs if failures occur.
- Templates under `templates/content_broadcaster/` plus Tabulator-powered JS (`static/js/planning-table.js`) render planning tables, modals, SEO score badges, refinement history, and prompt overrides. UI now displays live SEO scores and refinement iteration counts.
- `tests/test_content_broadcaster_integration.py` covers the legacy Content Broadcaster service (content CRUD, approvals, scheduling) so we have regression coverage for the original slice.

---

## 🚧 Active Work / Gaps

1. **Background Processing Observability**  
   - Celery worker + async endpoint are live, but we still need progress streaming (SSE/WebSocket), task dashboards, and retries surfaced in the UI. Currently users only see a status change with no detailed telemetry.

2. **Trigger + UX Automation**  
   - Plan creation does not enqueue processing automatically. We need a user-friendly “Process” button (already present) plus an async queue path that runs autonomously and surfaces progress via SSE (`progress_stream_manager` is unused outside SEO connector APIs).

3. **Automated Tests for New Modules**  
   - `ContentPlanningService`, `AIResearchService`, `AIGenerationService`, and `ContentOrchestratorService` have zero unit/async integration tests. Only the older `ContentBroadcasterService` scenarios are covered.

4. **Content Publishing UX Hooks**  
   - JS handlers in `static/js/content-table.js` still contain TODO placeholders for approve/reject/schedule/publish actions. The backend APIs exist, but buttons are not wired.

5. **Advanced Insights**  
   - Research data still leaves `keywords_found` empty (see TODO in `ai_research_service.py:353`), and we have not added dashboard visualizations for SEO gains/refinement history.

6. **Operational Readiness**  
   - Need runbook updates covering: starting Postgres, running `python3 manage_db.py upgrade`, configuring OpenAI + Firecrawl secrets, and verifying migrations. Current doc assumes these steps without concrete verification.

---

## 📋 Next Actions (Priority Order)

1. **Progress Streaming + Task UX**
   - Publish worker progress (researching/generating/refining) via `progress_stream_manager` and surface it on the planning table/cards.  
   - Persist Celery task IDs + timestamps so users can check status/history.  
   - Consider auto-enqueue on plan creation or scheduled batches once observability is solid.

2. **Testing Pass**
   - Add async unit tests for `ContentPlanningService` (validation, filtering, status updates) and `ContentOrchestratorService` (happy path + failure).  
   - Mock OpenAI/Firecrawl clients to keep tests deterministic.  
   - Extend integration tests to cover the planning routes (HTMX responses) and variant generation.

3. **UI Wiring + UX Polish**
   - Hook the TODO actions in `static/js/content-table.js` to the existing `/api/{content_id}` endpoints so approvals, rejections, scheduling, and publishing work end-to-end.  
   - Finish modal implementations referenced in `partials/list_content.html` and add SSE-powered progress indicators.

4. **Research Insights Enhancements**
   - Extract keyword summaries inside `AIResearchService.process_research` and surface them in `metadata_tab.html`.  
   - Add a compact competitor comparison widget (Doc PRP §4.2 requirement).

5. **Ops + Docs**
   - Add a short runbook section (README or doc) describing DB migration commands, secret prerequisites, and demo checklist so onboarding engineers can reproduce the flow without tribal knowledge.

---

## 📊 File Status Snapshot

| File / Area | Status | Notes |
|-------------|--------|-------|
| `models.py` | ✅ | ContentPlan/Variant/Item definitions with audit + enums. |
| `migrations/*.py` | ✅ | Tables, skip_research, prompt settings migrations present. |
| `services/content_planning_service.py` | ✅ | CRUD, filters, status + audit helpers implemented. |
| `services/ai_research_service.py` | ✅ | Firecrawl/OpenAI powered research pipeline. |
| `services/ai_generation_service.py` | ✅ | Blog drafts, variants, validation, metadata extraction. |
| `services/content_orchestrator_service.py` | ✅ | Research→Generation→Refinement pipeline + variant persistence. |
| `services/progress_stream.py` | ✅ | SSE pub/sub utility (needs adoption inside planning workflow). |
| `routes/planning_routes.py` | ✅ | HTMX/JSON API for planning with new `/process-async` Celery enqueue + sync fallback. |
| `templates/content_broadcaster/*` | ✅ | Planning UI, modals, SEO score badges, prompt management. |
| `static/js/planning-table.js` | ✅ | Tabulator table, status badges, async process trigger + view actions. |
| `static/js/content-table.js` | ⚠️ | Core actions still TODO in JS even though backend APIs exist. |
| `content_broadcaster/tasks.py` | ✅ | Celery worker coordinates orchestrator + secret retrieval for plans. |
| Tests (new services) | ❌ | Only legacy ContentBroadcaster tests exist; planning/AI pipeline untested. |

---

## 📝 Demo Checklist (current state)

- [x] Create content plan via UI/form or API.  
- [x] Run `/planning/{plan_id}/process-async` (Celery) or `/process` (sync fallback) to generate research → draft → variants.  
- [x] View SEO score, refinement history, and generated draft in HTMX modal.  
- [x] Approve/schedule content via backend APIs (front-end buttons still TODO).  
- [ ] Trigger processing automatically via Celery/GH worker.  
- [ ] Display real-time progress and job history in UI.  
- [ ] Show published metrics/accounts after jobs execute.

This should serve as the authoritative progress tracker going forward. Update it whenever a major milestone (worker, tests, UI wiring, ops runbook) lands.
