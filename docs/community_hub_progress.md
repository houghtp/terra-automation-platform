# Community Hub Progress Tracker

Status board for the Radium Community Hub slice. Use the checklists below to see what is live, what is in progress, and the remaining scope to reach a V1 release.

## ✅ Delivered

- [x] Tenant-scoped member and partner directories with CRUD services, HTMX forms, and API routes
- [x] Community groups, posts, comments, and messaging flows wired into shared service layer
- [x] Events and polls modules (CRUD + templates) exposed through `/features/community/*`
- [x] Content & Learning Hub data model (articles, podcasts, videos, news, engagement) with Alembic migration `9b3c1d0f3b5a`
- [x] Content Hub services + API endpoints for articles, podcasts, videos, news, and engagement logging
- [x] HTMX form routes and partials for creating/updating/deleting all content hub entities
- [x] Content Hub dashboard UI, navigation entry, and modal management script (`content-hub.js`)

## 🔄 Newly Completed

- [x] Documented SQL migration plan for dev/staging/prod rollouts (`docs/community_hub_migration.md`)
- [x] Seed script for starter articles/podcasts/videos/news (`seed_community_content.py`)
- [x] Service + API tests covering content hub CRUD and engagement (`tests/integration/community/test_content_hub.py`, `test_content_api.py`)
- [x] Engagement metrics surfaced on Content Hub dashboard cards
- [x] Admin-only guardrails for content CRUD routes/forms (using `get_admin_user` dependency)
- [x] Markdown preview workflow for article editor (HTMX + markdown renderer)
- [x] OpenAPI metadata added to content endpoints for improved schema documentation
- [x] Playwright smoke script outline for Content Hub UI flows (`tests/ui/test_content_hub.py`)

## 🧭 Suggested Next Steps for V1

1. Run `alembic upgrade head` in each environment and execute `seed_community_content.py` where demo data is needed.
2. Capture real tenant requirements for engagement actions (e.g., likes vs. downloads) and expand tracking schema if required.
3. Enable Playwright fixtures + authentication so the new Content Hub smoke suite runs in CI.
4. Add analytics widgets for trending content (top views/shares) once engagement data accumulates.
5. Coordinate content author training and document moderation workflow before GA launch.

> Keep this file updated as tasks complete so any teammate can pick up where you left off.
